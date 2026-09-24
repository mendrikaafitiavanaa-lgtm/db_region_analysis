"""
Module de classification et partitionnement thématique local.

Utilise flashtext (arbre de recherche Trie / Aho-Corasick) pour classer
instantanément des milliers de documents sans aucun coût de tokens LLM.
Regroupe ensuite les documents par domaine en paquets homogènes.
Garantit une étanchéité thématique absolue (aucun mélange entre domaines).
"""
from typing import List, Dict
from collections import defaultdict
from flashtext import KeywordProcessor


# Dictionnaire thématique précis pour la Corse et les collectivités territoriales
DOMAINS_KEYWORDS = {
    # NOTE (2026-09) : domaine recentré sur le risque "sec" (feu/sécheresse/pollution).
    # Le mot-clé générique "eau" a été retiré : il captait aussi bien les posts sur
    # les restrictions d'eau (sécheresse) que les crues/inondations (excès d'eau),
    # deux problématiques opposées qui ne doivent pas être fusionnées dans le même bilan.
    "environnement_climat_risques": [
        "incendie", "incendies", "feu", "feux", "pompiers", "pompier", "sdis",
        "sécheresse", "secheresse", "canicule", "chaleur", "flamme", "flammes",
        "forêt", "foret", "écologie", "ecologie", "pollution", "qualitair",
        "nappe phréatique", "nappe phreatique", "restriction d'eau", "restrictions d'eau",
        "économie d'eau", "economie d'eau", "manque d'eau", "eau potable",
        "biodiversité", "biodiversite", "sécheresse hydrologique",
        "vigilance canicule", "particules fines"
    ],
    # NOUVEAU DOMAINE : phénomènes météo violents "humides" (orage, crue, vent fort),
    # analytiquement distincts de la sécheresse/incendie ci-dessus.
    "meteo_intemperies_crues": [
        "orage", "orages", "intempérie", "intempéries", "intemperies",
        "inondation", "inondations", "crue", "crues", "tempête", "tempete",
        "vent violent", "rafale", "rafales", "vigilance orange", "vigilance jaune",
        "vigilance rouge", "montée des eaux", "montee des eaux", "évacuation préventive",
        "evacuation preventive", "plan communal de sauvegarde", "météo", "meteo"
    ],
    "cadre_vie_proprete_dechets": [
        "déchet", "dechets", "déchets", "ordures", "ordure", "poubelle", "poubelles",
        "décharge", "decharge", "dépôt sauvage", "depot sauvage", "tri sélectif",
        "tri", "recyclage", "syvadec", "encombrants", "propreté", "proprete",
        "salubrité", "salubrite", "station d'épuration", "station d epuration",
        "assainissement", "eaux usées", "eaux usees", "incivilités", "incivilites"
    ],
    "transport_mobilite": [
        "route", "routes", "circulation", "bouchon", "bouchons", "trafic",
        "bus", "train", "gare", "ferroviaire", "cfc", "chemin de fer", "port",
        "ports", "maritime", "ferry", "corsica lineas", "corsica linea",
        "corsica ferries", "aéroport", "aeroport", "vol", "vols", "avion", "avions",
        "air corsica", "voirie", "stationnement", "parking", "parkings", "trottinette",
        "piste cyclable", "vélo", "velo", "asphalte", "enrobé", "enrobe",
        "nid-de-poule", "nids-de-poule", "pont", "tunnel", "blocage de route"
    ],
    "sante_secours": [
        "médecin", "medecin", "médecins", "medecins", "docteur", "docteurs",
        "urgence", "urgences", "hôpital", "hopital", "hôpitaux", "hopitaux",
        "soin", "soins", "santé", "sante", "désert médical", "desert medical",
        "clinique", "ehpad", "pharmacie", "pharmacien", "infirmier", "infirmière",
        "infirmiers", "infirmieres", "médical", "medical", "médicale", "medicale",
        "pédiatre", "pediatre", "spécialiste", "spécialistes", "smur", "samu",
        "ambulance", "ambulances", "dialyse", "maternité", "maternite", "ars"
    ],
    "securite_justice": [
        "police", "gendarmerie", "gendarme", "gendarmes", "policier", "policiers",
        "tribunal", "justice", "juge", "procureur", "parquet", "procès", "proces",
        "enquête", "enquete", "agression", "violence", "vol", "cambriolage",
        "braquage", "drogue", "stupéfiants", "stupefiants", "trafic de drogue",
        "dégradations", "degradations", "garde à vue", "garde a vue", "plainte",
        "arme", "armes", "fusillade", "homicide", "tentative de meurtre", "accident"
    ],
    "economie_tourisme": [
        "commerce", "commerces", "commerçant", "commercant", "commerçants",
        "entreprise", "entreprises", "artisan", "artisans", "emploi", "chômage",
        "chomage", "tourisme", "touriste", "touristes", "hôtel", "hotel",
        "hôtels", "hotels", "restaurant", "restaurants", "saison", "saisonnier",
        "saisonniers", "pouvoir d'achat", "inflation", "agriculture", "agriculteur",
        "agriculteurs", "élevage", "elevage", "pêche", "peche", "cci", "subvention",
        "tarifs", "prix", "carburant", "essence", "gasoil"
    ],
    "urbanisme_logement": [
        "logement", "logements", "loyer", "loyers", "immobilier", "habitation",
        "résidence", "residence", "résidences secondaires", "residences secondaires",
        "plu", "padduc", "permis de construire", "urbanisme", "construction",
        "bâtiment", "batiment", "chantier", "travaux publics", "électricité",
        "electricite", "edf", "fibre", "réseau", "reseau", "eau potable"
    ],
    "education_jeunesse": [
        "école", "ecole", "écoles", "ecoles", "classe", "classes", "enseignant",
        "enseignants", "professeur", "professeurs", "prof", "profs", "instituteur",
        "institutrice", "collège", "college", "lycée", "lycee", "université",
        "universite", "corte", "étudiant", "etudiant", "étudiants", "etudiants",
        "cantine", "scolaire", "scolaires", "rentrée", "rentree", "grève", "greve",
        "fermeture de classe", "rectorat", "académie", "academie"
    ],
    "politique_societe_vie_locale": [
        "mairie", "maire", "conseil municipal", "élus", "elus", "collectivité de corse",
        "collectivite de corse", "assemblée de corse", "assemblee de corse",
        "délibération", "deliberation", "syndicat", "manifestation", "rassemblement",
        "association", "culture", "patrimoine", "festival", "fête", "fete", "sport"
    ],
}


def _build_keyword_processor() -> KeywordProcessor:
    """Initialise le processeur de mots-clés FlashText."""
    kp = KeywordProcessor(case_sensitive=False)
    for domain, keywords in DOMAINS_KEYWORDS.items():
        for kw in keywords:
            kp.add_keyword(kw, domain)
    return kp


_KEYWORD_PROCESSOR = _build_keyword_processor()


def classify_document(title: str, raw_text: str, source_category: str = None) -> str:
    """
    Détecte le domaine principal d'un document basé sur le titre et un extrait de texte.
    Retourne le domaine ayant le plus grand nombre d'occurrences de mots-clés.
    Si aucun mot-clé n'est détecté, retourne 'politique_societe_vie_locale'.
    """
    text_sample = f"{title or ''} {(raw_text or '')[:1000]} {source_category or ''}"
    keywords_found = _KEYWORD_PROCESSOR.extract_keywords(text_sample)
    
    if not keywords_found:
        return "politique_societe_vie_locale"
    
    # Compte les occurrences par domaine
    counts = defaultdict(int)
    for dom in keywords_found:
        counts[dom] += 1
    
    # Domaine prédominant
    best_domain = max(counts, key=counts.get)
    return best_domain


def group_documents_into_batches(
    documents: List[dict],
    batch_size: int = 8,
    min_batch_size: int = 2,
    domain_field: str = "domaine_principal",
) -> List[Dict]:
    """
    Regroupe une liste de documents bruts STRICTEMENT par domaine thématique,
    puis découpe chaque domaine en lots homogènes.
    
    RÈGLE ABSOLUE : Les reliquats d'un domaine ne sont JAMAIS mélangés avec un autre domaine.
    Si un domaine contient 10 documents, il produit par exemple 1 lot de 8 et 1 lot de 2 (du même domaine).
    
    Retourne une liste de structures de lot :
    [
        {
            "domaine": "sante_secours",
            "documents": [doc1, doc2, ... doc8]
        },
        ...
    ]
    """
    # 1. Partition stricte par domaine
    by_domain = defaultdict(list)
    for doc in documents:
        # Si le document a déjà un domaine pré-calculé (ex: L1/L2)
        dom = doc.get(domain_field) or doc.get("domaine_principal") or doc.get("domaine")
        if not dom:
            dom = classify_document(
                title=doc.get("title", ""),
                raw_text=doc.get("raw_text", ""),
                source_category=doc.get("source_category", "")
            )
        by_domain[dom].append(doc)
    
    batches = []
    
    # 2. Découpage en lots au sein de CHAQUE domaine individuellement
    for dom, docs in by_domain.items():
        total_docs = len(docs)
        if total_docs == 0:
            continue
            
        # Si le domaine a moins que la taille d'un lot, on fait un seul lot de ce domaine
        if total_docs <= batch_size:
            batches.append({
                "domaine": dom,
                "documents": docs
            })
            continue
            
        # Sinon découpage par tranche de batch_size
        for i in range(0, total_docs, batch_size):
            chunk = docs[i : i + batch_size]
            
            # Si le dernier morceau est trop petit (ex: 1 doc seul), on le rattache au lot précédent du même domaine
            if len(chunk) < min_batch_size and batches and batches[-1]["domaine"] == dom:
                batches[-1]["documents"].extend(chunk)
            else:
                batches.append({
                    "domaine": dom,
                    "documents": chunk
                })
            
    return batches