"""
Config centralisée. Tout le reste du code lit ses paramètres ICI,
"""
import os


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
    return int(os.getenv(name, default))


def _float(name: str, default: float) -> float:
    return float(os.getenv(name, default))


# --- MongoDB (3 collections de destination + 1 source) ---
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/").strip()
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "France-Corse").strip()
MONGO_SOURCE_COLLECTION = os.getenv("MONGO_SOURCE_COLLECTION", "Corse-du-Sud").strip().lstrip("=")

# 1. Collection Terrain (Stages 1 et 2 : L1 + L2)
MONGO_SYNTHESES_COLLECTION = os.getenv(
    "MONGO_SYNTHESES_COLLECTION",
    os.getenv("MONGO_L1_COLLECTION", "Corse_Sud_syntheses_analysis"),
).strip().lstrip("=")

# 2. Collection Stratégique (Stages 3 et 4 : Bilans domaines + Rapport global)
MONGO_DOMAINES_COLLECTION = os.getenv(
    "MONGO_DOMAINES_COLLECTION", "Corse_Sud_domaines_analysis"
).strip().lstrip("=")

# 3. Collection Finale Décideurs (Stage 5 : Synthèse mensuelle arbitrage)
MONGO_FINALE_COLLECTION = os.getenv(
    "MONGO_FINALE_COLLECTION", "Corse_Sud_mensuel_analysis"
).strip().lstrip("=")

# Alias de compatibilité
MONGO_L1_COLLECTION = MONGO_SYNTHESES_COLLECTION
MONGO_L2_COLLECTION = MONGO_SYNTHESES_COLLECTION
MONGO_GLOBAL_COLLECTION = MONGO_DOMAINES_COLLECTION


# --- OpenRouter ---
OPENROUTER_API_KEY = (
    os.getenv("OPENROUTER_API_KEY")
    or os.getenv("openRouter_API_KEY", "")
    or os.getenv("openrouter_api_key", "")
)
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
# Les modèles libres changent souvent. Pour éviter les 404/402 inutiles, on garde uniquement le modèle connu valide
# et on laisse le failover automatique décider sans enchaîner des slugs inaccessibles.
OPENROUTER_FALLBACK_MODELS = [
    "openrouter/free",
]

# --- LLM provider selection & failover ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto").lower()
# 0 = cooldown désactivé ; cela évite de bloquer indéfiniment un fournisseur sur un vieux fichier de checkpoint
LLM_COOLDOWN_HOURS = _float("LLM_COOLDOWN_HOURS", 0.0)
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

# --- Filtre temporel et territorial ---
MOIS_CIBLE = os.getenv("MOIS_CIBLE", "2026-08").strip()  # ex: "2026-08", vide = pas de filtre
REGION = os.getenv("REGION", "region_corse_sud").strip()  # ex: "region_corse_sud"

# --- Performance ---
BATCH_SIZE = _int("BATCH_SIZE", 8)
PAUSE_SECONDES = _float("PAUSE_SECONDES", 1.5)
MAX_WORKERS = _int("MAX_WORKERS", 1)
MAX_DOCS_PER_RUN = _int("MAX_DOCS_PER_RUN", 0)  # 0 = illimité

# --- Maîtrise tokens / latence LLM ---
RAW_TEXT_MAX_CHARS = _int("RAW_TEXT_MAX_CHARS", 250)
LLM_MAX_TOKENS_OUTPUT = _int("LLM_MAX_TOKENS_OUTPUT", 1500)
LLM_TIMEOUT_SECONDES = _int("LLM_TIMEOUT_SECONDES", 45)
LLM_MAX_RETRIES = _int("LLM_MAX_RETRIES", 3)
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

