"""
PROMPT STAGE 1 : Faits bruts (Niveau 0) -> Micro-synthèse (Niveau 1).

Analyse un lot de 6 à 8 documents d'un même domaine pour en extraire
une micro-synthèse factuelle et structurée.
"""
from typing import List, Dict
from config import settings

STAGE1_SYSTEM_PROMPT = (
    "Tu es un analyste territorial senior expert de la région Corse. "
    "Tu synthétises des faits bruts d'un même domaine d'intervention sans inventer aucune donnée. "
    "RÈGLES STRICTES :\n"
    "1. Reste factuel, précis, concis (1 à 2 phrases par champ).\n"
    "2. Détecte la problématique récurrente ou l'événement critique commun au lot.\n"
    "3. Réponds STRICTEMENT avec l'objet JSON ci-dessous, sans Markdown additionnel ni verbiage."
)

STAGE1_JSON_SHAPE = """{
  "gravite": "faible | modere | grave",
  "resume_court": "Synthèse factuelle en 1 à 2 phrases du lot de signalements.",
  "problematique_identifiee": "Problématique récurrente ou incident saillant constaté sur l'ensemble du lot.",
  "consequence_potentielle": "Risque direct pour la population, les services publics ou l'écosystème.",
  "besoins_reels_detectes": "Besoins prioritaires constatés sur le terrain.",
  "solutions_recommandees": "Actions concrètes préconisées à court/moyen terme."
}"""


def build_stage1_messages(documents: List[Dict], domaine: str) -> list:
    """Construit la liste des messages (system + user) pour le Stage 1."""
    items = []
    for idx, doc in enumerate(documents, start=1):
        title = doc.get("title", "Sans titre")
        muni = doc.get("municipality") or doc.get("department") or "Corse"
        raw_text = (doc.get("raw_text", "") or "")[: settings.RAW_TEXT_MAX_CHARS]
        pub_date = str(doc.get("publication_date") or "")[:10]
        items.append(f"[{idx}] Lieu: {muni} ({pub_date}) | Titre: {title}\nExtrait: {raw_text}")
    
    docs_block = "\n\n".join(items)
    user_content = (
        f"THÉMATIQUE EXCLUSIVE : {domaine.upper()}\n"
        f"Voici {len(documents)} faits bruts collectés sur ce domaine :\n\n"
        f"{docs_block}\n\n"
        f"Produis la micro-synthèse d'analyse au format JSON strict suivant :\n{STAGE1_JSON_SHAPE}"
    )
    return [
        {"role": "system", "content": STAGE1_SYSTEM_PROMPT},
        {"role": "user", "content": user_content}
    ]
