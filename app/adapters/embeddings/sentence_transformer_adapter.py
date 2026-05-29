from sentence_transformers import SentenceTransformer
from app.config.settings import EMBEDDING_MODEL


class SentenceTransformerAdapter:
    def __init__(self, model_name: str = EMBEDDING_MODEL):
        self.model_name = model_name
        self._model = None

    def _get_model(self):
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_texts(self, texts):
        model = self._get_model()
        return model.encode(texts, convert_to_numpy=True).tolist()

    def embed_query(self, query: str):
        model = self._get_model()
        return model.encode(query, convert_to_numpy=True).tolist()