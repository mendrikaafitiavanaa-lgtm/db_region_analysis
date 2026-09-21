"""
Orchestrateur principal de la pyramide d'analyse territoriale (Stages 1 à 5).

Supporte l'exécution multi-territoires (4 collections sources),
le découpage par session/lots (--limit), et la bascule automatique entre les 4 LLM.
"""
import time
from datetime import datetime, timezone
from typing import Dict, Optional, List

from config import settings
from src.utils.logger import get_logger
from src.pipeline.stage1_micro import run_stage_1
from src.pipeline.stage2_meso import run_stage_2
from src.pipeline.stage3_domaines import run_stage_3
from src.pipeline.stage4_global import run_stage_4
from src.pipeline.stage5_finale import run_stage_5


def run_pipeline(
    stage: str = "all",
    run_id: Optional[str] = None,
    force: bool = False,
    dept: str = "all",
    limit: int = 0,
) -> Dict:
    """
    Exécute le pipeline pyramidal d'analyse.
    
    Args:
        stage: '1', '2', '3', '4', '5' ou 'all'
        run_id: Identifiant unique du run (généré si None)
        force: Force la ré-analyse même si les documents sont déjà indexés
        dept: 'all' pour les 4 collections, ou le nom d'un territoire précis (ex: 'Corse-du-Sud')
        limit: Nombre max de lots/documents à traiter pour cette session (0 = sans limite)
    """
    logger = get_logger()
    settings.validate()
    
    run_id = run_id or f"run_pipeline_{datetime.now().strftime('%Y-%m-%d_%Hh%M')}"
    start_global = time.time()
    
    # Détermination des collections sources cibles
    if dept and dept.lower() != "all":
        source_collections = [dept]
        territoire_label = dept
    else:
        source_collections = settings.get_source_collections()
        territoire_label = "Corse"
    
    logger.info("=" * 70)
    logger.info(f" 🚀 DÉMARRAGE DU PIPELINE PYRAMIDAL TERRITORIAL [{run_id}]")
    logger.info(f"   Étage(s) d'exécution : Stage '{stage.upper()}' (Force={force})")
    logger.info(f"   Périmètre Source     : {dept} ({source_collections})")
    logger.info(f"   Fournisseurs LLM     : {settings.LLM_PROVIDER_ORDER}")
    logger.info(f"   Mois cible           : {settings.MOIS_CIBLE or 'Global / Tous mois'}")
    if limit > 0:
        logger.info(f"   Limite par session   : {limit} lots/documents max")
    logger.info("=" * 70)
    
    results = {
        "run_id": run_id,
        "date_debut": datetime.now(timezone.utc).isoformat(),
        "statut": "en_cours",
        "stages": {},
    }
    
    try:
        # --- ÉTAPE 1 : Documents Bruts -> Micro-synthèses L1 ---
        if stage in ("1", "all"):
            logger.info("\n▶ [STAGE 1] Micro-synthèses par lots thématiques (L0 -> L1)")
            res_s1 = run_stage_1(
                run_id=run_id,
                force=force,
                limit=limit,
                territoire=territoire_label if dept.lower() != "all" else None,
                source_collections=source_collections,
            )
            results["stages"]["stage_1"] = res_s1
            logger.info(f"✅ Stage 1 terminé : {res_s1.get('succes', 0)} micro-synthèses L1 générées.\n")
        
        # --- ÉTAPE 2 : Micro-synthèses L1 -> Méso-synthèses L2 ---
        if stage in ("2", "all"):
            logger.info("\n▶ [STAGE 2] Consolidation méso-territoriale par domaine (L1 -> L2)")
            res_s2 = run_stage_2(
                run_id=run_id,
                force=force,
                territoire=territoire_label if dept.lower() != "all" else None,
                limit=limit,
            )
            results["stages"]["stage_2"] = res_s2
            logger.info(f"✅ Stage 2 terminé : {res_s2.get('succes', 0)} méso-synthèses L2 générées.\n")
        
        # --- ÉTAPE 3 : Méso-synthèses L2 -> Bilans de Domaine ---
        if stage in ("3", "all"):
            logger.info("\n▶ [STAGE 3] Grands Bilans Mensuels par Domaine (L2 -> L3)")
            res_s3 = run_stage_3(
                run_id=run_id,
                territoire=territoire_label if dept.lower() != "all" else None,
            )
            results["stages"]["stage_3"] = res_s3
            logger.info(f"✅ Stage 3 terminé : {res_s3.get('succes', 0)} bilans de domaine rédigés.\n")
        
        # --- ÉTAPE 4 : Bilans de Domaine -> Rapport Global Territorial ---
        if stage in ("4", "all"):
            logger.info("\n▶ [STAGE 4] Rapport Stratégique Territorial Global (L3 -> L4 - Sommet)")
            res_s4 = run_stage_4(
                run_id=run_id,
                territoire=territoire_label if dept.lower() != "all" else None,
            )
            results["stages"]["stage_4"] = res_s4
            logger.info(f"✅ Stage 4 terminé : {res_s4.get('titre', 'Rapport Global')}\n")
        
        # --- ÉTAPE 5 : Rapport Global -> Synthèse Exécutive Problème N°1 ---
        if stage in ("5", "all"):
            logger.info("\n▶ [STAGE 5] Synthèse Exécutive Finale N°1 (L4 -> L5 - Sommet Ultime)")
            res_s5 = run_stage_5(
                run_id=run_id,
                territoire=territoire_label if dept.lower() != "all" else None,
            )
            results["stages"]["stage_5"] = res_s5
            logger.info(
                f"✅ Stage 5 terminé : Domaine N°1 [{res_s5.get('domaine_prioritaire', '').upper()}] - {res_s5.get('probleme_persistant')}\n"
            )
        
        results["statut"] = "succes"

    except Exception as exc:
        results["statut"] = "erreur"
        results["erreur"] = str(exc)
        logger.error(f"❌ Arrêt prématuré du pipeline sur exception : {exc}", exc_info=True)
        raise
    finally:
        total_duree = time.time() - start_global
        results["date_fin"] = datetime.now(timezone.utc).isoformat()
        results["duree_totale_secondes"] = round(total_duree, 2)
        
        logger.info("=" * 70)
        logger.info(f" 🏁 FIN D'EXÉCUTION DU PIPELINE [{run_id}] en {total_duree:.1f}s")
        logger.info(f"   Statut global : {results['statut'].upper()}")
        logger.info("=" * 70)

    return results
