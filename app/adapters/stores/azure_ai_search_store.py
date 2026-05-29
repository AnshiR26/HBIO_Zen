from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import VectorizedQuery
from app.config.settings import (
   AZURE_SEARCH_ENDPOINT,
   AZURE_SEARCH_API_KEY,
   AZURE_SEARCH_INDEX_NAME,
)
class AzureAISearchKnowledgeStore:
   def __init__(self):
       self.client = SearchClient(
           endpoint=AZURE_SEARCH_ENDPOINT,
           index_name=AZURE_SEARCH_INDEX_NAME,
           credential=AzureKeyCredential(
               AZURE_SEARCH_API_KEY
           ),
       )
   # ==========================================================
   # ADD TEXT CHUNKS
   # ==========================================================
   def add_text_chunks(self, chunks, embeddings):
       documents = []
       for i, chunk in enumerate(chunks):
           metadata = chunk["metadata"]
           documents.append(
               {
                   "id": chunk["id"],
                   "content": chunk["text"],
                   "contentVector": embeddings[i],
                   # metadata fields
                   "source": metadata.get("source", ""),
                   "page": metadata.get("page", 0),
                   "article_id": str(
                       metadata.get("article_id", "")
                   ),
                   "title": metadata.get("title", ""),
                   "url": metadata.get("url", ""),
                   "visibility": metadata.get(
                       "visibility",
                       "public",
                   ),
                   "user_segment_id": metadata.get(
                       "user_segment_id",
                       "",
                   ),
                   "user_segment_ids": metadata.get(
                       "user_segment_ids",
                       "",
                   ),
                   "permission_group_id": metadata.get(
                       "permission_group_id",
                       "",
                   ),
                   "section_id": metadata.get(
                       "section_id",
                       "",
                   ),
                   "category_id": metadata.get(
                       "category_id",
                       "",
                   ),
                   "updated_at": metadata.get(
                       "updated_at",
                       "",
                   ),
               }
           )
       result = self.client.upload_documents(documents)
       successful = sum(
           1 for r in result if r.succeeded
       )
       return successful
   # ==========================================================
   # IMAGE ENTRIES
   # ==========================================================
   # OPTIONAL
   # Since you moved to expand-link architecture,
   # images can effectively be ignored.
   def add_image_entries(self, image_entries, embeddings):
       return 0
   # ==========================================================
   # QUERY TEXT CHUNKS
   # ==========================================================
   def query_text_chunks(
       self,
       query_embedding,
       top_k=4,
       filters=None,
   ):
       vector_query = VectorizedQuery(
           vector=query_embedding,
           k_nearest_neighbors=top_k,
           fields="contentVector",
       )
       filter_expression = None
       # ------------------------------------------------------
       # Convert filters to Azure AI Search filter syntax
       # ------------------------------------------------------
       if filters:
           if "user_segment_ids" in filters:
               user_seg_list = filters["user_segment_ids"]
               if user_seg_list:
                   segs_str = ",".join(str(s) for s in user_seg_list)
                   filter_expression = (
                       f"visibility eq 'public' or "
                       f"(visibility eq 'restricted' and search.in(user_segment_ids, '{segs_str}', ','))"
                   )
               else:
                   filter_expression = "visibility eq 'public'"
           elif "visibility" in filters:
               visibility = filters["visibility"]
               filter_expression = (
                   f"visibility eq '{visibility}'"
               )
       results = self.client.search(
           search_text=None,
           vector_queries=[vector_query],
           top=top_k,
           filter=filter_expression,
       )
       retrieved = []
       for doc in results:
           retrieved.append(
               {
                   "text": doc.get("content", ""),
                   "source": doc.get("source", "unknown"),
                   "page": doc.get("page", 0),
                   "distance": None,
                   "metadata": {
                       "source": doc.get("source", ""),
                       "page": doc.get("page", 0),
                       "article_id": doc.get(
                           "article_id",
                           "",
                       ),
                       "title": doc.get("title", ""),
                       "url": doc.get("url", ""),
                       "visibility": doc.get(
                           "visibility",
                           "public",
                       ),
                       "user_segment_id": doc.get(
                           "user_segment_id",
                           "",
                       ),
                       "user_segment_ids": doc.get(
                           "user_segment_ids",
                           "",
                       ),
                       "permission_group_id": doc.get(
                           "permission_group_id",
                           "",
                       ),
                       "section_id": doc.get(
                           "section_id",
                           "",
                       ),
                       "category_id": doc.get(
                           "category_id",
                           "",
                       ),
                       "updated_at": doc.get(
                           "updated_at",
                           "",
                       ),
                   },
               }
           )
       return retrieved
   # ==========================================================
   # QUERY IMAGES
   # ==========================================================
   def query_images(
       self,
       query_embedding,
       top_k=2,
       filters=None,
   ):
       return []
   # ==========================================================
   # GET COUNTS
   # ==========================================================
   def get_text_count(self):
       results = self.client.search(
           search_text="*",
           top=0,
           include_total_count=True,
       )
       return results.get_count()
   def get_image_count(self):
       return 0
   # ==========================================================
   # RESET INDEX
   # ==========================================================
   def reset(self):
       print(
           "RESET not implemented for Azure AI Search"
       )
   # ==========================================================
   # DELETE BY SOURCE
   # ==========================================================
   def delete_by_source(self, source: str) -> None:
       try:
           results = self.client.search(
               search_text="*",
               filter=f"source eq '{source}'",
               top=1000,
           )
           ids_to_delete = []
           for doc in results:
               ids_to_delete.append(
                   {
                       "id": doc["id"]
                   }
               )
           if ids_to_delete:
               self.client.delete_documents(
                   documents=ids_to_delete
               )
               print(
                   f"DELETED {len(ids_to_delete)} "
                   f"DOCUMENTS for source {source}"
               )
       except Exception as e:
           print(
               f"DELETE ERROR for source {source}: {e}"
           )