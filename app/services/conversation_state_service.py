class ConversationStateService:
    def __init__(self):
        self._state = {}

    def get(self, conversation_id: str):
        return self._state.get(conversation_id)

    def start_ticket_flow(self, conversation_id: str):
        self._state[conversation_id] = {
            "mode": "ticket_creation",
            "step": "awaiting_subject",
            "data": {
                "subject": "",
                "description": "",
                "email": "",
                "name": "",
            },
        }

    def update_data(self, conversation_id: str, **kwargs):
        state = self._state.get(conversation_id)
        if not state:
            return
        state["data"].update(kwargs)

    def set_step(self, conversation_id: str, step: str):
        state = self._state.get(conversation_id)
        if not state:
            return
        state["step"] = step

    def clear(self, conversation_id: str):
        self._state.pop(conversation_id, None)

    def is_ticket_flow(self, conversation_id: str) -> bool:
        state = self._state.get(conversation_id)
        return bool(state and state.get("mode") == "ticket_creation")

    def start_email_collection_flow(self, conversation_id: str):
        """Start flow where bot asks anonymous user for their email before Q&A."""
        self._state[conversation_id] = {
            "mode": "email_collection",
            "step": "awaiting_email",
            "data": {},
        }

    def is_email_collection_flow(self, conversation_id: str) -> bool:
        state = self._state.get(conversation_id)
        return bool(state and state.get("mode") == "email_collection")
