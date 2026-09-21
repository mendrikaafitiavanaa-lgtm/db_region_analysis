"""
Wrapper LLM avec basculement automatique (failover) multi-fournisseurs.

Supporte 4 fournisseurs gratuits en cascade :
1. Groq (Llama 3.3 / Mixtral)
2. Google Gemini (Flash Lite)
3. OpenRouter (Free models)
4. Hugging Face (Inference Router)

En cas d'erreur de quota (HTTP 429/402), bascule automatiquement sur le fournisseur suivant
sans interrompre le traitement.
"""
import logging
from typing import List, Tuple
from config import settings
from src.llm import cooldown_manager
from src.llm.rate_limiter import global_rate_limiter
from src.llm import token_budget
from src.llm import groq_client
from src.llm import google_client
from src.llm import openrouter_client
from src.llm import huggingface_client

logger = logging.getLogger("scraper_logger")

_LAST_PROVIDER_USED = "groq"


class LLMError(Exception):
    pass


# Tuple de toutes les exceptions de quota pour interception standardisée
QUOTA_EXCEPTIONS = (
    groq_client.GroqQuotaError,
    google_client.GoogleQuotaError,
    openrouter_client.OpenRouterQuotaError,
    huggingface_client.HuggingFaceQuotaError,
)


def get_last_provider_used() -> str:
    """Retourne le nom du dernier fournisseur LLM ayant répondu avec succès."""
    return _LAST_PROVIDER_USED


def _get_provider_pipeline() -> List[Tuple[str, callable]]:
    """Retourne la liste ordonnée des fournisseurs à essayer selon la configuration."""
    pipeline = []
    order = settings.LLM_PROVIDER_ORDER if settings.LLM_PROVIDER == "auto" else [settings.LLM_PROVIDER]

    for p in order:
        p_clean = p.strip().lower()
        if p_clean in ("groq", "grok"):
            pipeline.append(("groq", groq_client.call_llm))
        elif p_clean in ("google", "google_aistudio", "aistudio", "gemini"):
            pipeline.append(("google", google_client.call_llm))
        elif p_clean == "openrouter":
            pipeline.append(("openrouter", openrouter_client.call_llm))
        elif p_clean in ("huggingface", "hf", "hugginface"):
            pipeline.append(("huggingface", huggingface_client.call_llm))

    if not pipeline:
        # Ordre de fallback par défaut complet
        pipeline = [
            ("groq", groq_client.call_llm),
            ("google", google_client.call_llm),
            ("openrouter", openrouter_client.call_llm),
            ("huggingface", huggingface_client.call_llm),
        ]

    return pipeline


def call_llm_with_meta(messages: list) -> Tuple[str, str]:
    """Appelle le pool de LLM et retourne un tuple (texte_reponse, nom_fournisseur)."""
    global _LAST_PROVIDER_USED
    
    # 1. Estimation tokens prompt
    prompt_tokens = token_budget.estimate_tokens_for_messages(messages)

    # 2. Vérification budget journalier si configuré
    if settings.LLM_TOKEN_BUDGET_DAILY and settings.LLM_TOKEN_BUDGET_DAILY > 0:
        consumed = token_budget.get_consumed_today()
        remaining = settings.LLM_TOKEN_BUDGET_DAILY - consumed
        reserved_estimate = prompt_tokens + int(settings.LLM_MAX_TOKENS_OUTPUT)
        if remaining <= 0:
            raise token_budget.BudgetExceeded("Budget journalier de tokens atteint. Arrêt des appels LLM.")
        if reserved_estimate > remaining:
            raise token_budget.BudgetExceeded(
                f"Budget journalier insuffisant (nécessite ~{reserved_estimate} tokens, reste {remaining})."
            )

    # 3. Rate limiter
    try:
        global_rate_limiter.acquire()
    except Exception:
        pass

    pipeline = _get_provider_pipeline()

    # Filtrer les fournisseurs disponibles selon le statut de cooldown
    available_providers = [
        (name, fn) for name, fn in pipeline
        if cooldown_manager.is_provider_available(name)
    ]

    # Si tous les fournisseurs sont actuellement bloqués par un cooldown actif
    if not available_providers:
        status_details = []
        for name, _ in pipeline:
            rem = cooldown_manager.get_remaining_cooldown_seconds(name)
            rem_str = cooldown_manager.format_remaining_time(rem)
            status_details.append(f"{name.upper()} (cooldown restant: {rem_str})")
        details_str = ", ".join(status_details)
        raise LLMError(
            f"Tous les fournisseurs LLM sont actuellement bloqués par un cooldown. [{details_str}]. "
            f"Attendez la fin du cooldown ou vérifiez vos clés API dans le fichier .env."
        )

    last_exc = None

    for provider_name, call_fn in available_providers:
        try:
            raw = call_fn(messages)

            # Enregistrer consommation tokens
            try:
                resp_tokens = token_budget.estimate_tokens_from_text(raw)
                token_budget.add_consumed(prompt_tokens + resp_tokens)
            except Exception:
                pass

            _LAST_PROVIDER_USED = provider_name
            return raw, provider_name

        except QUOTA_EXCEPTIONS as quota_err:
            cooldown_manager.mark_cooldown(
                provider_name=provider_name,
                reason=str(quota_err),
                duration_hours=settings.LLM_COOLDOWN_HOURS,
            )
            logger.warning(
                f"⚠️ [FAILOVER] Quota/Limite 429 atteinte sur '{provider_name.upper()}'. "
                f"Bascule automatique vers le fournisseur suivant..."
            )
            last_exc = quota_err
            continue

        except Exception as exc:
            # Si erreur générique ou réseau, tenter aussi le fallback si d'autres fournisseurs disponibles
            if settings.LLM_PROVIDER == "auto" and len(available_providers) > 1:
                logger.warning(
                    f"⚠️ [FAILOVER] Erreur sur '{provider_name.upper()}': {exc}. "
                    f"Bascule automatique vers le fournisseur suivant..."
                )
                last_exc = exc
                continue
            raise LLMError(f"[{provider_name}] {exc}") from exc

    raise LLMError(f"Tous les fournisseurs LLM disponibles ont échoué. Dernière erreur: {last_exc}")


def call_llm(messages: list) -> str:
    """Appelle le pool de LLM avec failover automatique sur 429/quota."""
    raw, _ = call_llm_with_meta(messages)
    return raw


def get_error_class():
    return LLMError
