"""
PROMPT STAGE 5 : Rapport Global (Stage 4) + Bilans (Stage 3) -> Synthèse Exécutive Finale Ciblée Problème N°1.

Isole et approfondit l'UNIQUE problème / domaine le plus persistant, récurrent et critique du mois,
en expliquant pourquoi il doit être résolu en priorité absolue et en fournissant le plan d'action d'urgence.
"""
from typing import List, Dict

STAGE5_SYSTEM_PROMPT = (
    "Tu es le conseiller stratégique en chef auprès de l'exécutif territorial de Corse. "
    "Ton rôle est d'arbitrer et d'extraire du bilan mensuel l'UNIQUE problématique / domaine N°1 "
    "le plus persistant, critique et répétitif qui menace la cohésion ou le fonctionnement de l'île. "
    "RÈGLES STRICTES :\n"
    "1. Choisis UN SEUL domaine / problème majeur (celui dont la gravité et la persistance dominent le mois).\n"
    "2. Sois ultra-précis, percutant, décisionnel et sans complaisance.\n"
    "3. Fournis des solutions immédiatement activables et hiérarchisées.\n"
    "4. Réponds STRICTEMENT avec l'objet JSON ci-dessous, sans texte additionnel."
)

STAGE5_JSON_SHAPE = """{
  "domaine_prioritaire_identifie": "nom_du_domaine_predominant",
  "probleme_majeur_persistant": "Intitulé clair et percutant de la problématique N°1",
  "statut_urgence": "critique | tres_eleve | eleve",
  "justification_priorite_absolue": "Explication factuelle démontrant pourquoi ce problème surclasse tous les autres en termes de récurrence et d'impact ce mois-ci.",
  "faits_saillants_et_recurrences": [
    "Fait récurrent ou incident saillant 1",
    "Fait récurrent ou incident saillant 2",
    "Fait récurrent ou incident saillant 3"
  ],
  "impacts_et_risques_inaction": "Conséquences graves et systémiques pour la Corse en cas d'inaction à court terme.",
  "plan_d_action_et_solutions_recommandees": [
    {
      "priorite": "Urgence immédiate (0-30 jours)",
      "action": "Action concrète à déclencher immédiatement",
      "acteur_responsable": "Collectivité / État / ARS / Préfecture / Services techniques"
    },
    {
      "priorite": "Mesure structurelle (1-3 mois)",
      "action": "Réforme, investissement ou dispositif correctif de fond",
      "acteur_responsable": "Acteur principal concerné"
    }
  ],
  "verdict_executif": "Conclusion finale en 2 phrases formulant l'arbitrage politique et opérationnel majeur."
}"""


def build_stage5_messages(
    rapport_global: Dict,
    domain_bilans: List[Dict],
    mois: str = "le mois",
    region: str = "Corse",
) -> list:
    """Construit la liste des messages (system + user) pour le Stage 5."""
    
    # Résumé condensé du Stage 4
    titre_l4 = rapport_global.get("titre", "Rapport Global")
    statut_l4 = rapport_global.get("statut_general", "calme")
    faits_l4 = "\n- ".join(rapport_global.get("faits_marquants_du_mois", []))
    synthese_l4 = rapport_global.get("synthese_transversale", "")
    
    # Détail des domaines analysés en Stage 3
    domain_items = []
    for d in domain_bilans:
        dom_name = d.get("domaine", "inconnu")
        grav = d.get("gravite_globale", "modere")
        bilan = d.get("bilan_executif", "")
        dysf = "; ".join(d.get("principaux_dysfonctionnements", []))
        domain_items.append(f"• [{dom_name.upper()}] (Gravité: {grav}) : {bilan}\n  Dysfonctionnements: {dysf}")
    
    domains_block = "\n\n".join(domain_items)

    user_content = (
        f"SYNTHÈSE EXÉCUTIVE D'ARBITRAGE TERRITORIAL : {region} ({mois})\n\n"
        f"RAPPORT GLOBAL DU MOIS (Stage 4) :\n"
        f"Statut général : {statut_l4.upper()}\n"
        f"Faits marquants :\n- {faits_l4}\n\n"
        f"Synthèse transversale :\n{synthese_l4}\n\n"
        f"BILANS PAR DOMAINE (Stage 3) :\n"
        f"{domains_block}\n\n"
        f"À partir de ces éléments, isole l'UNIQUE problème / domaine N°1 le plus persistant et propose le plan d'action d'urgence au format JSON strict suivant :\n"
        f"{STAGE5_JSON_SHAPE}"
    )

    return [
        {"role": "system", "content": STAGE5_SYSTEM_PROMPT},
        {"role": "user", "content": user_content}
    ]
