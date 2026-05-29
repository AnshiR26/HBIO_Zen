# app/adapters/local_image_storage_adapter.py
import os
from app.config.settings import IMAGE_DIR


class LocalImageStorageAdapter:
    def save_image(self, source: str, index: int, content: bytes, content_type: str) -> str:
        os.makedirs(IMAGE_DIR, exist_ok=True)

        ext = ".jpg"
        if "png" in content_type.lower():
            ext = ".png"

        filename = f"{source}_img_{index}{ext}"
        path = os.path.join(IMAGE_DIR, filename)

        with open(path, "wb") as f:
            f.write(content)

        return filename