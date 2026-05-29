import re

class HandleWebhookMessageUseCase:
   def __init__(
       self,
       answer_question_use_case,
       chat_platform,
       ticket_intent_service,
       conversation_state_service,
       zendesk_ticket_service,
       conversation_ticket_store,
       conversation_memory_service,
   ):
       self.answer_question_use_case = answer_question_use_case
       self.chat_platform = chat_platform
       self.ticket_intent_service = ticket_intent_service
       self.conversation_state_service = conversation_state_service
       self.zendesk_ticket_service = zendesk_ticket_service
       self.conversation_ticket_store = conversation_ticket_store
       self.conversation_memory_service = conversation_memory_service
   # ==================================================================
   # HELPERS
   # ==================================================================
   def _extract_email(self, text: str) -> str:
       if not text:
           return ""
       match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
       return match.group(0) if match else ""
   def _is_greeting(self, text: str) -> bool:
       clean = re.sub(r'[^\w\s]', '', text.lower()).strip()
       greetings = {
           "hi", "hello", "hey", "hola", "yo", "greetings",
           "good morning", "good afternoon", "good evening",
           "hi there", "hello there", "hey there",
           "test", "start", "restart", "help",
       }
       return clean in greetings
   def _send_typing_safe(self, conversation_id: str) -> None:
       try:
           self.chat_platform.send_typing_start(conversation_id)
       except Exception as e:
           print("TYPING INDICATOR ERROR:", str(e), flush=True)
   def _send_reply(self, conversation_id: str, reply: str) -> dict:
       self.chat_platform.send_message(
           conversation_id=conversation_id,
           text=reply,
           images=[],
       )
       return {"answer": reply, "images": []}
   # ==================================================================
   # SEGMENT RESOLUTION
   # ==================================================================
   def _resolve_user_and_filters(
       self,
       user_email: str,
       user_external_id: str,
       user_id: str,
   ) -> tuple:
       try:
           user = None
           if user_email:
               print(f"SEGMENTATION DEBUG: Looking up user by email: {user_email}", flush=True)
               user = self.zendesk_ticket_service.get_user_by_email(user_email)
           if not user and user_external_id:
               print(f"SEGMENTATION DEBUG: Looking up user by external_id: {user_external_id}", flush=True)
               user = self.zendesk_ticket_service.get_user_by_external_id(user_external_id)
           if not user and user_id:
               print(f"SEGMENTATION DEBUG: Looking up via SC user_id: {user_id}", flush=True)
               user = self.zendesk_ticket_service.get_user_by_sc_user_id(user_id)
           if user:
               api_email = user.get("email") or user_email or ""
               zendesk_user_id = user.get("id")
               print(
                   f"SEGMENTATION DEBUG: Found Zendesk user "
                   f"{zendesk_user_id} (email={api_email})",
                   flush=True,
               )
               segments = self.zendesk_ticket_service.get_user_segments(zendesk_user_id)
               user_segment_ids = [str(seg["id"]) for seg in segments if seg.get("id")]
               segment_names = [seg.get("name", "") for seg in segments]
               print(f"SEGMENTATION DEBUG: User Segments IDs: {user_segment_ids}", flush=True)
               print(f"SEGMENTATION DEBUG: User Segment Names: {segment_names}", flush=True)
               return api_email, {"user_segment_ids": user_segment_ids}
           # Authenticated but not found in Zendesk
           print(
               "SEGMENTATION DEBUG: Authenticated user not found in Zendesk. "
               "Falling back to public-only (no segments assigned).",
               flush=True,
           )
           return (user_email or "", {"user_segment_ids": []})
       except Exception as e:
           print(f"SEGMENTATION ERROR: {e}. Falling back to public only.", flush=True)
           return (user_email or "", {"user_segment_ids": []})
   # ==================================================================
   # TICKET SYNC
   # ==================================================================
   def _sync_to_ticket(
       self,
       conversation_id: str,
       user_text: str,
       bot_answer: str,
       resolved_email: str,
       ticket_data: dict | None = None,
   ) -> None:
       if ticket_data is None:
           ticket_data = self.conversation_ticket_store.get_ticket_data(conversation_id)
       comment_body = f"User: {user_text}\n\nBot: {bot_answer}"
       is_greeting = self._is_greeting(user_text)
       if ticket_data:
           ticket_id = ticket_data["ticket_id"]
           is_placeholder = ticket_data.get("is_placeholder_subject", False)
           print(f"TICKET DEBUG: Appending comment to ticket {ticket_id}", flush=True)
           subject_to_update = None
           if is_placeholder and not is_greeting:
               truncated = user_text[:50] + "..." if len(user_text) > 50 else user_text
               subject_to_update = f"AI Chat - {truncated}"
               print(f"TICKET DEBUG: Promoting subject -> {subject_to_update}", flush=True)
           self.zendesk_ticket_service.add_ticket_comment(
               ticket_id=int(ticket_id),
               comment_body=comment_body,
               public=True,
               subject=subject_to_update,
           )
           if subject_to_update:
               self.conversation_ticket_store.save_mapping(
                   conversation_id=conversation_id,
                   ticket_id=ticket_id,
                   is_placeholder_subject=False,
                   email=ticket_data.get("email"),
               )
       else:
           if is_greeting:
               subject = "AI Chat - Active Conversation"
               is_placeholder_subject = True
           else:
               truncated = user_text[:50] + "..." if len(user_text) > 50 else user_text
               subject = f"AI Chat - {truncated}"
               is_placeholder_subject = False
           ticket_email = resolved_email or f"widget_user_{conversation_id}@parkar.in"
           print(f"TICKET DEBUG: Creating ticket '{subject}' for {ticket_email}", flush=True)
           ticket_res = self.zendesk_ticket_service.create_ticket(
               subject=subject,
               description=comment_body,
               requester_name="Widget User",
               requester_email=ticket_email,
           )
           new_ticket_id = ticket_res.get("ticket", {}).get("id")
           if new_ticket_id:
               self.conversation_ticket_store.save_mapping(
                   conversation_id=conversation_id,
                   ticket_id=str(new_ticket_id),
                   is_placeholder_subject=is_placeholder_subject,
                   email=ticket_email,
               )
               print(f"TICKET DEBUG: Saved mapping -> ticket {new_ticket_id}", flush=True)
   # ==================================================================
   # MAIN EXECUTE
   # ==================================================================
   def execute(
       self,
       conversation_id: str,
       user_text: str,
       authenticated: bool = False,
       user_email: str = None,
       user_external_id: str = None,
       user_id: str = None,
   ):
       text = (user_text or "").strip()
       print("DEBUG: execute called", flush=True)
       print("DEBUG: conversation_id:", conversation_id, flush=True)
       print("DEBUG: user_text:", text, flush=True)
       print("DEBUG: authenticated:", authenticated, flush=True)
       # ==============================================================
       # FEEDBACK ACTIONS
       # Synced to ticket so conversation log is complete.
       # ==============================================================
       normalized = text.lower().strip()
       if normalized in {"feedback_yes", "yes", "👍 yes", "thumbs up"}:
           reply = "Glad I could help! Let me know if you need anything else."
           ticket_data = self.conversation_ticket_store.get_ticket_data(conversation_id)
           try:
               self._sync_to_ticket(
                   conversation_id=conversation_id,
                   user_text=text,
                   bot_answer=reply,
                   resolved_email=(ticket_data or {}).get("email", ""),
                   ticket_data=ticket_data,
               )
           except Exception as sync_err:
               print(f"TICKET SYNC ERROR (feedback_yes): {sync_err}", flush=True)
           return self._send_reply(conversation_id, reply)
       if normalized in {"feedback_no", "no", "👎 no", "thumbs down"}:
           reply = (
               "I'm sorry that didn't help. Please share more details and "
               "I'll try again."
           )
           ticket_data = self.conversation_ticket_store.get_ticket_data(conversation_id)
           try:
               self._sync_to_ticket(
                   conversation_id=conversation_id,
                   user_text=text,
                   bot_answer=reply,
                   resolved_email=(ticket_data or {}).get("email", ""),
                   ticket_data=ticket_data,
               )
           except Exception as sync_err:
               print(f"TICKET SYNC ERROR (feedback_no): {sync_err}", flush=True)
           return self._send_reply(conversation_id, reply)
       # ==============================================================
       # CANCEL FLOW
       # ==============================================================
       if text.lower() in {"cancel", "cancel ticket", "never mind"}:
           self.conversation_state_service.clear(conversation_id)
           return self._send_reply(conversation_id, "Okay, I've cancelled the current flow.")
       # ==============================================================
       # EMAIL COLLECTION FLOW
       # ==============================================================
       if self.conversation_state_service.is_email_collection_flow(conversation_id):
           email = self._extract_email(text)
           if not email:
               return self._send_reply(
                   conversation_id,
                   "That doesn't look like a valid email address. Please enter a valid email so I can assist you.",
               )
           print(f"EMAIL COLLECT: Got email {email}. Creating ticket.", flush=True)
           try:
               ticket_res = self.zendesk_ticket_service.create_ticket(
                   subject="AI Chat - Active Conversation",
                   description=f"New conversation started. Requester email: {email}",
                   requester_name="Widget User",
                   requester_email=email,
               )
               new_ticket_id = ticket_res.get("ticket", {}).get("id")
               if new_ticket_id:
                   self.conversation_ticket_store.save_mapping(
                       conversation_id=conversation_id,
                       ticket_id=str(new_ticket_id),
                       is_placeholder_subject=True,
                       email=email,
                   )
           except Exception as e:
               print(f"EMAIL COLLECT TICKET ERROR: {e}", flush=True)
           self.conversation_state_service.clear(conversation_id)
           return self._send_reply(conversation_id, "Thank you! How can I help you today?")
       # ==============================================================
       # EMAIL GATE
       # Sits BEFORE greeting shortcut — anonymous users cannot bypass
       # email collection by sending a greeting.
       # Fetch ticket_data once here and reuse throughout.
       # ==============================================================
       ticket_data = self.conversation_ticket_store.get_ticket_data(conversation_id)
       stored_email = (ticket_data or {}).get("email")
       if not authenticated and not stored_email:
           print("EMAIL GATE: Anonymous user with no email. Asking for email.", flush=True)
           self.conversation_state_service.start_email_collection_flow(conversation_id)
           self._send_typing_safe(conversation_id)
           return self._send_reply(
               conversation_id,
               "Hi, Welcome! Please provide your email address so I can assist you and keep a record of your conversation.",
           )
       # ==============================================================
       # GREETING SHORTCUT
       # After email gate — anonymous users must provide email first.
       # ==============================================================
       if self._is_greeting(text):
           greeting_reply = "Hey! How can I help you?"
           self.chat_platform.send_message(
               conversation_id=conversation_id,
               text=greeting_reply,
               images=[],
           )
           try:
               self._sync_to_ticket(
                   conversation_id=conversation_id,
                   user_text=text,
                   bot_answer=greeting_reply,
                   resolved_email=stored_email or "",
                   ticket_data=ticket_data,
               )
           except Exception as sync_err:
               print(f"TICKET SYNC ERROR: {sync_err}", flush=True)
           return {"answer": greeting_reply, "images": []}
       # ==============================================================
       # RESOLVE VISIBILITY FILTERS
       # Cache check first — segment lookup only on first message.
       # ==============================================================
       if authenticated:
           cached_filters = self.conversation_ticket_store.get_visibility_filters(
               conversation_id
           )
           if cached_filters:
               resolved_email = cached_filters.get("email", "")
               visibility_filters = cached_filters.get("filters", {"user_segment_ids": []})
               print(
                   f"FILTER: Using cached filters for conversation {conversation_id}: {visibility_filters}",
                   flush=True,
               )
           else:
               # First message — resolve and cache for this conversation
               resolved_email, visibility_filters = self._resolve_user_and_filters(
                   user_email,
                   user_external_id,
                   user_id,
               )
               self.conversation_ticket_store.save_visibility_filters(
                   conversation_id=conversation_id,
                   email=resolved_email,
                   filters=visibility_filters,
               )
               print(
                   f"FILTER: Resolved and cached filters for conversation {conversation_id}: {visibility_filters}",
                   flush=True,
               )
       else:
           resolved_email = stored_email
           visibility_filters = {"visibility": "public"}
       # ==============================================================
       # MEMORY — add current user message FIRST so that
       # format_history_for_prompt includes the current turn.
       #
       # Order:
       #   1. add user message     <- current question is now in history
       #   2. build chat_history   <- includes current question as last line
       #   3. call LLM             <- sees full context
       #   4. add assistant reply  <- stored after answer is known
       # ==============================================================
       self.conversation_memory_service.add_message(
           conversation_id=conversation_id,
           role="user",
           text=text,
       )
       chat_history = self.conversation_memory_service.format_history_for_prompt(
           conversation_id
       )
       # ==============================================================
       # AI RESPONSE
       # ==============================================================
       self._send_typing_safe(conversation_id)
       result = self.answer_question_use_case.execute(
           question=user_text,
           visibility_filters=visibility_filters,
           chat_history=chat_history,
       )
       answer_text = result.get("answer", "")
       # ==============================================================
       # MEMORY — store assistant reply after answer is generated
       # ==============================================================
       self.conversation_memory_service.add_message(
           conversation_id=conversation_id,
           role="assistant",
           text=answer_text,
       )
       # ==============================================================
       # SEND ANSWER
       # ==============================================================
       self.chat_platform.send_message(
           conversation_id=conversation_id,
           text=answer_text,
           images=[],
       )
       # ==============================================================
       # FEEDBACK BUTTONS
       # ==============================================================
       self.chat_platform.send_message(
           conversation_id=conversation_id,
           text="Was this helpful?",
           images=[],
           actions=[
               {"type": "reply", "text": "👍 Yes", "payload": "feedback_yes"},
               {"type": "reply", "text": "👎 No", "payload": "feedback_no"},
           ],
       )
       # ==============================================================
       # TICKET SYNC
       # Pass pre-fetched ticket_data to avoid second store lookup.
       # ==============================================================
       try:
           self._sync_to_ticket(
               conversation_id=conversation_id,
               user_text=text,
               bot_answer=answer_text,
               resolved_email=resolved_email,
               ticket_data=ticket_data,
           )
       except Exception as sync_err:
           print(f"TICKET SYNC ERROR: {sync_err}", flush=True)
       return result