class TicketIntentService:
    def is_ticket_intent(self, text: str) -> bool:
        if not text:
            return False

        q = text.strip().lower()

        triggers = [
            "create ticket",
            "create a ticket",
            "raise ticket",
            "raise a ticket",
            "log issue",
            "log an issue",
            "open ticket",
            "open a ticket",
            "contact support",
            "submit ticket",
            "make a ticket",
        ]

        return any(trigger in q for trigger in triggers)