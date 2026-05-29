# app/adapters/json_sync_state_adapter.py
import json
import os
from app.config.settings import STATE_FILE


class JsonSyncStateAdapter:
    def load_state(self) -> dict:
        if not os.path.exists(STATE_FILE):
            return {}
        with open(STATE_FILE, "r") as f:
            return json.load(f)

    def save_state(self, state: dict) -> None:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)