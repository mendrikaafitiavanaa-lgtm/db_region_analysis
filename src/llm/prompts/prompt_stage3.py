"""
PROMPT STAGE 3 : Méso-synthèses L2 (Niveau 2) -> Grand Bilan Mensuel de Domaine (Niveau 3).

Synthétise l'ensemble des méso-synthèses d'un domaine pour produire le Bilan
Mensuel Sectoriel complet pour toute la Corse.
"""
from typing import List, Dict

STAGE3_SYSTEM_PROMPT = (
    "Tu es un directeur de cabinet expert en prospective et gestion publique pour la Corse. "
    "Tu rédiges le bilan mensuel officiel d'un grand domaine d'action publique sur le territoire. "
    "RÈGLES STRICTES :\n"
    "1. Adopte une vision stratégique et territoriale claire.\n"
    "2. Identifie précisément les points chauds géographiques et dysfonctionnements majeurs.\n"
    "3. Fournis des préconisations concrètes pour les décideurs.\n"
    "4. Réponds STRICTEMENT avec l'objet JSON ci-dessous."
)

STAGE3_JSON_SHAPE = """{
  "gravite_globale": "faible | modere | grave",
  "bilan_executif": "Bilan complet et structuré du domaine sur l'ensemble du mois pour la Corse.",
  "points_chauds_geographiques": [
    "Lieu/Secteur A : nature des difficultés observées",
    "Lieu/Secteur B : faits notables ou tensions"
  ],
  "principaux_dysfonctionnements": [
    "Dysfonctionnement ou risque critique 1",
    "Dysfonctionnement ou risque critique 2"
  ],
  "preconisations_strategiques": [
    "Mesure structurelle prioritaire 1",
    "Mesure d'urgence ou accompagnement 2"
  ]
}"""


def build_stage3_messages(l2_syntheses: List[Dict], domaine: str, mois: str = "le mois") -> list:
    """Construit la liste des messages (system + user) pour le Stage 3."""
    items = []
    for idx, syn in enumerate(l2_syntheses, start=1):
        resume = syn.get("resume_consolide") or syn.get("resume_court", "")
        tendance = syn.get("tendance_majeure") or syn.get("problematique_identifiee", "")
        grav = syn.get("gravite", "modere")
        impacts = syn.get("impacts_territoriaux", "")
        items.append(f"[{idx}] Gravité: {grav} | Tendance: {tendance}\nSynthèse: {resume}\nImpacts: {impacts}")
    
    syntheses_block = "\n\n".join(items)
    user_content = (
        f"BILAN MENSUEL DU DOMAINE : {domaine.upper()} (Période : {mois})\n"
        f"Voici les {len(l2_syntheses)} synthèses consolidées disponibles pour ce domaine :\n\n"
        f"{syntheses_block}\n\n"
        f"Produis le GRAND BILAN MENSUEL DU DOMAINE au format JSON strict suivant :\n{STAGE3_JSON_SHAPE}"
    )
    return [
        {"role": "system", "content": STAGE3_SYSTEM_PROMPT},
        {"role": "user", "content": user_content}
    ]
