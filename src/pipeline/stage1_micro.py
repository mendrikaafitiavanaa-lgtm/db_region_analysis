"""
STAGE 1 : Micro-synthèses de Niveau 1 (Articles bruts -> Lots L1 par domaine).

Flux :
1. Lecture et normalisation des documents sources bruts restants (exclut ceux déjà dans L1).
2. Regroupement thématique local FlashText (0 token LLM) par domaine.
3. Découpage en lots homogènes de N documents (ex: 6 à 8).
4. Pour chaque lot : synthèse IA consolidée via le pool multi-LLM (Groq, Gemini, OpenRouter, HF).
5. Sauvegarde dans la collection unifiée syntheses_analysis avec traçabilité complète.
"""
import time
from datetime import datetime, timezone
from typing import Dict, Optional, List

from config import settings
from src.db import source_reader, target_writer
from src.pipeline.topic_grouper import group_documents_into_batches
from src.db.normalizer import deduplicate_documents
from src.llm.client import call_llm, call_llm_with_meta, get_error_class
from src.llm.prompts.prompt_stage1 import build_stage1_messages
from src.llm.response_parser import parse_stage1_response, ParsingError
from src.schema.analyse_schema import build_stage1_document
from src.utils.logger import get_logger
from src.llm import token_budget


def run_stage_1(
    run_id: Optional[str] = None,
    force: bool = False,
    limit: int = 0,
    territoire: Optional[str] = None,
    source_collections: Optional[List[str]] = None,
) -> Dict:
    logger = get_logger()
    settings.validate()
    target_writer.ensure_all_indexes()

    run_id = run_id or f"run_l1_{datetime.now().strftime('%Y-%m-%d_%Hh%M')}"
    logger.info(f"=== [STAGE 1] Démarrage du traitement L1 ({run_id}) ===")

    # 1. Identifier les documents déjà traités en L1
    if force:
        already_done_ids = set()
        logger.info("[STAGE 1] Mode FORCE activé : ré-analyse de l'intégralité des sources.")
    else:
        already_done_ids = source_reader.get_already_processed_ids(
            collection_name=settings.MONGO_SYNTHESES_COLLECTION,
            id_field="document_ids",
            stage_type="synthese_l1",
            require_fields=["cause", "preuve"],
            territoire=territoire,
        )

    # 2. Charger les documents sources non traités ou nécessitant mise à jour
    max_to_load = settings.MAX_DOCS_PER_RUN
    all_pending_docs = source_reader.read_all_pending_sources(
        exclude_ids=already_done_ids,
        source_collections=source_collections,
        mois_cible=settings.MOIS_CIBLE,
        max_docs=max_to_load,
    )

    total_loaded = len(all_pending_docs)
    logger.info(
        f"[STAGE 1] Documents sources déjà à jour en L1 : {len(already_done_ids)}. "
        f"Restant à traiter : {total_loaded}."
    )

    if total_loaded == 0:
        logger.info("[STAGE 1] Toutes les micro-synthèses L1 sont à jour pour le périmètre demandé.")
        return {"statut": "termine", "total_lots": 0, "succes": 0, "erreurs": 0}

    # 2bis. Déduplication : fusionne les posts quasi-identiques (ex: "Baromètre
    # Citoyen" gabarité republié des centaines de fois) en 1 seul document
    # annoté d'un compteur d'occurrences, pour ne pas noyer le LLM sous du bruit
    # répétitif et gaspiller des tokens sur du contenu non informatif.
    deduped_docs = deduplicate_documents(all_pending_docs)
    if len(deduped_docs) < total_loaded:
        logger.info(
            f"[STAGE 1] Déduplication : {total_loaded} docs -> {len(deduped_docs)} "
            f"documents uniques ({total_loaded - len(deduped_docs)} doublons fusionnés)."
        )

    # 3. Regroupement thématique FlashText par domaine strict
    batches = group_documents_into_batches(
        documents=deduped_docs,
        batch_size=settings.BATCH_SIZE,
    )
    total_lots = len(batches)
    
    # Appliquer la limite de session (--limit) si demandée
    if limit > 0 and limit < total_lots:
        logger.info(f"[STAGE 1] Limite de session activée : traitement de {limit} lots sur {total_lots}.")
        batches = batches[:limit]
        total_lots = len(batches)
    else:
        logger.info(f"[STAGE 1] Regroupement thématique : {total_lots} lots L1 à traiter.")

    total_ok = 0
    total_erreurs = 0
    start_time = time.time()

    for idx, batch in enumerate(batches, start=1):
        domaine = batch.get("domaine", "general")
        docs = batch.get("documents", [])
        lot_start = time.time()

        logger.info(f"[STAGE 1] Lot {idx}/{total_lots} [{domaine.upper()}] ({len(docs)} docs)...")

        try:
            messages = build_stage1_messages(docs, domaine=domaine)
            raw_resp, used_provider = call_llm_with_meta(messages)
            analyse = parse_stage1_response(raw_resp)

            doc_l1 = build_stage1_document(
                source_docs=docs,
                analyse=analyse,
                domaine=domaine,
                run_id=run_id,
                lot_numero=idx,
                territoire=territoire,
                provider=used_provider,
            )

            target_writer.save_synthese_l1(doc_l1)
            total_ok += 1
            lot_dur = time.time() - lot_start
            logger.info(f"-> [STAGE 1] Lot {idx} OK (gravité={doc_l1.get('gravite')}, provider={used_provider}) en {lot_dur:.1f}s")

        except token_budget.BudgetExceeded as be:
            logger.warning(f"[STAGE 1] Arrêt: budget token atteint: {be}")
            break
        except (get_error_class(), ParsingError, Exception) as exc:
            total_erreurs += 1
            logger.error(f"-> [STAGE 1] Lot {idx} ÉCHEC: {exc}")

        if settings.PAUSE_SECONDES > 0:
            time.sleep(settings.PAUSE_SECONDES)

    total_duration = time.time() - start_time
    logger.info(
        f"=== [STAGE 1 TERMINÉ] {total_ok} synthèses L1 sauvegardées, "
        f"{total_erreurs} erreurs, en {total_duration:.1f}s ==="
    )

    return {
        "statut": "termine",
        "total_lots": total_lots,
        "succes": total_ok,
        "erreurs": total_erreurs,
        "duree_secondes": round(total_duration, 2),
    }