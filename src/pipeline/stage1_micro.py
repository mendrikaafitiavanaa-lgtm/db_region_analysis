"""
STAGE 1 : Micro-synthèses de Niveau 1 (Articles bruts -> Lots L1 par domaine).

Flux :
1. Lecture des documents sources bruts restants (exclut ceux déjà dans L1).
2. Regroupement thématique local FlashText (0 token LLM) étanche par domaine.
3. Découpage en lots homogènes de N documents (ex: 6 à 8).
4. Pour chaque lot : synthèse IA consolidée (1 seul appel LLM).
5. Sauvegarde dans la collection syntheses_l1.
"""
import time
from datetime import datetime, timezone
from typing import Dict, Optional

from config import settings
from src.db import source_reader, target_writer
from src.pipeline.topic_grouper import group_documents_into_batches
from src.llm.client import call_llm, get_error_class
from src.llm.prompts.prompt_stage1 import build_stage1_messages
from src.llm.response_parser import parse_stage1_response, ParsingError
from src.schema.analyse_schema import build_stage1_document
from src.utils.logger import get_logger
from src.llm import token_budget


def run_stage_1(run_id: Optional[str] = None, force: bool = False) -> Dict:
    logger = get_logger()
    settings.validate()
    target_writer.ensure_all_indexes()

    run_id = run_id or f"run_l1_{datetime.now().strftime('%Y-%m-%d_%Hh%M')}"
    logger.info(f"=== [STAGE 1] Démarrage du traitement L1 ({run_id}) ===")

    # 1. Identifier les documents déjà traités en L1 (ayant bien cause et preuve)
    if force:
        already_done_ids = set()
        logger.info("[STAGE 1] Mode FORCE activé : ré-analyse de l'intégralité des sources.")
    else:
        already_done_ids = source_reader.get_already_processed_ids(
            collection_name=settings.MONGO_SYNTHESES_COLLECTION,
            id_field="document_ids",
            stage_type="synthese_l1",
            require_fields=["cause", "preuve"],
        )

    # 2. Charger les documents sources non traités ou nécessitant mise à jour
    all_pending_docs = source_reader.read_all_pending_sources(
        exclude_ids=already_done_ids,
        max_docs=settings.MAX_DOCS_PER_RUN
    )

    total_loaded = len(all_pending_docs)
    logger.info(
        f"[STAGE 1] Documents sources déjà à jour en L1 (avec cause et preuve): {len(already_done_ids)}. "
        f"Restant à traiter/mettre à jour: {total_loaded}."
    )

    if total_loaded == 0:
        logger.info("[STAGE 1] Toutes les micro-synthèses L1 sont à jour (avec cause et preuve).")
        return {"statut": "termine", "total_lots": 0, "succes": 0, "erreurs": 0}

    # 3. Regroupement thématique FlashText par domaine strict
    batches = group_documents_into_batches(
        documents=all_pending_docs,
        batch_size=settings.BATCH_SIZE,
    )
    total_lots = len(batches)
    logger.info(f"[STAGE 1] Regroupement thématique : {total_lots} lots L1 générés.")

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
            raw_resp = call_llm(messages)
            analyse = parse_stage1_response(raw_resp)

            doc_l1 = build_stage1_document(
                source_docs=docs,
                analyse=analyse,
                domaine=domaine,
                run_id=run_id,
                lot_numero=idx,
            )

            target_writer.save_synthese_l1(doc_l1)
            total_ok += 1
            lot_dur = time.time() - lot_start
            logger.info(f"-> [STAGE 1] Lot {idx} OK (gravité={doc_l1.get('gravite')}) en {lot_dur:.1f}s")

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
