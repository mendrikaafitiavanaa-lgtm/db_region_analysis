"""
PROMPT STAGE 3 : Méso-synthèses L2 (Niveau 2) -> Grand Bilan Mensuel de Domaine (Niveau 3).

Synthétise l'ensemble des méso-synthèses d'un domaine pour produire le Bilan
Mensuel Sectoriel complet pour toute la Corse.

Les prompts et formats sont configurables dans :
- System_Prompt.md (section ## STAGE 3)
- System_Traitement.md (section ## STAGE 3)
"""
from typing import List, Dict
from src.llm.prompts.prompt_loader import get_system_prompt, get_json_shape

# Chargement dynamique depuis System_Prompt.md et System_Traitement.md
STAGE3_SYSTEM_PROMPT = get_system_prompt(3)
STAGE3_JSON_SHAPE = get_json_shape(3)


def build_stage3_messages(l2_syntheses: List[Dict], domaine: str, mois: str = "le mois") -> list:
    """Construit la liste des messages (system + user) pour le Stage 3."""
    system_prompt = get_system_prompt(3)
    json_shape = get_json_shape(3)

    items = []
    for idx, syn in enumerate(l2_syntheses, start=1):
        resume = syn.get("resume_consolide") or syn.get("resume_court", "")
        tendance = syn.get("tendance_majeure") or syn.get("problematique_identifiee", "")
        grav = syn.get("gravite", "modere")
        cause = syn.get("cause", "")
        preuve = syn.get("preuve", "")
        impacts = syn.get("impacts_territoriaux", "")
        items.append(
            f"[{idx}] Gravité: {grav} | Tendance: {tendance}\n"
            f"Synthèse: {resume}\n"
            f"Cause: {cause or 'N/A'}\n"
            f"Preuve: {preuve or 'N/A'}\n"
            f"Impacts: {impacts}"
        )
    
    syntheses_block = "\n\n".join(items)
    user_content = (
        f"BILAN MENSUEL DU DOMAINE : {domaine.upper()} (Période : {mois})\n"
        f"Voici les {len(l2_syntheses)} synthèses consolidées disponibles pour ce domaine :\n\n"
        f"{syntheses_block}\n\n"
        f"Produis le GRAND BILAN MENSUEL DU DOMAINE au format JSON strict suivant :\n{json_shape}"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]
