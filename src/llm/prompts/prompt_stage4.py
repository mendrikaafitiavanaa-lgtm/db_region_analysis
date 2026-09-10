"""
PROMPT STAGE 4 : Bilans de Domaine (Niveau 3) -> Rapport Stratégique Territorial Global (Niveau 4 - Sommet).

Croise tous les bilans thématiques (Santé, Transports, Sécurité, Environnement, Économie, etc.)
pour rédiger le Rapport Exécutif Territorial Global pour la Corse.
"""
from typing import List, Dict

STAGE4_SYSTEM_PROMPT = (
    "Tu es le haut conseiller stratégique auprès des décideurs de la région Corse. "
    "Tu rédiges le rapport exécutif mensuel consolidé au plus haut niveau de décision. "
    "RÈGLES STRICTES :\n"
    "1. Analyse transversale et croisée (ex: surtourisme créant une tension sur l'eau + saturation des urgences + hausse des feux).\n"
    "2. Sois percutant, hiérarchisé et décisionnel.\n"
    "3. Réponds STRICTEMENT avec l'objet JSON ci-dessous."
)

STAGE4_JSON_SHAPE = """{
  "titre": "Rapport Stratégique Territorial - Corse (Mois)",
  "statut_general": "calme | sous_tension | critique",
  "faits_marquants_du_mois": [
    "Fait marquant transversal majeur 1",
    "Fait marquant transversal majeur 2",
    "Fait marquant transversal majeur 3"
  ],
  "synthese_transversale": "Analyse systémique globale croisant les dynamiques sectorielles observées sur l'île.",
  "tableau_de_bord_domaines": [
    {
      "domaine": "nom_du_domaine",
      "gravite": "faible | modere | grave",
      "resume_cle": "Synthèse d'impact du domaine en une phrase percutante."
    }
  ],
  "recommandations_prioritaires_decideurs": [
    "Décision d'arbitrage ou action d'urgence 1",
    "Mesure de coordination interservices 2",
    "Plan de résilience ou investissement prioritaire 3"
  ]
}"""


def build_stage4_messages(domain_bilans: List[Dict], mois: str = "le mois", region: str = "Corse") -> list:
    """Construit la liste des messages (system + user) pour le Stage 4."""
    items = []
    for idx, bilan in enumerate(domain_bilans, start=1):
        dom = bilan.get("domaine", "Domaine inconnu")
        grav = bilan.get("gravite_globale", "modere")
        exec_summary = bilan.get("bilan_executif", "")
        pts_chauds = "; ".join(bilan.get("points_chauds_geographiques", []))
        dysf = "; ".join(bilan.get("principaux_dysfonctionnements", []))
        precos = "; ".join(bilan.get("preconisations_strategiques", []))
        
        items.append(
            f"=== [DOMAINE {idx}] {dom.upper()} | Statut: {grav.upper()} ===\n"
            f"Bilan Sectoriel: {exec_summary}\n"
            f"Points chauds: {pts_chauds or 'N/A'}\n"
            f"Dysfonctionnements: {dysf or 'N/A'}\n"
            f"Préconisations sectorielles: {precos or 'N/A'}"
        )
    
    bilans_block = "\n\n".join(items)
    user_content = (
        f"PÉRIODE D'ANALYSE : {mois} | TERRITOIRE : {region}\n"
        f"Voici les bilans sectoriels de tous les domaines analysés :\n\n"
        f"{bilans_block}\n\n"
        f"Produis le RAPPORT STRATÉGIQUE TERRITORIAL GLOBAL au format JSON strict suivant :\n{STAGE4_JSON_SHAPE}"
    )
    return [
        {"role": "system", "content": STAGE4_SYSTEM_PROMPT},
        {"role": "user", "content": user_content}
    ]
