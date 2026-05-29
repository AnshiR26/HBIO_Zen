from collections import deque
class WebhookParserService:
   def __init__(self):
       self.recent_event_ids = deque(maxlen=100)
   def extract_conversation_id(self, payload: dict):
       try:
           events = payload.get("events") or []
           if events:
               conv = events[0].get("payload", {}).get("conversation", {})
               conv_id = conv.get("id")
               if conv_id:
                   return conv_id
       except Exception:
           pass
       conv = payload.get("conversation") or {}
       return conv.get("id")
   def extract_user_text(self, payload: dict):
       try:
           events = payload.get("events") or []
           if events:
               msg = events[0].get("payload", {}).get("message", {})
               content = msg.get("content", {})
               if content.get("type") == "text":
                   text = content.get("text")
                   if text:
                       return text
       except Exception:
           pass
       msgs = payload.get("messages") or []
       if msgs:
           first_msg = msgs[0] or {}
           content = first_msg.get("content", {})
           if content.get("type") == "text":
               return content.get("text")
       return None
   def extract_message_author_type(self, payload: dict):
       try:
           events = payload.get("events") or []
           if events:
               msg = events[0].get("payload", {}).get("message", {})
               author = msg.get("author", {}) or {}
               return author.get("type")
       except Exception:
           pass
       return None
   def extract_event_type(self, payload: dict):
       try:
           events = payload.get("events") or []
           if events:
               return events[0].get("type")
       except Exception:
           pass
       return None
   def extract_event_id(self, payload: dict):
       try:
           events = payload.get("events") or []
           if events:
               return events[0].get("id")
       except Exception:
           pass
       return None
   def extract_authenticated(self, payload: dict) -> bool:
       """
       Extract whether the Zendesk user is authenticated.
       Returns:
           True  -> user is logged in to the knowledge portal / Zendesk Messaging
           False -> anonymous visitor
       """
       try:
           events = payload.get("events") or []
           if events:
               return (
                   events[0]
                   .get("payload", {})
                   .get("message", {})
                   .get("author", {})
                   .get("user", {})
                   .get("authenticated", False)
               )
       except Exception:
           pass
       return False
   def extract_user_email(self, payload: dict) -> str:
       try:
           events = payload.get("events") or []
           if events:
               user = (
                   events[0]
                   .get("payload", {})
                   .get("message", {})
                   .get("author", {})
                   .get("user", {})
               )
               return user.get("email") or ""
       except Exception:
           pass
       return ""
   def extract_user_external_id(self, payload: dict) -> str:
       try:
           events = payload.get("events") or []
           if events:
               user = (
                   events[0]
                   .get("payload", {})
                   .get("message", {})
                   .get("author", {})
                   .get("user", {})
               )
               return user.get("externalId") or ""
       except Exception:
           pass
       return ""
   def extract_user_id(self, payload: dict) -> str:
       try:
           events = payload.get("events") or []
           if events:
               author = (
                   events[0]
                   .get("payload", {})
                   .get("message", {})
                   .get("author", {})
               )
               return author.get("userId") or ""
       except Exception:
           pass
       return ""
   def parse(self, payload: dict):
       event_id = self.extract_event_id(payload)
       event_type = self.extract_event_type(payload)
       author_type = self.extract_message_author_type(payload)
       conversation_id = self.extract_conversation_id(payload)
       user_text = self.extract_user_text(payload)
       # Check for duplicate events
       if event_id and event_id in self.recent_event_ids:
           return {
               "should_process": False,
               "reason": "duplicate_event"
           }
       # Store event ID to prevent duplicate processing
       if event_id:
           self.recent_event_ids.append(event_id)
       # Ignore non-message events
       if event_type and event_type != "conversation:message":
           return {
               "should_process": False,
               "reason": "non-message event"
           }
       # Ignore bot/system messages
       if author_type and author_type != "user":
           return {
               "should_process": False,
               "reason": "non-user message"
           }
       # Validate required fields
       if not conversation_id or not user_text:
           return {
               "should_process": False,
               "reason": "missing conversation_id or text"
           }
       # Determine whether the user is authenticated
       authenticated = self.extract_authenticated(payload)
       # Extract user profile identifiers
       email = self.extract_user_email(payload)
       external_id = self.extract_user_external_id(payload)
       user_id = self.extract_user_id(payload)
       # Build default visibility filters
       #
       # authenticated = True:
       #   User is logged in, so allow both public and restricted articles.
       #   Returning None means "no filtering".
       #
       # authenticated = False:
       #   User is anonymous, so restrict retrieval to public articles only.
       if authenticated:
           visibility_filters = None
       else:
           visibility_filters = {
               "visibility": "public"
           }
       return {
           "should_process": True,
           "conversation_id": conversation_id,
           "user_text": user_text,
           "reason": "ok",
           "visibility_filters": visibility_filters,
           "authenticated": authenticated,
           "user_email": email,
           "user_external_id": external_id,
           "user_id": user_id,
       }