"""
PROMPT STAGE 2 : Synthèses L1 (Niveau 1) -> Méso-synthèse (Niveau 2).

Consolide un lot de 6 à 8 micro-synthèses L1 d'un même domaine
pour dégager une vision méso-territoriale.

Les prompts et formats sont configurables dans :
- System_Prompt.md (section ## STAGE 2)
- System_Traitement.md (section ## STAGE 2)
"""
from typing import List, Dict
from src.llm.prompts.prompt_loader import get_system_prompt, get_json_shape

# Chargement dynamique depuis System_Prompt.md et System_Traitement.md
STAGE2_SYSTEM_PROMPT = get_system_prompt(2)
STAGE2_JSON_SHAPE = get_json_shape(2)


def build_stage2_messages(l1_syntheses: List[Dict], domaine: str) -> list:
    """Construit la liste des messages (system + user) pour le Stage 2."""
    system_prompt = get_system_prompt(2)
    json_shape = get_json_shape(2)

    items = []
    for idx, syn in enumerate(l1_syntheses, start=1):
        resume = syn.get("resume_court", "")
        prob = syn.get("problematique_identifiee", "")
        grav = syn.get("gravite", "modere")
        cause = syn.get("cause", "")
        preuve = syn.get("preuve", "")
        besoins = syn.get("besoins_reels_detectes", "")
        items.append(
            f"[{idx}] Gravité: {grav} | Problème: {prob}\n"
            f"Résumé: {resume}\n"
            f"Cause identifiée: {cause or 'N/A'}\n"
            f"Preuve/Faits: {preuve or 'N/A'}\n"
            f"Besoins: {besoins}"
        )
    
    syntheses_block = "\n\n".join(items)
    user_content = (
        f"THÉMATIQUE CONSOLIDÉE : {domaine.upper()}\n"
        f"Voici {len(l1_syntheses)} micro-synthèses de terrain déjà consolidées :\n\n"
        f"{syntheses_block}\n\n"
        f"Produis la méso-synthèse intermédiaire au format JSON strict suivant :\n{json_shape}"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]
