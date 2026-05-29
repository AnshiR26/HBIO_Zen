import time
from app.ports.knowledge_source_port import KnowledgeSourcePort
from app.ports.knowledge_store_port import KnowledgeStorePort
from app.ports.embedding_port import EmbeddingPort
from app.ports.sync_state_port import SyncStatePort
from app.ports.image_downloader_port import ImageDownloaderPort
from app.ports.image_storage_port import ImageStoragePort
class SyncZendeskArticlesUseCase:
   def __init__(
       self,
       source: KnowledgeSourcePort,
       embedder: EmbeddingPort,
       knowledge_store: KnowledgeStorePort,
       chunker,
       sync_state: SyncStatePort,
       image_downloader: ImageDownloaderPort,
       image_storage: ImageStoragePort,
   ):
       self.source = source
       self.embedder = embedder
       self.knowledge_store = knowledge_store
       self.chunker = chunker
       self.sync_state = sync_state
       self.image_downloader = image_downloader
       self.image_storage = image_storage
   def _ingest_article(self, article: dict) -> None:
       article_id = article["id"]
       title = article.get("title", "untitled")
       updated_at = article.get("updated_at", "unknown")
       source_name = f"zendesk_article_{article_id}"
       # ----------------------------------------------------------
       # Visibility Metadata
       # ----------------------------------------------------------
       segment_ids = article.get("user_segment_ids") or []
       if article.get("user_segment_id"):
           segment_ids.append(article["user_segment_id"])
       segment_ids = list(set(segment_ids))
       visibility = "restricted" if segment_ids else "public"
       # ----------------------------------------------------------
       # Delete Existing Chunks
       # ----------------------------------------------------------
       self.knowledge_store.delete_by_source(source_name)
       # ----------------------------------------------------------
       # Extract Text + Images
       # ----------------------------------------------------------
       text, images = self.source.extract_text_and_images(article)
       # ----------------------------------------------------------
       # Ingest Text Chunks
       # ----------------------------------------------------------
       if text.strip():
           raw_chunks = self.chunker(text)
           chunks = []
           for i, chunk in enumerate(raw_chunks):
               chunks.append(
                   {
                       "id": f"{source_name}_chunk_{i}",
                       "text": chunk,
                       "metadata": {
                           "source": source_name,
                           "page": 0,
                           "article_id": article_id,
                           "title": title,
                           "url": article.get("html_url", ""),
                           "visibility": visibility,
                           "user_segment_id": str(
                               article.get("user_segment_id") or ""
                           ),
                           "user_segment_ids": ",".join(
                               str(x) for x in segment_ids
                           ),
                           "permission_group_id": str(
                               article.get("permission_group_id") or ""
                           ),
                           "section_id": str(
                               article.get("section_id") or ""
                           ),
                           "category_id": str(
                               article.get("category_id") or ""
                           ),
                           "updated_at": updated_at,
                       },
                   }
               )
           embeddings = self.embedder.embed_texts(
               [c["text"] for c in chunks]
           )
           self.knowledge_store.add_text_chunks(
               chunks,
               embeddings,
           )
       # ----------------------------------------------------------
    #    # Ingest Images
    #    # ----------------------------------------------------------
    #    image_entries = []
    #    for i, img in enumerate(images):
    #        try:
    #            content, content_type = self.image_downloader.download(
    #                img["url"],
    #                timeout=10,
    #            )
    #            filename = self.image_storage.save_image(
    #                source=source_name,
    #                index=i,
    #                content=content,
    #                content_type=content_type,
    #            )
    #            image_entries.append(
    #                {
    #                    "image_id": f"{source_name}_img_{i}",
    #                    "source": source_name,
    #                    "page": 0,
    #                    "image_path": filename,
    #                    "image_text": (
    #                        img.get("alt") or f"image from {title}"
    #                    ),
    #                    "visibility": visibility,
    #                    "user_segment_ids": ",".join(
    #                        str(x) for x in segment_ids
    #                    ),
    #                }
    #            )
    #        except Exception as e:
    #            print(
    #                f"IMAGE INGEST ERROR | "
    #                f"ARTICLE: {title} | "
    #                f"ERROR: {e}"
    #            )
    #            continue
    #    if image_entries:
    #        embeddings = self.embedder.embed_texts(
    #            [entry["image_text"] for entry in image_entries]
    #        )
    #        self.knowledge_store.add_image_entries(
    #            image_entries,
    #            embeddings,
    #        )
   # ==============================================================
   # FULL SYNC
   # ==============================================================
   def initial_full_sync(self) -> None:
       print("\nFULL SYNC START\n")
       articles = self.source.fetch_all_public_articles()
       total_articles = len(articles)
       print(f"TOTAL ARTICLES FETCHED: {total_articles}\n")
       public_titles = []
       restricted_titles = []
       for idx, article in enumerate(articles, start=1):
           segment_ids = article.get("user_segment_ids") or []
           if article.get("user_segment_id"):
               segment_ids.append(article["user_segment_id"])
           visibility = (
               "restricted"
               if segment_ids
               else "public"
           )
           title = article.get("title", "untitled")
           print(
               f"[{idx}/{total_articles}] "
               f"{title} "
               f"| VISIBILITY: {visibility}"
           )
           if visibility == "public":
               public_titles.append(title)
           else:
               restricted_titles.append(title)
           self._ingest_article(article)
       # ----------------------------------------------------------
       # Final Summary
       # ----------------------------------------------------------
       print("\n" + "=" * 80)
       print(f"TOTAL PUBLIC ARTICLES INGESTED: {len(public_titles)}")
       print("=" * 80)
       for idx, title in enumerate(public_titles, start=1):
           print(f"{idx}. {title}")
       print("\n" + "=" * 80)
       print(f"TOTAL RESTRICTED ARTICLES INGESTED: {len(restricted_titles)}")
       print("=" * 80)
       for idx, title in enumerate(restricted_titles, start=1):
           print(f"{idx}. {title}")
       # ----------------------------------------------------------
       # Save Sync State
       # ----------------------------------------------------------
       state = {
           "last_incremental_start_time": int(time.time()) - 60
       }
       self.sync_state.save_state(state)
       print("\nFULL SYNC DONE\n")
   # ==============================================================
   # INCREMENTAL SYNC
   # ==============================================================
   def incremental_sync(self) -> None:
       state = self.sync_state.load_state()
       start_time = state.get(
           "last_incremental_start_time",
           int(time.time()) - 86400,
       )
       print("\nINCREMENTAL SYNC START\n")
       articles, end_time = self.source.fetch_incremental_articles(
           start_time
       )
       total_articles = len(articles)
       print(f"UPDATED ARTICLES FETCHED: {total_articles}\n")
       for idx, article in enumerate(articles, start=1):
           segment_ids = article.get("user_segment_ids") or []
           if article.get("user_segment_id"):
               segment_ids.append(article["user_segment_id"])
           visibility = (
               "restricted"
               if segment_ids
               else "public"
           )
           title = article.get("title", "untitled")
           print(
               f"[{idx}/{total_articles}] "
               f"{title} "
               f"| VISIBILITY: {visibility}"
           )
           self._ingest_article(article)
       self.sync_state.save_state(
           {
               "last_incremental_start_time": end_time
           }
       )
       print("\nINCREMENTAL SYNC DONE\n")
if __name__ == "__main__":
    from app.config.container import Container

    container = Container()

    print("Starting FULL sync...")

    container.sync_zendesk_articles_use_case.initial_full_sync()

    print("FULL sync complete.")