"""Connexion MongoDB centralisée et accès aux 3 collections de la pyramide d'analyse."""
from pymongo import MongoClient
from pymongo.collection import Collection
from config import settings

_client = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(settings.MONGO_URI)
    return _client


def get_db():
    return get_client()[settings.MONGO_DB_NAME]


def get_collection(name: str) -> Collection:
    return get_db()[name]


def get_source_collection() -> Collection:
    """Collection source des articles bruts (Niveau 0)."""
    return get_collection(settings.MONGO_SOURCE_COLLECTION)


def get_syntheses_collection() -> Collection:
    """Collection 1 (Terrain) : regroupe les micro-synthèses L1 et méso-synthèses L2."""
    return get_collection(settings.MONGO_SYNTHESES_COLLECTION)


def get_domaines_collection() -> Collection:
    """Collection 2 (Stratégique) : regroupe les bilans de domaine L3 et le rapport global L4."""
    return get_collection(settings.MONGO_DOMAINES_COLLECTION)


def get_finale_collection() -> Collection:
    """Collection 3 (Décisionnelle) : synthèse exécutive finale ciblée problème N°1 (Stage 5)."""
    return get_collection(settings.MONGO_FINALE_COLLECTION)


# Fonctions d'accès de compatibilité
def get_l1_collection() -> Collection:
    return get_syntheses_collection()


def get_l2_collection() -> Collection:
    return get_syntheses_collection()


def get_global_collection() -> Collection:
    return get_domaines_collection()
