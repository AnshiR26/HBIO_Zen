# app/ports/sync_state_port.py
from typing import Protocol


class SyncStatePort(Protocol):
    def load_state(self) -> dict:
        ...

    def save_state(self, state: dict) -> None:
        ...