import re
import os


class ImageService:
    def __init__(self, public_base_url: str):
        self.public_base_url = public_base_url.rstrip("/")

    def _extract_image_name(self, image: dict) -> str:
        return (
            image.get("image_path")
            or image.get("image_name")
            or image.get("name")
            or image.get("file_name")
            or image.get("blob_name")
            or image.get("metadata", {}).get("image_path")
            or ""
        )

    def _image_sort_key(self, image) -> int:
        name = self._extract_image_name(image)
        match = re.search(r'_img_(\d+)(?:\.\w+)?$', name)
        return int(match.group(1)) if match else 10**9

    def format_images(self, images: list) -> list:
        if not images:
            print("IMAGE DEBUG: no images received", flush=True)
            return []

        print("IMAGE DEBUG: raw images:", images, flush=True)

        sorted_images = sorted(images, key=self._image_sort_key)

        formatted = []
        for image in sorted_images:
            image_name = self._extract_image_name(image)
            if not image_name:
                continue

            image_url = f"{self.public_base_url}/images/{image_name}"

            item = {
                "image_name": image_name,
                "url": image_url,
                "caption": image.get("caption") or "",
                "source": image.get("source") or image.get("metadata", {}).get("source") or "",
            }
            formatted.append(item)

        print("IMAGE DEBUG: formatted images:", formatted, flush=True)
        return formatted