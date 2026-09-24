"""
STAGE 3 : Grands Bilans Mensuels par Domaine (Synthèses L2 -> 1 Bilan par Domaine Territorial).

Flux :
1. Lecture de toutes les synthèses L2 de la période pour le territoire cible.
2. Regroupement par grand domaine.
3. Pour chaque domaine : génération du Bilan Mensuel de Domaine approfondi.
4. Sauvegarde dans la collection unifiée domaines_analysis.
"""
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, Optional

from config import settings
from src.db import source_reader, target_writer
from src.llm.client import call_llm, call_llm_with_meta, get_error_class
from src.llm.prompts.prompt_stage3 import build_stage3_messages
from src.llm.response_parser import parse_stage3_response, ParsingError
from src.schema.analyse_schema import build_stage3_document
from src.utils.logger import get_logger
from src.llm import token_budget


def run_stage_3(run_id: Optional[str] = None, territoire: Optional[str] = None) -> Dict:
    logger = get_logger()
    settings.validate()
    target_writer.ensure_all_indexes()

    run_id = run_id or f"run_l3_{datetime.now().strftime('%Y-%m-%d_%Hh%M')}"
    logger.info(f"=== [STAGE 3] Démarrage des Bilans par Domaine ({run_id}) ===")

    # 1. Charger toutes les synthèses L2
    all_l2_docs = source_reader.read_stage_documents(
        collection_name=settings.MONGO_SYNTHESES_COLLECTION,
        stage_type="synthese_l2",
        territoire=territoire,
        mois_cible=settings.MOIS_CIBLE,
    )

    if not all_l2_docs:
        # Fallback sur L1 si pas de L2
        logger.warning("[STAGE 3] Aucune synthèse L2 trouvée, tentative de lecture depuis L1...")
        all_l2_docs = source_reader.read_stage_documents(
            collection_name=settings.MONGO_SYNTHESES_COLLECTION,
            stage_type="synthese_l1",
            territoire=territoire,
            mois_cible=settings.MOIS_CIBLE,
        )

    if not all_l2_docs:
        logger.warning("[STAGE 3] Aucune donnée disponible pour générer les bilans de domaine.")
        return {"statut": "vide", "total_domaines": 0, "succes": 0, "erreurs": 0}

    # 2. Partitionner par domaine
    by_domain = defaultdict(list)
    for doc in all_l2_docs:
        dom = doc.get("domaine_principal") or "general_territoire"
        by_domain[dom].append(doc)

    logger.info(f"[STAGE 3] {len(by_domain)} domaines à synthétiser : {list(by_domain.keys())}")

    total_ok = 0
    total_erreurs = 0
    start_time = time.time()

    for idx, (domaine, l2_sub_docs) in enumerate(by_domain.items(), start=1):
        dom_start = time.time()
        logger.info(f"[STAGE 3] Bilan {idx}/{len(by_domain)} [{domaine.upper()}] ({len(l2_sub_docs)} synthèses)...")

        try:
            messages = build_stage3_messages(l2_sub_docs, domaine=domaine)
            raw_resp, used_provider = call_llm_with_meta(messages)
            analyse = parse_stage3_response(raw_resp)

            doc_l3 = build_stage3_document(
                l2_docs=l2_sub_docs,
                analyse=analyse,
                domaine=domaine,
                mois=settings.MOIS_CIBLE,
                region=territoire if (territoire and territoire.lower() != "all") else "",
                territoire=territoire if (territoire and territoire.lower() != "all") else "",
                run_id=run_id,
                provider=used_provider,
            )

            target_writer.save_bilan_domaine(doc_l3)
            total_ok += 1
            dom_dur = time.time() - dom_start
            logger.info(f"-> [STAGE 3] Bilan {domaine.upper()} validé (gravité={doc_l3.get('gravite_globale')}, provider={used_provider}) en {dom_dur:.1f}s")

        except token_budget.BudgetExceeded as be:
            logger.warning(f"[STAGE 3] Arrêt: budget token atteint: {be}")
            break
        except (get_error_class(), ParsingError, Exception) as exc:
            total_erreurs += 1
            logger.error(f"-> [STAGE 3] Bilan {domaine.upper()} ÉCHEC: {exc}")

        if settings.PAUSE_SECONDES > 0:
            time.sleep(settings.PAUSE_SECONDES)

    total_duration = time.time() - start_time
    logger.info(
        f"=== [STAGE 3 TERMINÉ] {total_ok} bilans de domaine enregistrés, "
        f"{total_erreurs} erreurs, en {total_duration:.1f}s ==="
    )

    return {
        "statut": "termine",
        "total_domaines": len(by_domain),
        "succes": total_ok,
        "erreurs": total_erreurs,
        "duree_secondes": round(total_duration, 2),
    }
