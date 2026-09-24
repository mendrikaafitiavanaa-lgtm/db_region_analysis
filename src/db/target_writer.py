"""
Écriture et persistance des synthèses dans l'architecture à 3 collections cibles :
1. MONGO_SYNTHESES_COLLECTION : Stages 1 et 2 (L1 + L2)
2. MONGO_DOMAINES_COLLECTION  : Stages 3 et 4 (Bilans Domaines + Rapport Global)
3. MONGO_FINALE_COLLECTION    : Stage 5 (Synthèse Finale Arbitrage N°1)
"""
from typing import Set, Optional, Dict, Any
from datetime import datetime, timezone
from config import settings
from src.db.mongo_client import (
    get_syntheses_collection,
    get_domaines_collection,
    get_finale_collection,
    get_collection,
)


def _ensure_meta_fields(doc: Dict[str, Any]) -> Dict[str, Any]:
    """S'assure que les métadonnées essentielles de traçabilité sont présentes."""
    if not isinstance(doc, dict):
        return doc
    
    if "date_execution" not in doc:
        doc["date_execution"] = datetime.now(timezone.utc).isoformat()
        
    if "mois_cible" not in doc or not doc["mois_cible"]:
        doc["mois_cible"] = settings.MOIS_CIBLE or "general"
        
    if "source_territoire" not in doc or not doc["source_territoire"]:
        doc["source_territoire"] = doc.get("department") or doc.get("region") or getattr(settings, "REGION", "Corse") or "Corse"
        
    return doc


def save_synthese_l1(synthese_doc: dict) -> bool:
    """Enregistre une micro-synthèse de Niveau 1 dans la collection Syntheses."""
    if not synthese_doc:
        return False
    coll = get_syntheses_collection()
    synthese_doc = _ensure_meta_fields(synthese_doc)
    doc_ids = synthese_doc.get("document_ids", [])
    if doc_ids:
        coll.update_one(
            {"type": "synthese_l1", "document_ids": doc_ids},
            {"$set": synthese_doc},
            upsert=True,
        )
    else:
        coll.insert_one(synthese_doc)
    return True


def save_synthese_l2(synthese_doc: dict) -> bool:
    """Enregistre une méso-synthèse de Niveau 2 dans la collection Syntheses."""
    if not synthese_doc:
        return False
    coll = get_syntheses_collection()
    synthese_doc = _ensure_meta_fields(synthese_doc)
    l1_ids = synthese_doc.get("l1_synthese_ids", [])
    if l1_ids:
        coll.update_one(
            {"type": "synthese_l2", "l1_synthese_ids": l1_ids},
            {"$set": synthese_doc},
            upsert=True,
        )
    else:
        coll.insert_one(synthese_doc)
    return True


def save_bilan_domaine(bilan_doc: dict) -> bool:
    """Enregistre le grand bilan mensuel d'un domaine (Niveau 3) dans la collection Domaines."""
    if not bilan_doc:
        return False
    coll = get_domaines_collection()
    bilan_doc = _ensure_meta_fields(bilan_doc)
    domaine = bilan_doc.get("domaine")
    mois = bilan_doc.get("mois_cible") or settings.MOIS_CIBLE or "general"
    territoire = bilan_doc.get("source_territoire") or settings.REGION
    
    query = {"type": "bilan_domaine", "domaine": domaine, "mois_cible": mois}
    if territoire:
        query["source_territoire"] = territoire
        
    coll.update_one(query, {"$set": bilan_doc}, upsert=True)
    return True


def save_rapport_global(rapport_doc: dict) -> bool:
    """Enregistre le rapport régional global consolidé (Niveau 4) dans la collection Domaines."""
    if not rapport_doc:
        return False
    coll = get_domaines_collection()
    rapport_doc = _ensure_meta_fields(rapport_doc)
    mois = rapport_doc.get("mois_cible") or settings.MOIS_CIBLE or "general"
    territoire = rapport_doc.get("source_territoire") or rapport_doc.get("region") or settings.REGION
    
    query = {"type": "rapport_global_mensuel", "mois_cible": mois}
    if territoire:
        query["source_territoire"] = territoire
        
    coll.update_one(query, {"$set": rapport_doc}, upsert=True)
    return True


def save_rapport_mensuel_finale(finale_doc: dict) -> bool:
    """Enregistre la synthèse exécutive finale problème N°1 (Stage 5) dans la collection Finale."""
    if not finale_doc:
        return False
    coll = get_finale_collection()
    finale_doc = _ensure_meta_fields(finale_doc)
    mois = finale_doc.get("mois_cible") or settings.MOIS_CIBLE or "general"
    territoire = finale_doc.get("source_territoire") or finale_doc.get("region") or settings.REGION
    
    query = {"type": "rapport_mensuel_finale", "mois_cible": mois}
    if territoire:
        query["source_territoire"] = territoire
        
    coll.update_one(query, {"$set": finale_doc}, upsert=True)
    return True


def save_stage_log(stage_name: str, log_doc: dict) -> None:
    """Enregistre le journal d'exécution d'un stage."""
    if not log_doc or "run_id" not in log_doc:
        return
    coll = get_domaines_collection()
    coll.update_one(
        {"type": "log_stage", "stage": stage_name, "run_id": log_doc["run_id"]},
        {"$set": log_doc},
        upsert=True,
    )


def ensure_all_indexes():
    """Crée les index optimisés sur les 3 collections cibles pour des requêtes instantanées (0 ms)."""
    # 1. Collection Syntheses (L1 + L2)
    coll_synth = get_syntheses_collection()
    try:
        coll_synth.create_index("type")
        coll_synth.create_index("stage")
        coll_synth.create_index("region")
        coll_synth.create_index("source_territoire")
        coll_synth.create_index("mois_cible")
        coll_synth.create_index("domaine_principal")
        coll_synth.create_index("document_ids")
        coll_synth.create_index("l1_synthese_ids")
        coll_synth.create_index([("type", 1), ("source_territoire", 1), ("mois_cible", 1)])
        coll_synth.create_index([("type", 1), ("domaine_principal", 1), ("mois_cible", 1)])
        coll_synth.create_index("meta_analyse.run_id")
    except Exception:
        pass

    # 2. Collection Domaines & Rapport Global (L3 + L4)
    coll_dom = get_domaines_collection()
    try:
        coll_dom.create_index("type")
        coll_dom.create_index("stage")
        coll_dom.create_index("region")
        coll_dom.create_index("source_territoire")
        coll_dom.create_index("mois_cible")
        coll_dom.create_index("domaine")
        coll_dom.create_index([("type", 1), ("source_territoire", 1), ("domaine", 1), ("mois_cible", 1)])
        coll_dom.create_index([("type", 1), ("source_territoire", 1), ("mois_cible", 1)])
        coll_dom.create_index("meta_analyse.run_id")
    except Exception:
        pass

    # 3. Collection Finale Décisionnelle (L5)
    coll_fin = get_finale_collection()
    try:
        coll_fin.create_index("type")
        coll_fin.create_index("stage")
        coll_fin.create_index("region")
        coll_fin.create_index("source_territoire")
        coll_fin.create_index("mois_cible")
        coll_fin.create_index("domaine_prioritaire_identifie")
        coll_fin.create_index([("type", 1), ("source_territoire", 1), ("mois_cible", 1)])
        coll_fin.create_index("meta_analyse.run_id")
    except Exception:
        pass


# Alias de compatibilité
ensure_indexes = ensure_all_indexes
