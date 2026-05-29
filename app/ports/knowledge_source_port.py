from typing import Protocol


class KnowledgeSourcePort(Protocol):
    def fetch_all_public_articles(self) -> list[dict]:
        ...

    def fetch_incremental_articles(self, start_time: int) -> tuple[list[dict], int]:
        ...

    def extract_text_and_images(self, article: dict) -> tuple[str, list[dict]]:
        ...