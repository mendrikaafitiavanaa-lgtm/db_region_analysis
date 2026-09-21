"""
Module de normalisation (Format Pivot) pour l'ingestion multi-sources.

Convertit les documents hétérogènes (anglais/français, dates BSON/ISO)
issus des différentes collections sources vers une structure unifiée PivotDocument.
"""
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional


def parse_datetime_flexible(val: Any) -> Optional[datetime]:
    """Parse une date sous diverses formes (datetime, dict {'$date': ...}, string ISO)."""
    if val is None:
        return None
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val.astimezone(timezone.utc)
    if isinstance(val, dict) and "$date" in val:
        raw_str = val["$date"]
        if isinstance(raw_str, (int, float)):
            return datetime.fromtimestamp(raw_str / 1000.0, tz=timezone.utc)
        return parse_datetime_flexible(raw_str)
    if isinstance(val, (int, float)):
        return datetime.fromtimestamp(val, tz=timezone.utc)
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return None
        # Nettoyage formats ISO (ex: Z -> +00:00)
        iso_str = val.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(iso_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            pass
        # Fallback formats standards YYYY-MM-DD
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                dt = datetime.strptime(val, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def normalize_document(raw_doc: Dict[str, Any], default_source_collection: str = "") -> Dict[str, Any]:
    """
    Transforme un document brut (EN ou FR) en Format Pivot standardisé.
    
    Structure Pivot retournée :
    {
        "document_id": str,
        "title": str,
        "raw_text": str,
        "url": str,
        "source_name": str,
        "source_category": str,
        "region": str,
        "department": str,
        "territoire": str,
        "publication_date": Optional[datetime],
        "mois_publication": str (YYYY-MM),
        "source_collection": str,
        "raw_doc_id": str,
    }
    """
    if not isinstance(raw_doc, dict):
        return {}

    # 1. URL & ID
    url = (
        raw_doc.get("url")
        or raw_doc.get("url_source")
        or raw_doc.get("link")
        or ""
    ).strip()

    raw_id = raw_doc.get("document_id") or raw_doc.get("_id")
    if raw_id is not None:
        doc_id = str(raw_id)
    elif url:
        doc_id = hashlib.sha256(url.encode("utf-8")).hexdigest()
    else:
        doc_id = hashlib.sha256(str(raw_doc).encode("utf-8")).hexdigest()

    # 2. Titre & Texte
    title = (
        raw_doc.get("title")
        or raw_doc.get("titre")
        or raw_doc.get("headline")
        or ""
    ).strip()

    raw_text = (
        raw_doc.get("raw_text")
        or raw_doc.get("texte_complet")
        or raw_doc.get("extrait")
        or raw_doc.get("description")
        or raw_doc.get("content")
        or ""
    ).strip()

    # 3. Source & Catégorie
    source_name = (
        raw_doc.get("source_name")
        or raw_doc.get("source_nom")
        or raw_doc.get("source")
        or "Source Inconnue"
    ).strip()

    source_category = (
        raw_doc.get("source_category")
        or raw_doc.get("categorie")
        or "news"
    ).strip()

    # 4. Région & Territoire / Département
    region = (
        raw_doc.get("region")
        or "Corse"
    ).strip()

    dept_raw = (
        raw_doc.get("department")
        or raw_doc.get("territoire")
        or raw_doc.get("departement")
    )
    if not dept_raw and "departement_detecte" in raw_doc:
        detecte = raw_doc["departement_detecte"]
        if isinstance(detecte, list) and len(detecte) > 0:
            dept_raw = detecte[0]
        elif isinstance(detecte, str):
            dept_raw = detecte

    if not dept_raw:
        dept_raw = default_source_collection or "Corse"

    department = str(dept_raw).strip()

    # 5. Date de publication & Mois
    pub_date_raw = (
        raw_doc.get("publication_date")
        or raw_doc.get("date_publication")
        or raw_doc.get("date_extraction")
        or raw_doc.get("first_discovered_at")
    )
    pub_date = parse_datetime_flexible(pub_date_raw)
    mois_str = pub_date.strftime("%Y-%m") if pub_date else ""

    return {
        "_id": raw_doc.get("_id"),
        "document_id": doc_id,
        "title": title,
        "raw_text": raw_text,
        "url": url,
        "source_name": source_name,
        "source_category": source_category,
        "region": region,
        "department": department,
        "territoire": department,
        "publication_date": pub_date,
        "mois_publication": mois_str,
        "source_collection": default_source_collection,
    }
