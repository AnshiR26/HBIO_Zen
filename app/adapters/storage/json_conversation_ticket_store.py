import json
import os
import threading

class JsonConversationTicketStore:
   def __init__(self, filepath: str):
       self.filepath = filepath
       self.lock = threading.Lock()
       self._mappings = {}
       self._load()
   # ==================================================================
   # INTERNAL LOAD / SAVE
   # ==================================================================
   def _load(self):
       with self.lock:
           if os.path.exists(self.filepath):
               try:
                   with open(self.filepath, "r") as f:
                       self._mappings = json.load(f)
               except Exception as e:
                   print(f"Error loading conversation mappings: {e}", flush=True)
                   self._mappings = {}
   def _save(self):
       with self.lock:
           try:
               os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
               with open(self.filepath, "w") as f:
                   json.dump(self._mappings, f, indent=2)
           except Exception as e:
               print(f"Error saving conversation mappings: {e}", flush=True)
   # ==================================================================
   # TICKET DATA
   # ==================================================================
   def get_ticket_data(self, conversation_id: str) -> dict:
       with self.lock:
           val = self._mappings.get(conversation_id)
           if not val:
               return None
           if isinstance(val, dict):
               return val
           # Backwards compatibility for old string mapping format
           return {
               "ticket_id": str(val),
               "is_placeholder_subject": False,
               "email": None,
           }
   def save_mapping(
       self,
       conversation_id: str,
       ticket_id: str,
       is_placeholder_subject: bool = False,
       email: str = None,
   ):
       with self.lock:
           # Preserve existing email if not explicitly overriding
           existing = self._mappings.get(conversation_id) or {}
           existing_email = existing.get("email") if isinstance(existing, dict) else None
           self._mappings[conversation_id] = {
               "ticket_id": str(ticket_id),
               "is_placeholder_subject": is_placeholder_subject,
               "email": email or existing_email,
           }
       self._save()
   # ==================================================================
   # VISIBILITY FILTERS CACHE
   # Segment lookup is expensive — resolve once per conversation and
   # cache here alongside ticket data so subsequent messages reuse it.
   #
   # Stored under a separate key: f"{conversation_id}__filters"
   # to avoid any collision with existing ticket data keys.
   # ==================================================================
   def get_visibility_filters(self, conversation_id: str) -> dict | None:
       """
       Returns {"email": ..., "filters": {...}} if already resolved
       for this conversation, or None if this is the first message.
       """
       key = f"{conversation_id}__filters"
       with self.lock:
           return self._mappings.get(key, None)
   def save_visibility_filters(
       self,
       conversation_id: str,
       email: str,
       filters: dict,
   ) -> None:
       """
       Cache resolved visibility filters for the lifetime of this
       conversation. Called once on the first authenticated message.
       """
       key = f"{conversation_id}__filters"
       with self.lock:
           self._mappings[key] = {
               "email": email,
               "filters": filters,
           }
       self._save()