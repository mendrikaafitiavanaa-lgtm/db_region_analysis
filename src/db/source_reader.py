"""
Module de lecture des collections MongoDB avec curseurs optimisés.
Supporte la lecture pour le Stage 1 (documents bruts) et les Stages 2, 3, 4 (synthèses).
"""
import calendar
from datetime import datetime, timezone
from typing import Iterator, List, Optional, Set
from bson import ObjectId
from pymongo.collection import Collection

from config import settings
from src.db.mongo_client import (
    get_source_collection,
    get_l1_collection,
    get_l2_collection,
    get_domaines_collection,
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
        start, end = _mois_bounds(settings.MOIS_CIBLE)
        filt["publication_date"] = {"$gte": start, "$lte": end}
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
    query: Optional[dict] = None
) -> List[dict]:
    """Lit tous les documents d'une collection de stage donnée."""
    coll = get_collection(collection_name)
    filt = query or {}
    # Exclure les logs d'exécution éventuels
    filt["type"] = {"$ne": "log_stage"}
    return list(coll.find(filt).sort("_id", 1))


def get_already_processed_ids(collection_name: str, id_field: str = "document_ids") -> Set[str]:
    """Récupère tous les IDs déjà traités dans la collection cible pour éviter les doublons."""
    coll = get_collection(collection_name)
    processed = coll.distinct(id_field, {"type": {"$ne": "log_stage"}})
    return set(str(doc_id) for doc_id in processed if doc_id)
