"""
Module de lecture des collections MongoDB avec curseurs optimisés.
Supporte l'architecture à 3 collections cibles :
1. Syntheses (L1 + L2)
2. Domaines (L3 + L4)
3. Finale (L5)
"""
import calendar
from datetime import datetime, timezone
from typing import Iterator, List, Optional, Set
from bson import ObjectId
from pymongo.collection import Collection

from config import settings
from src.db.mongo_client import (
    get_source_collection,
    get_syntheses_collection,
    get_domaines_collection,
    get_finale_collection,
    get_collection,
)

SOURCE_PROJECTION = {
    "_id": 1,
    "document_id": 1,
    "url": 1,
    "title": 1,
    "raw_text": 1,
    "source_name": 1,
    "source_category": 1,
    "region": 1,
    "department": 1,
    "municipality": 1,
    "publication_date": 1,
    "last_updated_at": 1,
}


def _mois_bounds(mois_cible: str):
    """Convertit 'YYYY-MM' -> (datetime debut UTC, datetime fin UTC)."""
    year, month = (int(x) for x in mois_cible.split("-"))
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    last_day = calendar.monthrange(year, month)[1]
    end = datetime(year, month, last_day, 23, 59, 59, 999000, tzinfo=timezone.utc)
    return start, end


def get_base_date_filter() -> dict:
    filt = {}
    if settings.MOIS_CIBLE:
        try:
            start, end = _mois_bounds(settings.MOIS_CIBLE)
            filt["$or"] = [
                {"publication_date": {"$gte": start, "$lte": end}},
                {"publication_date": {"$regex": f"^{settings.MOIS_CIBLE}"}},
            ]
        except Exception:
            filt["publication_date"] = {"$regex": f"^{settings.MOIS_CIBLE}"}
    return filt


def count_sources_pending(exclude_ids: Optional[Set[str]] = None) -> int:
    coll = get_source_collection()
    filt = get_base_date_filter()
    if exclude_ids:
        filt["document_id"] = {"$nin": list(exclude_ids)}
    return coll.count_documents(filt)


def read_all_pending_sources(
    exclude_ids: Optional[Set[str]] = None,
    max_docs: int = 0
) -> List[dict]:
    """Charge en mémoire les documents sources non traités pour le regroupement thématique."""
    coll = get_source_collection()
    filt = get_base_date_filter()
    if exclude_ids:
        filt["document_id"] = {"$nin": list(exclude_ids)}

    cursor = coll.find(filt, SOURCE_PROJECTION).sort("_id", 1)
    if max_docs > 0:
        cursor = cursor.limit(max_docs)
    
    return list(cursor)


def read_stage_documents(
    collection_name: str,
    query: Optional[dict] = None,
    stage_type: Optional[str] = None,
) -> List[dict]:
    """Lit les documents d'une collection avec filtrage optionnel par stage_type."""
    coll = get_collection(collection_name)
    filt = dict(query) if query else {}
    if stage_type:
        filt["type"] = stage_type
    elif "type" not in filt:
        filt["type"] = {"$ne": "log_stage"}
    return list(coll.find(filt).sort("_id", 1))


def get_already_processed_ids(
    collection_name: str,
    id_field: str = "document_ids",
    stage_type: Optional[str] = None,
    require_fields: Optional[List[str]] = None,
) -> Set[str]:
    """Récupère tous les IDs déjà traités et à jour dans la collection cible pour éviter les doublons."""
    coll = get_collection(collection_name)
    filt = {}
    if stage_type:
        filt["type"] = stage_type
    else:
        filt["type"] = {"$ne": "log_stage"}
    
    # Si des champs obligatoires sont requis (par ex: cause, preuve), ne considérer comme traités
    # que les documents qui les ont renseignés avec un contenu valide (non vide / non générique).
    if require_fields:
        for f in require_fields:
            filt[f] = {
                "$exists": True,
                "$ne": "",
                "$nin": [
                    f"Information non consolidée pour {f}",
                    "Cause racine en attente de précision",
                    "Cause sectorielle non consolidée",
                    "Causes transversales en attente d'analyse",
                    "Éléments de preuve en cours de rassemblement",
                    "Preuves et indicateurs en attente",
                    "Preuves et indicateurs globaux non disponibles",
                ],
            }

    processed = coll.distinct(id_field, filt)
    return set(str(doc_id) for doc_id in processed if doc_id)
