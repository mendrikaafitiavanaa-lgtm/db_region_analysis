"""
Module de lecture des collections MongoDB avec curseurs et projections optimisés.
Supporte l'ingestion multi-sources hétérogènes (anglais et français)
et l'architecture à 3 collections cibles.
"""
import calendar
from datetime import datetime, timezone
from typing import Iterator, List, Optional, Set, Dict, Any
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
from src.db.normalizer import normalize_document, parse_datetime_flexible

# Projection légère couvrant les formats anglais et français
OPTIMIZED_SOURCE_PROJECTION = {
    "_id": 1,
    "document_id": 1,
    "url": 1,
    "url_source": 1,
    "title": 1,
    "titre": 1,
    "raw_text": 1,
    "texte_complet": 1,
    "extrait": 1,
    "description": 1,
    "source_name": 1,
    "source_nom": 1,
    "source_category": 1,
    "categorie": 1,
    "region": 1,
    "department": 1,
    "departement_detecte": 1,
    "territoire": 1,
    "publication_date": 1,
    "date_publication": 1,
    "date_extraction": 1,
    "first_discovered_at": 1,
}


def _mois_bounds(mois_cible: str):
    """Convertit 'YYYY-MM' -> (datetime debut UTC, datetime fin UTC)."""
    year, month = (int(x) for x in mois_cible.split("-"))
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    last_day = calendar.monthrange(year, month)[1]
    end = datetime(year, month, last_day, 23, 59, 59, 999000, tzinfo=timezone.utc)
    return start, end


def get_flexible_date_filter(mois_cible: Optional[str] = None) -> dict:
    """Construit un filtre Mongo tolérant les dates BSON Date et les chaînes ISO."""
    mois = (mois_cible or settings.MOIS_CIBLE or "").strip()
    if not mois:
        return {}

    try:
        start, end = _mois_bounds(mois)
        return {
            "$or": [
                {"publication_date": {"$gte": start, "$lte": end}},
                {"publication_date": {"$regex": f"^{mois}"}},
                {"date_publication": {"$gte": start, "$lte": end}},
                {"date_publication": {"$regex": f"^{mois}"}},
                {"date_extraction": {"$regex": f"^{mois}"}},
            ]
        }
    except Exception:
        return {
            "$or": [
                {"publication_date": {"$regex": f"^{mois}"}},
                {"date_publication": {"$regex": f"^{mois}"}},
            ]
        }


def get_already_processed_ids(
    collection_name: str,
    id_field: str = "document_ids",
    stage_type: Optional[str] = None,
    require_fields: Optional[List[str]] = None,
    mois_cible: Optional[str] = None,
    territoire: Optional[str] = None,
) -> Set[str]:
    """Récupère l'ensemble des identifiants sources déjà consolidés dans la collection cible."""
    coll = get_collection(collection_name)
    filt: Dict[str, Any] = {}
    if stage_type:
        filt["type"] = stage_type

    mois = (mois_cible or settings.MOIS_CIBLE or "").strip()
    if mois:
        filt["mois_cible"] = mois

    if territoire and territoire.lower() != "all":
        filt["$or"] = [
            {"source_territoire": territoire},
            {"department": territoire},
            {"region": territoire},
        ]

    # Vérification optionnelle de complétude
    if require_fields:
        for f in require_fields:
            filt[f] = {"$exists": True, "$ne": "", "$nin": [None, "NON PRÉCISÉ", "NON_PRECISE"]}

    processed_ids = set()
    cursor = coll.find(filt, {id_field: 1, "_id": 0})
    for doc in cursor:
        val = doc.get(id_field)
        if isinstance(val, list):
            for item in val:
                if item:
                    processed_ids.add(str(item))
        elif val:
            processed_ids.add(str(val))

    return processed_ids


def read_pending_sources_from_collection(
    collection_name: str,
    exclude_ids: Optional[Set[str]] = None,
    mois_cible: Optional[str] = None,
    max_docs: int = 0,
) -> List[Dict[str, Any]]:
    """Lit et normalise les documents d'une collection source spécifique."""
    coll = get_source_collection(collection_name)
    filt = get_flexible_date_filter(mois_cible)

    cursor = coll.find(filt, OPTIMIZED_SOURCE_PROJECTION).sort("_id", 1)
    results = []
    
    for raw in cursor:
        normalized = normalize_document(raw, default_source_collection=collection_name)
        doc_id = normalized.get("document_id")
        
        # Filtrer si déjà traité
        if exclude_ids and (doc_id in exclude_ids or str(raw.get("_id")) in exclude_ids):
            continue
            
        # Filtrer si pas de texte utile
        if not normalized.get("raw_text") and not normalized.get("title"):
            continue

        results.append(normalized)
        if max_docs > 0 and len(results) >= max_docs:
            break

    return results


def read_all_pending_sources(
    exclude_ids: Optional[Set[str]] = None,
    source_collections: Optional[List[str]] = None,
    mois_cible: Optional[str] = None,
    max_docs: int = 0,
) -> List[Dict[str, Any]]:
    """Charge et normalise les documents sources de toutes les collections configurées."""
    collections = source_collections or settings.get_source_collections()
    all_docs = []
    
    for coll_name in collections:
        if not coll_name:
            continue
        try:
            limit_for_coll = (max_docs - len(all_docs)) if max_docs > 0 else 0
            docs = read_pending_sources_from_collection(
                collection_name=coll_name,
                exclude_ids=exclude_ids,
                mois_cible=mois_cible,
                max_docs=limit_for_coll,
            )
            all_docs.extend(docs)
            if max_docs > 0 and len(all_docs) >= max_docs:
                break
        except Exception as err:
            # Tolérance aux erreurs de collection (ex: collection inexistante)
            pass

    return all_docs


def read_stage_documents(
    collection_name: str,
    query: Optional[dict] = None,
    stage_type: Optional[str] = None,
    territoire: Optional[str] = None,
    mois_cible: Optional[str] = None,
) -> List[dict]:
    """Lit les documents d'une collection cible avec filtrage de stage, territoire et mois."""
    coll = get_collection(collection_name)
    filt = dict(query) if query else {}
    if stage_type:
        filt["type"] = stage_type
    elif "type" not in filt:
        filt["type"] = {"$ne": "log_stage"}

    mois = (mois_cible or settings.MOIS_CIBLE or "").strip()
    if mois and "mois_cible" not in filt:
        filt["mois_cible"] = mois

    if territoire and territoire.lower() != "all" and "source_territoire" not in filt:
        filt["source_territoire"] = territoire

    return list(coll.find(filt).sort("_id", 1))
