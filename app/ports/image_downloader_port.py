# app/ports/image_downloader_port.py
from typing import Protocol


class ImageDownloaderPort(Protocol):
    def download(self, url: str, timeout: float = 10.0) -> tuple[bytes, str]:
        """
        Returns (image_bytes, content_type_header)
        """
        ...