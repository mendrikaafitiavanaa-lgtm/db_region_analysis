"""
Cache persistant simple des prompts -> enrichissements.
Permet d'éviter appels LLM répétés pour le même (title, raw_text).
"""
import os
import json
import threading
import hashlib
from typing import Optional

from config import settings

CACHE_FILE = os.path.join(settings.CHECKPOINT_DIR, "prompt_cache.json")

_lock = threading.Lock()
_cache = None  # lazy load


def _ensure_dir():
    os.makedirs(settings.CHECKPOINT_DIR, exist_ok=True)


def _load():
    global _cache
    if _cache is not None:
        return _cache
    _ensure_dir()
    if not os.path.exists(CACHE_FILE):
        _cache = {}
        return _cache
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as fh:
            _cache = json.load(fh)
    except Exception:
        _cache = {}
    return _cache


def _save():
    _ensure_dir()
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as fh:
            json.dump(_cache or {}, fh)
    except Exception:
        pass


def _make_key(title: str, raw_text: str) -> str:
    s = (title or "") + "\n" + (raw_text or "")
    return hashlib.sha256(s.encode("utf-8")[: 10000]).hexdigest()


def get_analyse(title: str, raw_text: str) -> Optional[dict]:
    cache = _load()
    key = _make_key(title, raw_text)
    val = cache.get(key)
    if val and isinstance(val, dict):
        # S'il s'agit d'un ancien cache contenant un document enrichi complet
        if "analyse" in val and "type" in val:
            return val.get("analyse")
    return val


def set_analyse(title: str, raw_text: str, analyse: dict):
    with _lock:
        cache = _load()
        key = _make_key(title, raw_text)
        cache[key] = analyse
        _save()


def get_enriched(title: str, raw_text: str) -> Optional[dict]:
    return get_analyse(title, raw_text)


def set_enriched(title: str, raw_text: str, enriched: dict):
    set_analyse(title, raw_text, enriched)


def clear():
    global _cache
    with _lock:
        _cache = {}
        _save()
