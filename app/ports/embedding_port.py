from typing import Protocol, List


class EmbeddingPort(Protocol):
    def embed_texts(self, texts: list[str]) -> List[List[float]]:
        ...

    def embed_query(self, query: str) -> List[float]:
        ...