import json
import os
import threading

class ConversationMemoryService:
   def __init__(self, filepath: str, max_messages: int = 10):
       """
       Stores recent conversation history, persisted to a JSON file.
       Structure on disk:
       {
           conversation_id: [
               {
                   "role": "user" / "assistant",
                   "text": "message text"
               }
           ]
       }
       - Survives server restarts (no lost context mid-conversation)
       - Thread-safe via threading.Lock
       - filepath should point to a persistent directory e.g.
         /home/data/conversation_memory.json on Azure App Service
       """
       self.filepath = filepath
       self.max_messages = max_messages
       self.lock = threading.Lock()
       self._memory = {}
       self._load()
   # ==========================================================
   # INTERNAL LOAD / SAVE
   # ==========================================================
   def _load(self):
       with self.lock:
           if os.path.exists(self.filepath):
               try:
                   with open(self.filepath, "r") as f:
                       self._memory = json.load(f)
               except Exception as e:
                   print(f"Error loading conversation memory: {e}", flush=True)
                   self._memory = {}
   def _save(self):
       # Called without lock — callers already hold it
       try:
           os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
           with open(self.filepath, "w") as f:
               json.dump(self._memory, f, indent=2)
       except Exception as e:
           print(f"Error saving conversation memory: {e}", flush=True)
   # ==========================================================
   # ADD MESSAGE
   # ==========================================================
   def add_message(
       self,
       conversation_id: str,
       role: str,
       text: str,
   ):
       if not conversation_id:
           return
       with self.lock:
           if conversation_id not in self._memory:
               self._memory[conversation_id] = []
           self._memory[conversation_id].append(
               {
                   "role": role,
                   "text": text,
               }
           )
           # Keep only recent messages
           self._memory[conversation_id] = (
               self._memory[conversation_id][-self.max_messages:]
           )
           self._save()
   # ==========================================================
   # GET HISTORY
   # ==========================================================
   def get_history(
       self,
       conversation_id: str,
   ):
       with self.lock:
           return list(self._memory.get(conversation_id, []))
   # ==========================================================
   # CLEAR HISTORY
   # ==========================================================
   def clear_history(
       self,
       conversation_id: str,
   ):
       with self.lock:
           if conversation_id in self._memory:
               del self._memory[conversation_id]
               self._save()
   # ==========================================================
   # FORMAT HISTORY FOR PROMPTS
   # ==========================================================
   def format_history_for_prompt(
       self,
       conversation_id: str,
   ) -> str:
       history = self.get_history(conversation_id)
       if not history:
           return ""
       formatted = []
       for item in history:
           role = item.get("role", "").capitalize()
           text = item.get("text", "")
           formatted.append(f"{role}: {text}")
       return "\n".join(formatted)