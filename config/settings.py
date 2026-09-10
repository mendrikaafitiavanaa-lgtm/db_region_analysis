"""
Config centralisée. Tout le reste du code lit ses paramètres ICI,
jamais directement via os.environ ailleurs dans le projet.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, default))


def _float(name: str, default: float) -> float:
    return float(os.getenv(name, default))


# --- MongoDB ---
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "synchronisations")
MONGO_SOURCE_COLLECTION = os.getenv("MONGO_SOURCE_COLLECTION", "db_france")
MONGO_L1_COLLECTION = os.getenv("MONGO_L1_COLLECTION", "db_france_syntheses_l1")
MONGO_L2_COLLECTION = os.getenv("MONGO_L2_COLLECTION", "db_france_syntheses_l2")
MONGO_DOMAINES_COLLECTION = os.getenv("MONGO_DOMAINES_COLLECTION", "db_france_bilans_domaines")
MONGO_GLOBAL_COLLECTION = os.getenv("MONGO_GLOBAL_COLLECTION", "db_france_rapport_mensuel")
MONGO_FINALE_COLLECTION = os.getenv("MONGO_FINALE_COLLECTION", "db_france_rapport_mensuel_finale")
MONGO_TARGET_COLLECTION = os.getenv("MONGO_TARGET_COLLECTION", "db_france_region_corse")

# --- OpenRouter ---
OPENROUTER_API_KEY = (
    os.getenv("OPENROUTER_API_KEY")
    or os.getenv("openRouter_API_KEY", "")
    or os.getenv("openrouter_api_key", "")
)
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "minimax/minimax-m3:free")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# --- LLM provider selection (openrouter, google, or auto) ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto").lower()
# Ordre de priorité des providers en mode fallback (séparés par virgule, ex: "google,openrouter" ou "openrouter,google")
LLM_PROVIDER_ORDER = [
    p.strip().lower()
    for p in os.getenv("LLM_PROVIDER_ORDER", "google,openrouter").split(",")
    if p.strip()
]

# --- Google AI Studio ---
GOOGLE_AI_API_KEY = (
    os.getenv("GOOGLE_AI_API_KEY")
    or os.getenv("GEMINI_API_KEY", "")
)
GOOGLE_AI_BASE_URL = os.getenv("GOOGLE_AI_BASE_URL", "https://generativelanguage.googleapis.com")
GOOGLE_AI_MODEL = os.getenv("GOOGLE_AI_MODEL", "gemini-flash-lite-latest")

# --- Filtre temporel ---
MOIS_CIBLE = os.getenv("MOIS_CIBLE", "").strip()  # ex: "2026-08", vide = pas de filtre

# --- Performance ---
BATCH_SIZE = _int("BATCH_SIZE", 8)
PAUSE_SECONDES = _float("PAUSE_SECONDES", 1.0)
MAX_WORKERS = _int("MAX_WORKERS", 1)
MAX_DOCS_PER_RUN = _int("MAX_DOCS_PER_RUN", 0)  # 0 = illimité

# --- Maîtrise tokens / latence LLM ---
RAW_TEXT_MAX_CHARS = _int("RAW_TEXT_MAX_CHARS", 250)
LLM_MAX_TOKENS_OUTPUT = _int("LLM_MAX_TOKENS_OUTPUT", 1500)
LLM_TIMEOUT_SECONDES = _int("LLM_TIMEOUT_SECONDES", 15)
LLM_MAX_RETRIES = _int("LLM_MAX_RETRIES", 2)
# Limiteur d'appels LLM (globally across threads, ex: 15 req/min pour free tier Google)
LLM_REQUESTS_PER_MINUTE = _int("LLM_REQUESTS_PER_MINUTE", 14)
# Optionnel: budget de tokens estimés par jour (0 = désactivé)
LLM_TOKEN_BUDGET_DAILY = _int("LLM_TOKEN_BUDGET_DAILY", 0)

# --- Chemins ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
CHECKPOINT_DIR = os.path.join(BASE_DIR, ".checkpoint")


def validate():
    """Appelé au démarrage : vérifie la disponibilité d'au moins un fournisseur LLM."""
    has_google = bool((GOOGLE_AI_API_KEY or "").strip())
    has_openrouter = bool((OPENROUTER_API_KEY or "").strip())

    if LLM_PROVIDER == "auto":
        if not has_google and not has_openrouter:
            raise RuntimeError(
                "Aucune clé d'API trouvée ! Remplis GOOGLE_AI_API_KEY ou OPENROUTER_API_KEY dans .env."
            )
    elif LLM_PROVIDER in ("google", "google_aistudio", "aistudio"):
        if not has_google:
            raise RuntimeError(
                "Variables .env manquantes: GOOGLE_AI_API_KEY (ou GEMINI_API_KEY)."
            )
    elif LLM_PROVIDER == "openrouter":
        if not has_openrouter:
            raise RuntimeError(
                "Variables .env manquantes: OPENROUTER_API_KEY."
            )
    else:
        raise RuntimeError(f"LLM_PROVIDER inconnu: {LLM_PROVIDER}. Choisir 'auto', 'google', ou 'openrouter'.")

