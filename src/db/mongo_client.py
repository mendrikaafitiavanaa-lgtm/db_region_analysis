"""Connexion MongoDB centralisée et accès aux collections des différents stages."""
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
    return get_collection(settings.MONGO_SOURCE_COLLECTION)


def get_l1_collection() -> Collection:
    return get_collection(settings.MONGO_L1_COLLECTION)


def get_l2_collection() -> Collection:
    return get_collection(settings.MONGO_L2_COLLECTION)


def get_domaines_collection() -> Collection:
    return get_collection(settings.MONGO_DOMAINES_COLLECTION)


def get_global_collection() -> Collection:
    return get_collection(settings.MONGO_GLOBAL_COLLECTION)


def get_finale_collection() -> Collection:
    return get_collection(settings.MONGO_FINALE_COLLECTION)

