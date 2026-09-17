"""
Écriture et persistance des synthèses dans l'architecture à 3 collections cibles :
1. MONGO_SYNTHESES_COLLECTION : Stages 1 et 2 (L1 + L2)
2. MONGO_DOMAINES_COLLECTION  : Stages 3 et 4 (Bilans Domaines + Rapport Global)
3. MONGO_FINALE_COLLECTION    : Stage 5 (Synthèse Finale Arbitrage N°1)
"""
from typing import Set, Optional
from config import settings
from src.db.mongo_client import (
    get_syntheses_collection,
    get_domaines_collection,
    get_finale_collection,
    get_collection,
)


def save_synthese_l1(synthese_doc: dict) -> bool:
    """Enregistre une micro-synthèse de Niveau 1 dans la collection Syntheses."""
    if not synthese_doc:
        return False
    coll = get_syntheses_collection()
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
    domaine = bilan_doc.get("domaine")
    mois = bilan_doc.get("mois_cible") or settings.MOIS_CIBLE or "general"
    coll.update_one(
        {"type": "bilan_domaine", "domaine": domaine, "mois_cible": mois},
        {"$set": bilan_doc},
        upsert=True,
    )
    return True


def save_rapport_global(rapport_doc: dict) -> bool:
    """Enregistre le rapport régional global consolidé (Niveau 4) dans la collection Domaines."""
    if not rapport_doc:
        return False
    coll = get_domaines_collection()
    mois = rapport_doc.get("mois_cible") or settings.MOIS_CIBLE or "general"
    region = rapport_doc.get("region") or settings.REGION
    coll.update_one(
        {"type": "rapport_global_mensuel", "mois_cible": mois, "region": region},
        {"$set": rapport_doc},
        upsert=True,
    )
    return True


def save_rapport_mensuel_finale(finale_doc: dict) -> bool:
    """Enregistre la synthèse exécutive finale problème N°1 (Stage 5) dans la collection Finale."""
    if not finale_doc:
        return False
    coll = get_finale_collection()
    mois = finale_doc.get("mois_cible") or settings.MOIS_CIBLE or "general"
    region = finale_doc.get("region") or settings.REGION
    coll.update_one(
        {"type": "rapport_mensuel_finale", "mois_cible": mois, "region": region},
        {"$set": finale_doc},
        upsert=True,
    )
    return True


def sync_all_collections_metadata():
    """Met à jour les métadonnées (region et mois_cible) sur les documents existants dans MongoDB."""
    target_region = settings.REGION
    target_mois = settings.MOIS_CIBLE or "2026-08"

    collections = [
        get_syntheses_collection(),
        get_domaines_collection(),
        get_finale_collection(),
    ]

    for coll in collections:
        try:
            # Mise à jour de region
            coll.update_many(
                {"$or": [{"region": {"$exists": False}}, {"region": "Corse"}]},
                {"$set": {"region": target_region, "meta_analyse.region": target_region}}
            )
            # Mise à jour de mois_cible si manquant ou générique
            coll.update_many(
                {"$or": [{"mois_cible": {"$exists": False}}, {"mois_cible": "Mois d'analyse"}]},
                {"$set": {"mois_cible": target_mois, "meta_analyse.mois_cible": target_mois}}
            )
        except Exception:
            pass


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
    """Crée les index optimisés sur les 3 collections pour des requêtes instantanées (0 ms)."""
    # 1. Collection Syntheses (L1 + L2)
    coll_synth = get_syntheses_collection()
    try:
        coll_synth.create_index("type")
        coll_synth.create_index("stage")
        coll_synth.create_index("region")
        coll_synth.create_index("mois_cible")
        coll_synth.create_index("domaine_principal")
        coll_synth.create_index("document_ids")
        coll_synth.create_index("l1_synthese_ids")
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
        coll_dom.create_index("mois_cible")
        coll_dom.create_index("domaine")
        coll_dom.create_index([("type", 1), ("domaine", 1), ("mois_cible", 1)])
        coll_dom.create_index([("type", 1), ("region", 1), ("mois_cible", 1)])
        coll_dom.create_index("meta_analyse.run_id")
    except Exception:
        pass

    # 3. Collection Finale Décisionnelle (L5)
    coll_fin = get_finale_collection()
    try:
        coll_fin.create_index("type")
        coll_fin.create_index("stage")
        coll_fin.create_index("region")
        coll_fin.create_index("mois_cible")
        coll_fin.create_index("domaine_prioritaire_identifie")
        coll_fin.create_index([("type", 1), ("region", 1), ("mois_cible", 1)])
        coll_fin.create_index("meta_analyse.run_id")
    except Exception:
        pass

    sync_all_collections_metadata()


# Alias de compatibilité
ensure_indexes = ensure_all_indexes
