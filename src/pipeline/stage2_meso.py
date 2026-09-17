"""
STAGE 2 : Méso-synthèses de Niveau 2 (Synthèses L1 -> Lots L2 consolidés par domaine).

Flux :
1. Lecture des synthèses L1 disponibles (exclut celles déjà consolidées en L2).
2. Regroupement thématique strict par domaine.
3. Découpage en paquets de N synthèses L1 (ex: 6 à 8).
4. Pour chaque paquet : synthèse consolidée IA.
5. Sauvegarde dans la collection syntheses_l2.
"""
import time
from datetime import datetime
from typing import Dict, Optional

from config import settings
from src.db import source_reader, target_writer
from src.pipeline.topic_grouper import group_documents_into_batches
from src.llm.client import call_llm, get_error_class
from src.llm.prompts.prompt_stage2 import build_stage2_messages
from src.llm.response_parser import parse_stage2_response, ParsingError
from src.schema.analyse_schema import build_stage2_document
from src.utils.logger import get_logger
from src.llm import token_budget


def run_stage_2(run_id: Optional[str] = None, force: bool = False) -> Dict:
    logger = get_logger()
    settings.validate()
    target_writer.ensure_all_indexes()

    run_id = run_id or f"run_l2_{datetime.now().strftime('%Y-%m-%d_%Hh%M')}"
    logger.info(f"=== [STAGE 2] Démarrage du traitement L2 ({run_id}) ===")

    # 1. Identifier les synthèses L1 déjà consolidées en L2 (avec cause et preuve)
    if force:
        already_done_l1_ids = set()
        logger.info("[STAGE 2] Mode FORCE activé : ré-analyse de l'intégralité des synthèses L1.")
    else:
        already_done_l1_ids = source_reader.get_already_processed_ids(
            collection_name=settings.MONGO_SYNTHESES_COLLECTION,
            id_field="l1_synthese_ids",
            stage_type="synthese_l2",
            require_fields=["cause", "preuve"],
        )

    # 2. Charger toutes les synthèses L1
    all_l1_docs = source_reader.read_stage_documents(
        collection_name=settings.MONGO_SYNTHESES_COLLECTION,
        stage_type="synthese_l1",
    )

    # Filtrer celles non traitées ou nécessitant consolidation
    pending_l1_docs = [doc for doc in all_l1_docs if str(doc.get("_id")) not in already_done_l1_ids]

    logger.info(
        f"[STAGE 2] Total L1 existants: {len(all_l1_docs)}. "
        f"Déjà consolidés en L2 (avec cause et preuve): {len(already_done_l1_ids)}. "
        f"Restant à traiter/mettre à jour: {len(pending_l1_docs)}."
    )

    if not pending_l1_docs:
        logger.info("[STAGE 2] Toutes les méso-synthèses L2 sont à jour (avec cause et preuve).")
        return {"statut": "termine", "total_lots": 0, "succes": 0, "erreurs": 0}

    # 3. Regroupement par domaine
    batches = group_documents_into_batches(
        documents=pending_l1_docs,
        batch_size=settings.BATCH_SIZE,
    )
    total_lots = len(batches)
    logger.info(f"[STAGE 2] Regroupement : {total_lots} lots L2 générés.")

    total_ok = 0
    total_erreurs = 0
    start_time = time.time()

    for idx, batch in enumerate(batches, start=1):
        domaine = batch.get("domaine", "general")
        docs_l1 = batch.get("documents", [])
        lot_start = time.time()

        logger.info(f"[STAGE 2] Lot {idx}/{total_lots} [{domaine.upper()}] ({len(docs_l1)} synthèses L1)...")

        try:
            messages = build_stage2_messages(docs_l1, domaine=domaine)
            raw_resp = call_llm(messages)
            analyse = parse_stage2_response(raw_resp)

            doc_l2 = build_stage2_document(
                l1_docs=docs_l1,
                analyse=analyse,
                domaine=domaine,
                run_id=run_id,
                lot_numero=idx,
            )

            target_writer.save_synthese_l2(doc_l2)
            total_ok += 1
            lot_dur = time.time() - lot_start
            logger.info(f"-> [STAGE 2] Lot {idx} OK (gravité={doc_l2.get('gravite')}) en {lot_dur:.1f}s")

        except token_budget.BudgetExceeded as be:
            logger.warning(f"[STAGE 2] Arrêt: budget token atteint: {be}")
            break
        except (get_error_class(), ParsingError, Exception) as exc:
            total_erreurs += 1
            logger.error(f"-> [STAGE 2] Lot {idx} ÉCHEC: {exc}")

        if settings.PAUSE_SECONDES > 0:
            time.sleep(settings.PAUSE_SECONDES)

    total_duration = time.time() - start_time
    logger.info(
        f"=== [STAGE 2 TERMINÉ] {total_ok} synthèses L2 sauvegardées, "
        f"{total_erreurs} erreurs, en {total_duration:.1f}s ==="
    )

    return {
        "statut": "termine",
        "total_lots": total_lots,
        "succes": total_ok,
        "erreurs": total_erreurs,
        "duree_secondes": round(total_duration, 2),
    }
