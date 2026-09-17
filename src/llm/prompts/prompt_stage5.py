"""
PROMPT STAGE 5 : Rapport Global (Stage 4) + Bilans (Stage 3) -> Synthèse Exécutive Finale Ciblée Problème N°1.

Isole et approfondit l'UNIQUE problème / domaine le plus persistant, récurrent et critique du mois,
en expliquant pourquoi il doit être résolu en priorité absolue et en fournissant le plan d'action d'urgence.

Les prompts et formats sont configurables dans :
- System_Prompt.md (section ## STAGE 5)
- System_Traitement.md (section ## STAGE 5)
"""
from typing import List, Dict
from src.llm.prompts.prompt_loader import get_system_prompt, get_json_shape

# Chargement dynamique depuis System_Prompt.md et System_Traitement.md
STAGE5_SYSTEM_PROMPT = get_system_prompt(5)
STAGE5_JSON_SHAPE = get_json_shape(5)


def build_stage5_messages(
    rapport_global: Dict,
    domain_bilans: List[Dict],
    mois: str = "le mois",
    region: str = "Corse",
) -> list:
    """Construit la liste des messages (system + user) pour le Stage 5."""
    system_prompt = get_system_prompt(5)
    json_shape = get_json_shape(5)
    
    # Résumé condensé du Stage 4
    titre_l4 = rapport_global.get("titre", "Rapport Global")
    statut_l4 = rapport_global.get("statut_general", "calme")
    cause_l4 = rapport_global.get("cause", "")
    preuve_l4 = rapport_global.get("preuve", "")
    faits_l4 = "\n- ".join(rapport_global.get("faits_marquants_du_mois", []))
    synthese_l4 = rapport_global.get("synthese_transversale", "")
    
    # Détail des domaines analysés en Stage 3
    domain_items = []
    for d in domain_bilans:
        dom_name = d.get("domaine", "inconnu")
        grav = d.get("gravite_globale", "modere")
        bilan = d.get("bilan_executif", "")
        cause_d = d.get("cause", "")
        preuve_d = d.get("preuve", "")
        dysf = "; ".join(d.get("principaux_dysfonctionnements", []))
        domain_items.append(
            f"• [{dom_name.upper()}] (Gravité: {grav}) : {bilan}\n"
            f"  Cause: {cause_d or 'N/A'} | Preuve: {preuve_d or 'N/A'}\n"
            f"  Dysfonctionnements: {dysf}"
        )
    
    domains_block = "\n\n".join(domain_items)

    user_content = (
        f"SYNTHÈSE EXÉCUTIVE D'ARBITRAGE TERRITORIAL : {region} ({mois})\n\n"
        f"RAPPORT GLOBAL DU MOIS (Stage 4) :\n"
        f"Titre : {titre_l4}\n"
        f"Statut général : {statut_l4.upper()}\n"
        f"Cause transversale : {cause_l4 or 'N/A'}\n"
        f"Preuves globales : {preuve_l4 or 'N/A'}\n"
        f"Faits marquants :\n- {faits_l4}\n\n"
        f"Synthèse transversale :\n{synthese_l4}\n\n"
        f"BILANS PAR DOMAINE (Stage 3) :\n"
        f"{domains_block}\n\n"
        f"À partir de ces éléments, isole l'UNIQUE problème / domaine N°1 le plus persistant et propose le plan d'action d'urgence au format JSON strict suivant :\n"
        f"{json_shape}"
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]
