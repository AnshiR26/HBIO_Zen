# app/adapters/http_image_downloader_adapter.py
import requests


class HttpImageDownloaderAdapter:
    def download(self, url: str, timeout: float = 10.0) -> tuple[bytes, str]:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.content, response.headers.get("Content-Type", "")