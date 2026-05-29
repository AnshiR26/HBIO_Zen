import os
from app.config.settings import (
    TOP_K,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    PUBLIC_BASE_URL,
    ZENDESK_SUBDOMAIN,
    ZENDESK_EMAIL,
    ZENDESK_API_TOKEN,
    SC_APP_ID,
    SC_KEY_ID,
    SC_SECRET,
    DATA_DIR,
)
from app.adapters.embeddings.sentence_transformer_adapter import SentenceTransformerAdapter
from app.adapters.llm.groq_adapter import GroqAdapter
from app.adapters.stores.azure_ai_search_store import AzureAISearchKnowledgeStore 
from app.adapters.sources.zendesk_helpcenter_source import ZendeskHelpCenterSource
from app.adapters.chat.sunshine_chat_adapter import SunshineChatAdapter
from app.services.prompt_service import PromptService
from app.services.image_service import ImageService
from app.services.webhook_parser_service import WebhookParserService
from app.services.ticket_intent_service import TicketIntentService
from app.services.conversation_state_service import ConversationStateService
from app.services.zendesk_ticket_service import ZendeskTicketService
from app.adapters.storage.json_sync_state_adapter import JsonSyncStateAdapter
from app.adapters.storage.json_conversation_ticket_store import JsonConversationTicketStore
from app.adapters.http.http_image_downloader_adapter import HttpImageDownloaderAdapter
from app.adapters.storage.local_image_storage_adapter import LocalImageStorageAdapter
from app.use_cases.answer_question import AnswerQuestionUseCase
from app.use_cases.handle_webhook_message import HandleWebhookMessageUseCase
from app.use_cases.sync_zendesk_articles import SyncZendeskArticlesUseCase
from app.services.conversation_memory_service import ConversationMemoryService


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


class Container:
    def __init__(self):
        self.embedder = SentenceTransformerAdapter()
        self.llm = GroqAdapter()
        self.knowledge_store = AzureAISearchKnowledgeStore()
        self.knowledge_source = ZendeskHelpCenterSource(
            subdomain="datasci",
            email="jdoyle@harvardbioscience.com",
            api_token="HcEoVxUOYxrvRsPJwOsPAyMm9FskF5gSYNa49xQ8",
            locale="en-us"
        )
        self.chat_platform = SunshineChatAdapter()
        self.conversation_memory_service = ConversationMemoryService(
            filepath=os.path.join(DATA_DIR, "conversation_memory.json")
        )

        self.prompt_service = PromptService()
        self.image_service = ImageService(public_base_url=PUBLIC_BASE_URL)
        self.webhook_parser_service = WebhookParserService()
        self.ticket_intent_service = TicketIntentService()
        self.conversation_state_service = ConversationStateService()
        self.zendesk_ticket_service = ZendeskTicketService(
            subdomain=ZENDESK_SUBDOMAIN,
            email=ZENDESK_EMAIL,
            api_token=ZENDESK_API_TOKEN,
            sc_app_id=SC_APP_ID,
            sc_key_id=SC_KEY_ID,
            sc_secret=SC_SECRET,
        )

        self.sync_state = JsonSyncStateAdapter()
        self.image_downloader = HttpImageDownloaderAdapter()
        self.image_storage = LocalImageStorageAdapter()

        
        self.conversation_ticket_store = JsonConversationTicketStore(
            filepath=os.path.join(DATA_DIR, "conversation_tickets.json")
        )

        self.answer_question_use_case = AnswerQuestionUseCase(
            embedder=self.embedder,
            knowledge_store=self.knowledge_store,
            llm=self.llm,
            prompt_service=self.prompt_service,
            image_service=self.image_service,
            top_k=TOP_K,
        )

        self.handle_webhook_message_use_case = HandleWebhookMessageUseCase(
            answer_question_use_case=self.answer_question_use_case,
            chat_platform=self.chat_platform,
            ticket_intent_service=self.ticket_intent_service,
            conversation_state_service=self.conversation_state_service,
            zendesk_ticket_service=self.zendesk_ticket_service,
            conversation_ticket_store=self.conversation_ticket_store,
            conversation_memory_service=self.conversation_memory_service,
        )

        self.sync_zendesk_articles_use_case = SyncZendeskArticlesUseCase(
            source=self.knowledge_source,
            embedder=self.embedder,
            knowledge_store=self.knowledge_store,
            chunker=chunk_text,
            sync_state=self.sync_state,
            image_downloader=self.image_downloader,
            image_storage=self.image_storage,
        )
        