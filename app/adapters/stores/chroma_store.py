import chromadb

from app.config.settings import (

    COLLECTION_NAME,

    IMAGE_COLLECTION_NAME,

    CHROMA_HOST,

    CHROMA_PORT,

    CHROMA_SSL,

    CHROMA_TENANT,

    CHROMA_DATABASE,

)

class ChromaKnowledgeStore:

    def __init__(self):

        self._client = None

    def _get_client(self):

        if self._client is None:

            self._client = chromadb.HttpClient(

                host=CHROMA_HOST,

                port=CHROMA_PORT,

                ssl=CHROMA_SSL,

                tenant=CHROMA_TENANT,

                database=CHROMA_DATABASE,

            )

        return self._client

    def _get_text_collection(self):

        return self._get_client().get_or_create_collection(

            name=COLLECTION_NAME

        )

    def _get_image_collection(self):

        return self._get_client().get_or_create_collection(

            name=IMAGE_COLLECTION_NAME

        )

    def add_text_chunks(self, chunks, embeddings):

        collection = self._get_text_collection()

        ids = [chunk["id"] for chunk in chunks]

        docs = [chunk["text"] for chunk in chunks]

        metas = [chunk["metadata"] for chunk in chunks]

        existing_ids = set()

        try:

            existing = collection.get(ids=ids)

            existing_ids = set(existing.get("ids", []))

        except Exception:

            existing_ids = set()

        filtered_ids = []

        filtered_docs = []

        filtered_metas = []

        filtered_embeddings = []

        for i, chunk_id in enumerate(ids):

            if chunk_id not in existing_ids:

                filtered_ids.append(ids[i])

                filtered_docs.append(docs[i])

                filtered_metas.append(metas[i])

                filtered_embeddings.append(embeddings[i])

        if filtered_ids:

            collection.add(

                ids=filtered_ids,

                documents=filtered_docs,

                metadatas=filtered_metas,

                embeddings=filtered_embeddings,

            )

        return len(filtered_ids)

    def add_image_entries(self, image_entries, embeddings):

        collection = self._get_image_collection()

        ids = [item["image_id"] for item in image_entries]

        docs = [item["image_text"] for item in image_entries]

        metas = [

            {

                "source": item["source"],

                "page": item["page"],

                "image_path": item["image_path"],

                "visibility": item.get("visibility", "public"),

                "user_segment_ids": item.get("user_segment_ids", ""),

            }

            for item in image_entries

        ]

        existing_ids = set()

        try:

            existing = collection.get(ids=ids)

            existing_ids = set(existing.get("ids", []))

        except Exception:

            existing_ids = set()

        filtered_ids = []

        filtered_docs = []

        filtered_metas = []

        filtered_embeddings = []

        for i, item_id in enumerate(ids):

            if item_id not in existing_ids:

                filtered_ids.append(ids[i])

                filtered_docs.append(docs[i])

                filtered_metas.append(metas[i])

                filtered_embeddings.append(embeddings[i])

        if filtered_ids:

            collection.add(

                ids=filtered_ids,

                documents=filtered_docs,

                metadatas=filtered_metas,

                embeddings=filtered_embeddings,

            )

        return len(filtered_ids)

    def query_text_chunks(self, query_embedding, top_k=4, filters=None):

        collection = self._get_text_collection()

        query_kwargs = {

            "query_embeddings": [query_embedding],

            "n_results": top_k,

        }

        # Apply metadata filters (e.g. {"visibility": "public"})

        if filters:

            query_kwargs["where"] = filters

        results = collection.query(**query_kwargs)

        documents = results.get("documents", [[]])[0]

        metadatas = results.get("metadatas", [[]])[0]

        distances = (

            results.get("distances", [[]])[0]

            if "distances" in results

            else []

        )

        retrieved = []

        for i, doc in enumerate(documents):

            metadata = metadatas[i] if i < len(metadatas) else {}

            distance = distances[i] if i < len(distances) else None

            retrieved.append(

                {

                    "text": doc,

                    "source": metadata.get("source", "unknown"),

                    "page": metadata.get("page", "unknown"),

                    "distance": distance,

                    "metadata": metadata,

                }

            )

        return retrieved

    def query_images(self, query_embedding, top_k=2, filters=None):

        collection = self._get_image_collection()

        query_kwargs = {

            "query_embeddings": [query_embedding],

            "n_results": top_k,

        }

        # Apply metadata filters (e.g. {"visibility": "public"})

        if filters:

            query_kwargs["where"] = filters

        results = collection.query(**query_kwargs)

        documents = results.get("documents", [[]])[0]

        metadatas = results.get("metadatas", [[]])[0]

        distances = (

            results.get("distances", [[]])[0]

            if "distances" in results

            else []

        )

        retrieved_images = []

        for i, _ in enumerate(documents):

            metadata = metadatas[i] if i < len(metadatas) else {}

            distance = distances[i] if i < len(distances) else None

            retrieved_images.append(

                {

                    "source": metadata.get("source", "unknown"),

                    "page": metadata.get("page", "unknown"),

                    "image_path": metadata.get("image_path", ""),

                    "distance": distance,

                    "metadata": metadata,

                }

            )

        return retrieved_images

    def get_text_count(self):

        return self._get_text_collection().count()

    def get_image_count(self):

        return self._get_image_collection().count()

    def reset(self):

        client = self._get_client()

        try:

            client.delete_collection(COLLECTION_NAME)

        except Exception:

            pass

        try:

            client.delete_collection(IMAGE_COLLECTION_NAME)

        except Exception:

            pass

    def delete_by_source(self, source: str) -> None:

        text_collection = self._get_text_collection()

        image_collection = self._get_image_collection()

        try:

            text_collection.delete(

                where={"source": {"$eq": source}}

            )

        except Exception as e:

            print(f"TEXT DELETE ERROR for source {source}: {e}")

        try:

            image_collection.delete(

                where={"source": {"$eq": source}}

            )

        except Exception as e:

            print(f"IMAGE DELETE ERROR for source {source}: {e}")
 