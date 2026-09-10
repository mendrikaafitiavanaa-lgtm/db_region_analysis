"""
PROMPT STAGE 2 : Synthèses L1 (Niveau 1) -> Méso-synthèse (Niveau 2).

Consolide un lot de 6 à 8 micro-synthèses L1 d'un même domaine
pour dégager une vision méso-territoriale.
"""
from typing import List, Dict

STAGE2_SYSTEM_PROMPT = (
    "Tu es un analyste territorial senior expert de la région Corse. "
    "Tu consolides un ensemble de micro-synthèses thématiques de terrain pour identifier "
    "les dynamiques territoriales et les impacts cumulés. "
    "RÈGLES STRICTES :\n"
    "1. Sois synthétique, analytique et percutant.\n"
    "2. Détermine la gravité globale consolidée du lot.\n"
    "3. Réponds STRICTEMENT avec l'objet JSON ci-dessous."
)

STAGE2_JSON_SHAPE = """{
  "gravite": "faible | modere | grave",
  "resume_consolide": "Synthèse consolidée intégrant les faits saillants des micro-synthèses.",
  "tendance_majeure": "Tendance de fond ou aggravation observée sur cette zone géographique.",
  "impacts_territoriaux": "Impacts cumulés sur le fonctionnement des services ou de la population.",
  "actions_prioritaires": "Actions collectives d'urgence ou correctives structurelles requises."
}"""


def build_stage2_messages(l1_syntheses: List[Dict], domaine: str) -> list:
    """Construit la liste des messages (system + user) pour le Stage 2."""
    items = []
    for idx, syn in enumerate(l1_syntheses, start=1):
        resume = syn.get("resume_court", "")
        prob = syn.get("problematique_identifiee", "")
        grav = syn.get("gravite", "modere")
        besoins = syn.get("besoins_reels_detectes", "")
        items.append(f"[{idx}] Gravité: {grav} | Problème: {prob}\nRésumé: {resume}\nBesoins: {besoins}")
    
    syntheses_block = "\n\n".join(items)
    user_content = (
        f"THÉMATIQUE CONSOLIDÉE : {domaine.upper()}\n"
        f"Voici {len(l1_syntheses)} micro-synthèses de terrain déjà consolidées :\n\n"
        f"{syntheses_block}\n\n"
        f"Produis la méso-synthèse intermédiaire au format JSON strict suivant :\n{STAGE2_JSON_SHAPE}"
    )
    return [
        {"role": "system", "content": STAGE2_SYSTEM_PROMPT},
        {"role": "user", "content": user_content}
    ]
