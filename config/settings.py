"""
Config centralisée pour le pipeline d'analyse territoriale Corse.
Supporte :
- 4 collections sources hétérogènes (Corse-du-Sud, Haute-Corse, Region-Corse, Corse)
- 3 collections cibles unifiées (Syntheses, Domaines, Finale)
- 4 fournisseurs LLM gratuits (Groq, Google Gemini, OpenRouter, Hugging Face)
"""
import os
from typing import List, Dict


def _load_env_file():
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_file = os.path.join(base, ".env")
        if os.path.exists(env_file):
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k not in os.environ:
                            os.environ[k] = v
            except Exception:
                pass

_load_env_file()


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except Exception:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except Exception:
        return default


# --- MongoDB Connection ---
MONGO_URI = (
    os.getenv("MONGO_URI")
    or os.getenv("MONGODB_URI")
    or "mongodb://localhost:27017/"
).strip()
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "France-Corse").strip()

# --- 4 Collections Sources Hétérogènes ---
MONGO_SOURCE_COLLECTION_A = os.getenv("MONGO_SOURCE_COLLECTION_A", "Corse-du-Sud").strip()
MONGO_SOURCE_COLLECTION_B = os.getenv("MONGO_SOURCE_COLLECTION_B", "Haute-Corse").strip()
MONGO_SOURCE_COLLECTION_C = os.getenv("MONGO_SOURCE_COLLECTION_C", "Region-Corse").strip()
MONGO_SOURCE_COLLECTION_D = os.getenv("MONGO_SOURCE_COLLECTION_D", "Corse").strip()

# Compatibilité et registre des sources
MONGO_SOURCE_COLLECTION = os.getenv("MONGO_SOURCE_COLLECTION", MONGO_SOURCE_COLLECTION_A).strip().lstrip("=")

def get_source_collections() -> List[str]:
    """Retourne la liste ordonnée et unique des collections sources configurées."""
    sources = []
    for coll in [
        MONGO_SOURCE_COLLECTION_A,
        MONGO_SOURCE_COLLECTION_B,
        MONGO_SOURCE_COLLECTION_C,
        MONGO_SOURCE_COLLECTION_D,
    ]:
        if coll and coll not in sources:
            sources.append(coll)
    if not sources:
        sources = [MONGO_SOURCE_COLLECTION]
    return sources


# --- 3 Collections Cibles Unifiées (Option B) ---
# 1. Collection Terrain (Stages 1 et 2 : L1 + L2)
MONGO_SYNTHESES_COLLECTION = (
    os.getenv("MONGO_SYNTHESES_COLLECTION")
    or os.getenv("MONGO_L1_COLLECTION")
    or "France_Corse_syntheses_analysis"
).strip().lstrip("=")

# 2. Collection Stratégique (Stages 3 et 4 : Bilans domaines + Rapport global)
MONGO_DOMAINES_COLLECTION = (
    os.getenv("MONGO_DOMAINES_COLLECTION")
    or "France_Corse_domaines_analysis"
).strip().lstrip("=")

# 3. Collection Finale Décideurs (Stage 5 : Synthèse mensuelle arbitrage)
MONGO_FINALE_COLLECTION = (
    os.getenv("MONGO_FINALE_COLLECTION")
    or "France_Corse_mensuel_analysis"
).strip().lstrip("=")

# Alias de compatibilité
MONGO_L1_COLLECTION = MONGO_SYNTHESES_COLLECTION
MONGO_L2_COLLECTION = MONGO_SYNTHESES_COLLECTION
MONGO_GLOBAL_COLLECTION = MONGO_DOMAINES_COLLECTION


# --- LLM Providers Configuration (Cascade 3 Providers: Google -> OpenRouter -> NVIDIA) ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto").lower()
LLM_COOLDOWN_HOURS = _float("LLM_COOLDOWN_HOURS", 0.0)
LLM_PROVIDER_ORDER = [
    p.strip().lower()
    for p in os.getenv("LLM_PROVIDER_ORDER", "google,openrouter,nvidia").split(",")
    if p.strip()
]

# 1. Google AI Studio (Gemini Flash)
GOOGLE_AI_API_KEY = (
    os.getenv("GOOGLE_AI_API_KEY")
    or os.getenv("GEMINI_API_KEY", "")
).strip().strip('"').strip("'")
GOOGLE_AI_BASE_URL = os.getenv("GOOGLE_AI_BASE_URL", "https://generativelanguage.googleapis.com").strip()
GOOGLE_AI_MODEL = os.getenv("GOOGLE_AI_MODEL", "gemini-flash-lite-latest").strip()

# 2. OpenRouter
OPENROUTER_API_KEY = (
    os.getenv("OPENROUTER_API_KEY")
    or os.getenv("openRouter_API_KEY", "")
    or os.getenv("openrouter_api_key", "")
).strip().strip('"').strip("'")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free").strip()
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()
OPENROUTER_FALLBACK_MODELS = ["openrouter/free"]

# 3. NVIDIA NIM (DeepSeek / Llama / Nemotron)
NVIDIA_API_KEY = (
    os.getenv("NVIDIA_API_KEY")
    or os.getenv("NVDIA_API_KEY")
    or os.getenv("NVIDIA_AI_API_KEY", "")
).strip().strip('"').strip("'")
NVIDIA_MODEL = (
    os.getenv("NVIDIA_MODEL")
    or os.getenv("NVDIA_MODEL")
    or "deepseek-ai/deepseek-v4.1-flash"
).strip()
NVIDIA_BASE_URL = (
    os.getenv("NVIDIA_BASE_URL")
    or os.getenv("NVDIA_BASE_URL")
    or "https://integrate.api.nvidia.com/v1"
).strip()
NVIDIA_FALLBACK_MODELS = [
    "deepseek-ai/deepseek-v4.1-flash",
    "meta/llama-3.3-70b-instruct",
    "mistralai/mistral-large-2-instruct",
    "deepseek-ai/deepseek-r1",
]


# --- Filtre temporel et territorial ---
MOIS_CIBLE = os.getenv("MOIS_CIBLE", "2026-08").strip()
REGION = os.getenv("REGION", "Corse").strip()

# --- Performance & Découpage par Lots ---
BATCH_SIZE = _int("BATCH_SIZE", 8)
PAUSE_SECONDES = _float("PAUSE_SECONDES", 1.5)
MAX_WORKERS = _int("MAX_WORKERS", 1)
MAX_DOCS_PER_RUN = _int("MAX_DOCS_PER_RUN", 0)  # 0 = illimité

# --- Maîtrise tokens / latence LLM ---
RAW_TEXT_MAX_CHARS = _int("RAW_TEXT_MAX_CHARS", 250)
LLM_MAX_TOKENS_OUTPUT = _int("LLM_MAX_TOKENS_OUTPUT", 1500)
LLM_TIMEOUT_SECONDES = _int("LLM_TIMEOUT_SECONDES", 45)
LLM_MAX_RETRIES = _int("LLM_MAX_RETRIES", 3)
LLM_REQUESTS_PER_MINUTE = _int("LLM_REQUESTS_PER_MINUTE", 14)
LLM_TOKEN_BUDGET_DAILY = _int("LLM_TOKEN_BUDGET_DAILY", 0)

# --- Chemins ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
CHECKPOINT_DIR = os.path.join(BASE_DIR, ".checkpoint")


def validate():
    """Appelé au démarrage : vérifie la disponibilité d'au moins un fournisseur LLM configuré."""
    has_google = bool(GOOGLE_AI_API_KEY)
    has_openrouter = bool(OPENROUTER_API_KEY)
    has_nvidia = bool(NVIDIA_API_KEY)

    available = []
    if has_google: available.append("google")
    if has_openrouter: available.append("openrouter")
    if has_nvidia: available.append("nvidia")

    if not available:
        raise RuntimeError(
            "Aucune clé d'API LLM configurée ! Veuillez remplir au moins une clé dans .env "
            "(GOOGLE_AI_API_KEY, OPENROUTER_API_KEY, ou NVIDIA_API_KEY)."
        )

    clean_provider = LLM_PROVIDER.replace("gemini", "google").replace("nvdia", "nvidia")
    if LLM_PROVIDER != "auto" and clean_provider not in available:
        raise RuntimeError(
            f"LLM_PROVIDER est réglé sur '{LLM_PROVIDER}', mais sa clé d'API est manquante ou vide dans .env. "
            f"Providers disponibles avec clé : {available}."
        )
