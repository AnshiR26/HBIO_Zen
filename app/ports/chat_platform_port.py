from typing import Protocol


class ChatPlatformPort(Protocol):
    def send_message(self, conversation_id: str, text: str, images=None) -> None:
        ...