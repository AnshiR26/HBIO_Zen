import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

DATA_DIR = os.environ.get("DATA_DIR", "/home/data")
PDF_DIR = os.path.join(DATA_DIR, "pdfs")
CHROMA_DIR = os.path.join(DATA_DIR, "chroma_db")
IMAGE_DIR = os.path.join(DATA_DIR, "extracted_images")

COLLECTION_NAME = os.getenv("COLLECTION_NAME", "pdf_rag_collection")
IMAGE_COLLECTION_NAME = os.getenv("IMAGE_COLLECTION_NAME", "pdf_image_collection")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "120"))
TOP_K = int(os.getenv("TOP_K", "4"))

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
CHROMA_SSL = os.getenv("CHROMA_SSL", "false").lower() == "true"
CHROMA_TENANT = os.getenv("CHROMA_TENANT", "default_tenant")
CHROMA_DATABASE = os.getenv("CHROMA_DATABASE", "default_database")

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

SC_KEY_ID = os.getenv("SC_KEY_ID")
SC_SECRET = os.getenv("SC_SECRET")
SC_APP_ID = os.getenv("SC_APP_ID")
ZENDESK_SUBDOMAIN = os.getenv("ZENDESK_SUBDOMAIN")

ZENDESK_EMAIL = os.getenv("ZENDESK_EMAIL")
ZENDESK_API_TOKEN = os.getenv("ZENDESK_API_TOKEN")
ZENDESK_LOCALE = os.getenv("ZENDESK_LOCALE", "en-us")

STATE_FILE = os.path.join(BASE_DIR, "zendesk_sync_state.json")

AZURE_SEARCH_ENDPOINT = os.getenv(
   "AZURE_SEARCH_ENDPOINT",
   ""
)
AZURE_SEARCH_API_KEY = os.getenv(
   "AZURE_SEARCH_API_KEY",
   ""
)
AZURE_SEARCH_INDEX_NAME = os.getenv(
   "AZURE_SEARCH_INDEX_NAME",
   "zendesk-knowledge-index"
)