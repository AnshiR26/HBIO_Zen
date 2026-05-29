# app/ports/image_storage_port.py
from typing import Protocol


class ImageStoragePort(Protocol):
    def save_image(self, source: str, index: int, content: bytes, content_type: str) -> str:
        """
        Returns a relative or absolute image_path to store in DB,
        e.g. 'zendesk_article_123_img_0.png'
        """
        ...