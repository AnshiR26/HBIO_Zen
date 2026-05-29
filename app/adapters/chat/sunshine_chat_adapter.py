import requests
from app.config.settings import SC_KEY_ID, SC_SECRET, SC_APP_ID, ZENDESK_SUBDOMAIN


class SunshineChatAdapter:
    def __init__(self):
        self.key_id = SC_KEY_ID
        self.secret = SC_SECRET
        self.app_id = SC_APP_ID
        self.subdomain = ZENDESK_SUBDOMAIN

    def _post_message(self, conversation_id: str, content: dict):
        url = f"https://{self.subdomain}.zendesk.com/sc/v2/apps/{self.app_id}/conversations/{conversation_id}/messages"
        payload = {
            "author": {"type": "business"},
            "content": content
        }

        response = requests.post(
            url,
            auth=(self.key_id, self.secret),
            json=payload,
            timeout=8
        )

        if not response.ok:
            print("ZENDESK ERROR:", response.status_code, response.text, flush=True)

        response.raise_for_status()
        return response.json()

    def _post_activity(self, conversation_id: str, activity_type: str):
        url = f"https://{self.subdomain}.zendesk.com/sc/v2/apps/{self.app_id}/conversations/{conversation_id}/activity"
        payload = {
            "author": {"type": "business"},
            "type": activity_type
        }

        response = requests.post(
            url,
            auth=(self.key_id, self.secret),
            json=payload,
            timeout=8
        )

        if not response.ok:
            print("ZENDESK ACTIVITY ERROR:", response.status_code, response.text, flush=True)

        response.raise_for_status()
        return response.json()

    def send_typing_start(self, conversation_id: str):
        return self._post_activity(conversation_id, "typing:start")

    def send_typing_stop(self, conversation_id: str):
        return self._post_activity(conversation_id, "typing:stop")

    def send_message(
        self,
        conversation_id: str,
        text: str,
        images=None,
        actions=None,
        ):
        content = {
            "type": "text",
            "markdownText": text
        }
        # Add quick reply buttons if actions exist
        if actions:
            content["actions"] = actions
        text_response = self._post_message(
            conversation_id,
            content
        )
        for img in images or []:
            try:
                image_url = img.get("url")
                if not image_url:
                    continue
                self._post_message(
                    conversation_id,
                    {
                        "type": "image",
                        "mediaUrl": image_url
                    }
                )
            except Exception as e:
                print("ZENDESK IMAGE SEND ERROR:", str(e), flush=True)
        return text_response