"""
STAGE 4 : Rapport Stratégique Territorial Global (Sommet de la Pyramide).

Flux :
1. Lecture de tous les bilans mensuels de domaines (Stage 3).
2. Appel unique au LLM pour la synthèse macro-territoriale croisée.
3. Sauvegarde dans la collection rapport_global_mensuel.
"""
import time
from datetime import datetime
from typing import Dict, Optional

from config import settings
from src.db import source_reader, target_writer
from src.llm.client import call_llm, get_error_class
from src.llm.prompts.prompt_stage4 import build_stage4_messages
from src.llm.response_parser import parse_stage4_response, ParsingError
from src.schema.analyse_schema import build_stage4_document
from src.utils.logger import get_logger
from src.llm import token_budget


def run_stage_4(run_id: Optional[str] = None) -> Dict:
    logger = get_logger()
    settings.validate()
    target_writer.ensure_all_indexes()

    run_id = run_id or f"run_l4_{datetime.now().strftime('%Y-%m-%d_%Hh%M')}"
    logger.info(f"=== [STAGE 4] Génération du Rapport Territorial Global ({run_id}) ===")

    # 1. Charger tous les bilans de domaine
    domain_bilans = source_reader.read_stage_documents(
        collection_name=settings.MONGO_DOMAINES_COLLECTION,
        stage_type="bilan_domaine",
    )

    if not domain_bilans:
        logger.warning("[STAGE 4] Aucun bilan de domaine trouvé. Veuillez d'abord exécuter le Stage 3.")
        return {"statut": "erreur", "erreur": "Aucun bilan de domaine trouvé"}

    logger.info(f"[STAGE 4] {len(domain_bilans)} bilans de domaine chargés pour le rapport global.")

    start_time = time.time()
    mois_label = settings.MOIS_CIBLE or "2026-08"
    region_label = settings.REGION or "region_corse_sud"

    try:
        messages = build_stage4_messages(domain_bilans, mois=mois_label, region=region_label)
        raw_resp = call_llm(messages)
        analyse = parse_stage4_response(raw_resp)

        rapport_global = build_stage4_document(
            domain_bilans=domain_bilans,
            analyse=analyse,
            mois=mois_label,
            region=region_label,
            run_id=run_id,
        )

        target_writer.save_rapport_global(rapport_global)
        duration = time.time() - start_time

        logger.info(
            f"=== [STAGE 4 TERMINÉ] 🎯 RAPPORT GLOBAL GÉNÉRÉ avec succès en {duration:.1f}s ! ===\n"
            f"Titre : {rapport_global.get('titre')}\n"
            f"Statut général : {rapport_global.get('statut_general')}\n"
            f"Total sources analysées : {rapport_global.get('total_documents_sources_couverts')} articles.\n"
        )

        return {
            "statut": "termine",
            "titre": rapport_global.get("titre"),
            "statut_general": rapport_global.get("statut_general"),
            "total_sources": rapport_global.get("total_documents_sources_couverts"),
            "duree_secondes": round(duration, 2),
        }

    except token_budget.BudgetExceeded as be:
        logger.warning(f"[STAGE 4] Arrêt: budget token atteint: {be}")
        return {"statut": "erreur", "erreur": str(be)}
    except (get_error_class(), ParsingError, Exception) as exc:
        logger.error(f"[STAGE 4] ÉCHEC génération rapport global: {exc}")
        return {"statut": "erreur", "erreur": str(exc)}
