"""
PROMPT STAGE 4 : Bilans de Domaine (Niveau 3) -> Rapport Stratégique Territorial Global (Niveau 4 - Sommet).

Croise tous les bilans thématiques (Santé, Transports, Sécurité, Environnement, Économie, etc.)
pour rédiger le Rapport Exécutif Territorial Global pour la Corse.

Les prompts et formats sont configurables dans :
- System_Prompt.md (section ## STAGE 4)
- System_Traitement.md (section ## STAGE 4)
"""
from typing import List, Dict
from src.llm.prompts.prompt_loader import get_system_prompt, get_json_shape

# Chargement dynamique depuis System_Prompt.md et System_Traitement.md
STAGE4_SYSTEM_PROMPT = get_system_prompt(4)
STAGE4_JSON_SHAPE = get_json_shape(4)


def build_stage4_messages(domain_bilans: List[Dict], mois: str = "le mois", region: str = "Corse") -> list:
    """Construit la liste des messages (system + user) pour le Stage 4."""
    system_prompt = get_system_prompt(4)
    json_shape = get_json_shape(4)

    items = []
    for idx, bilan in enumerate(domain_bilans, start=1):
        dom = bilan.get("domaine", "Domaine inconnu")
        grav = bilan.get("gravite_globale", "modere")
        exec_summary = bilan.get("bilan_executif", "")
        cause = bilan.get("cause", "")
        preuve = bilan.get("preuve", "")
        pts_chauds = "; ".join(bilan.get("points_chauds_geographiques", []))
        dysf = "; ".join(bilan.get("principaux_dysfonctionnements", []))
        precos = "; ".join(bilan.get("preconisations_strategiques", []))
        
        items.append(
            f"=== [DOMAINE {idx}] {dom.upper()} | Statut: {grav.upper()} ===\n"
            f"Bilan Sectoriel: {exec_summary}\n"
            f"Cause identifiée: {cause or 'N/A'}\n"
            f"Preuve/Faits: {preuve or 'N/A'}\n"
            f"Points chauds: {pts_chauds or 'N/A'}\n"
            f"Dysfonctionnements: {dysf or 'N/A'}\n"
            f"Préconisations sectorielles: {precos or 'N/A'}"
        )
    
    bilans_block = "\n\n".join(items)
    user_content = (
        f"PÉRIODE D'ANALYSE : {mois} | TERRITOIRE : {region}\n"
        f"Voici les bilans sectoriels de tous les domaines analysés :\n\n"
        f"{bilans_block}\n\n"
        f"Produis le RAPPORT STRATÉGIQUE TERRITORIAL GLOBAL au format JSON strict suivant :\n{json_shape}"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]
