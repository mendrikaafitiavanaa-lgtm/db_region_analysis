"""
STAGE 5 : Synthèse Exécutive Finale Ciblée sur le Problème Territorial N°1 (Sommet Ultime).

Flux :
1. Lecture du Rapport Global (Stage 4) et des Bilans de Domaine (Stage 3).
2. Appel unique au LLM pour l'arbitrage décisionnel :
   - Détection de l'unique problématique / domaine N°1 le plus persistant et récurrent du mois.
   - Justification de son urgence absolue.
   - Plan d'action prioritaire et solutions concrètes recommandées.
3. Sauvegarde dans la collection db_france_rapport_mensuel_finale.
"""
import time
from datetime import datetime
from typing import Dict, Optional

from config import settings
from src.db import source_reader, target_writer
from src.llm.client import call_llm, get_error_class
from src.llm.prompts.prompt_stage5 import build_stage5_messages
from src.llm.response_parser import parse_stage5_response, ParsingError
from src.schema.analyse_schema import build_stage5_document
from src.utils.logger import get_logger
from src.llm import token_budget


def run_stage_5(run_id: Optional[str] = None) -> Dict:
    logger = get_logger()
    settings.validate()
    target_writer.ensure_all_indexes()

    run_id = run_id or f"run_l5_{datetime.now().strftime('%Y-%m-%d_%Hh%M')}"
    logger.info(f"=== [STAGE 5] Démarrage de la Synthèse Exécutive Finale N°1 ({run_id}) ===")

    # 1. Charger le rapport global (Stage 4)
    rapports_l4 = source_reader.read_stage_documents(
        collection_name=settings.MONGO_GLOBAL_COLLECTION
    )

    if not rapports_l4:
        logger.warning("[STAGE 5] Aucun rapport global (Stage 4) trouvé. Veuillez d'abord exécuter le Stage 4.")
        return {"statut": "erreur", "erreur": "Aucun rapport global (Stage 4) trouvé"}

    # Prendre le plus récent
    rapport_global = rapports_l4[-1]

    # 2. Charger les bilans de domaine (Stage 3) en complément
    domain_bilans = source_reader.read_stage_documents(
        collection_name=settings.MONGO_DOMAINES_COLLECTION
    )

    start_time = time.time()
    mois_label = settings.MOIS_CIBLE or rapport_global.get("mois_cible") or "Mois d'analyse"
    region_label = rapport_global.get("region") or "Corse"

    try:
        messages = build_stage5_messages(
            rapport_global=rapport_global,
            domain_bilans=domain_bilans,
            mois=mois_label,
            region=region_label,
        )
        raw_resp = call_llm(messages)
        analyse = parse_stage5_response(raw_resp)

        finale_doc = build_stage5_document(
            rapport_global=rapport_global,
            analyse=analyse,
            mois=mois_label,
            region=region_label,
            run_id=run_id,
        )

        target_writer.save_rapport_mensuel_finale(finale_doc)
        duration = time.time() - start_time

        logger.info(
            f"=== [STAGE 5 TERMINÉ] 🏆 SYNTHÈSE FINALE N°1 GÉNÉRÉE avec succès en {duration:.1f}s ! ===\n"
            f"Domaine N°1 : {finale_doc.get('domaine_prioritaire_identifie', '').upper()}\n"
            f"Problème persistant : {finale_doc.get('probleme_majeur_persistant')}\n"
            f"Niveau d'urgence : {finale_doc.get('statut_urgence', '').upper()}\n"
            f"Verdict exécutif : {finale_doc.get('verdict_executif')}\n"
        )

        return {
            "statut": "termine",
            "domaine_prioritaire": finale_doc.get("domaine_prioritaire_identifie"),
            "probleme_persistant": finale_doc.get("probleme_majeur_persistant"),
            "statut_urgence": finale_doc.get("statut_urgence"),
            "verdict_executif": finale_doc.get("verdict_executif"),
            "total_sources": finale_doc.get("total_documents_sources_couverts"),
            "duree_secondes": round(duration, 2),
        }

    except token_budget.BudgetExceeded as be:
        logger.warning(f"[STAGE 5] Arrêt: budget token atteint: {be}")
        return {"statut": "erreur", "erreur": str(be)}
    except (get_error_class(), ParsingError, Exception) as exc:
        logger.error(f"[STAGE 5] ÉCHEC synthèse finale: {exc}")
        return {"statut": "erreur", "erreur": str(exc)}
