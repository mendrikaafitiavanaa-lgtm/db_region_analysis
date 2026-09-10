"""
Écriture et persistance des synthèses pour chaque étape du pipeline pyramidal.
"""
from typing import Set, Optional
from config import settings
from src.db.mongo_client import (
    get_l1_collection,
    get_l2_collection,
    get_domaines_collection,
    get_global_collection,
    get_finale_collection,
    get_collection,
)


def save_synthese_l1(synthese_doc: dict) -> bool:
    """Enregistre une micro-synthèse de Niveau 1."""
    if not synthese_doc:
        return False
    coll = get_l1_collection()
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
    """Enregistre une méso-synthèse de Niveau 2."""
    if not synthese_doc:
        return False
    coll = get_l2_collection()
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
    """Enregistre le grand bilan mensuel d'un domaine (Niveau 3)."""
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
    """Enregistre le rapport régional global consolidé (Niveau 4 - Sommet)."""
    if not rapport_doc:
        return False
    coll = get_global_collection()
    mois = rapport_doc.get("mois_cible") or settings.MOIS_CIBLE or "general"
    region = rapport_doc.get("region", "Corse")
    coll.update_one(
        {"type": "rapport_global_mensuel", "mois_cible": mois, "region": region},
        {"$set": rapport_doc},
        upsert=True,
    )
    return True


def save_rapport_mensuel_finale(finale_doc: dict) -> bool:
    """Enregistre la synthèse exécutive finale sur le problème N°1 le plus persistant (Stage 5)."""
    if not finale_doc:
        return False
    coll = get_finale_collection()
    mois = finale_doc.get("mois_cible") or settings.MOIS_CIBLE or "general"
    region = finale_doc.get("region", "Corse")
    coll.update_one(
        {"type": "rapport_mensuel_finale", "mois_cible": mois, "region": region},
        {"$set": finale_doc},
        upsert=True,
    )
    return True


def save_stage_log(stage_name: str, log_doc: dict) -> None:
    """Enregistre le journal d'exécution d'un stage."""
    if not log_doc or "run_id" not in log_doc:
        return
    coll = get_global_collection()
    coll.update_one(
        {"type": "log_stage", "stage": stage_name, "run_id": log_doc["run_id"]},
        {"$set": log_doc},
        upsert=True,
    )


def ensure_all_indexes():
    """Crée les index sur toutes les collections pour des requêtes instantanées."""
    for coll in [
        get_l1_collection(),
        get_l2_collection(),
        get_domaines_collection(),
        get_global_collection(),
        get_finale_collection(),
    ]:
        try:
            coll.create_index("type")
            coll.create_index("domaine")
            coll.create_index("domaine_principal")
            coll.create_index("domaine_prioritaire_identifie")
            coll.create_index("gravite")
            coll.create_index("date_analyse")
            coll.create_index("document_ids")
            coll.create_index("l1_synthese_ids")
            coll.create_index("meta_analyse.run_id")
        except Exception:
            pass


# Alias de compatibilité
ensure_indexes = ensure_all_indexes


