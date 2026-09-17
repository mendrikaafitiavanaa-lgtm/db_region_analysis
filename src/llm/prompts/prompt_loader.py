"""
Module de chargement dynamique des prompts et gabarits de traitement.

Permet de charger les System Prompts depuis `System_Prompt.md`
et les gabarits JSON depuis `System_Traitement.md` sans modifier le code Python.
"""
import os
import re
from pathlib import Path
from typing import Dict, Optional

_PROMPTS_DIR = Path(__file__).resolve().parent
_SYSTEM_PROMPT_FILE = _PROMPTS_DIR / "System_Prompt.md"
_SYSTEM_TRAITEMENT_FILE = _PROMPTS_DIR / "System_Traitement.md"

# Valeurs de secours (fallback) si les fichiers markdown sont absents ou corrompus
_DEFAULT_SYSTEM_PROMPTS = {
    1: (
        "Tu es un analyste territorial senior expert de la région Corse. "
        "Tu synthétises des faits bruts d'un même domaine d'intervention sans inventer aucune donnée. "
        "RÈGLES STRICTES :\n"
        "1. Reste factuel, précis, concis (1 à 2 phrases par champ) sans rien inventer.\n"
        "2. Détecte la problématique récurrente, la cause factuelle exacte tirée des faits réels et les preuves tangibles/chiffrées rapportées par les sources.\n"
        "3. Réponds STRICTEMENT avec l'objet JSON ci-dessous, sans Markdown additionnel ni verbiage."
    ),
    2: (
        "Tu es un analyste territorial senior expert de la région Corse. "
        "Tu consolides un ensemble de micro-synthèses thématiques de terrain pour identifier "
        "les dynamiques territoriales, les causes profondes communes et les preuves factuelles cumulées. "
        "RÈGLES STRICTES :\n"
        "1. Sois synthétique, analytique et percutant, sans inventer de faits.\n"
        "2. Détermine la cause consolidée et synthétise les preuves tangibles (chiffres, faits clés).\n"
        "3. Réponds STRICTEMENT avec l'objet JSON ci-dessous."
    ),
    3: (
        "Tu es un directeur de cabinet expert en prospective et gestion publique pour la Corse. "
        "Tu rédiges le bilan mensuel officiel d'un grand domaine d'action publique sur le territoire. "
        "RÈGLES STRICTES :\n"
        "1. Adopte une vision stratégique et territoriale claire sans inventer de données.\n"
        "2. Détermine la cause structurelle/racine dominante du domaine et synthétise les preuves matérielles/chiffrées du terrain.\n"
        "3. Identifie précisément les points chauds géographiques et dysfonctionnements majeurs.\n"
        "4. Fournis des préconisations concrètes pour les décideurs.\n"
        "5. Réponds STRICTEMENT avec l'objet JSON ci-dessous."
    ),
    4: (
        "Tu es le haut conseiller stratégique auprès des décideurs de la région Corse. "
        "Tu rédiges le rapport exécutif mensuel consolidé au plus haut niveau de décision. "
        "RÈGLES STRICTES :\n"
        "1. Analyse transversale et croisée (ex: surtourisme créant une tension sur l'eau + saturation des urgences + hausse des feux) sans inventer de faits.\n"
        "2. Identifie les causes profondes transversales et rassemble les preuves tangibles/chiffrées globales.\n"
        "3. Sois percutant, hiérarchisé et décisionnel.\n"
        "4. Réponds STRICTEMENT avec l'objet JSON ci-dessous."
    ),
    5: (
        "Tu es le conseiller stratégique en chef auprès de l'exécutif territorial de Corse. "
        "Ton rôle est d'arbitrer et d'extraire du bilan mensuel l'UNIQUE problématique / domaine N°1 "
        "le plus persistant, critique et répétitif qui menace la cohésion ou le fonctionnement de l'île. "
        "RÈGLES STRICTES :\n"
        "1. Choisis UN SEUL domaine / problème majeur (celui dont la gravité et la persistance dominent le mois).\n"
        "2. Détermine la cause racine incontestable et cite les preuves formelles/chiffrées sans rien inventer.\n"
        "3. Sois ultra-précis, percutant, décisionnel et sans complaisance.\n"
        "4. Fournis des solutions immédiatement activables et hiérarchisées selon le cas factuel.\n"
        "5. Réponds STRICTEMENT avec l'objet JSON ci-dessous, sans texte additionnel."
    ),
}

_DEFAULT_JSON_SHAPES = {
    1: """{
  "gravite": "faible | modere | grave",
  "resume_court": "Synthèse factuelle en 1 à 2 phrases du lot de signalements.",
  "problematique_identifiee": "Problématique récurrente ou incident saillant constaté sur l'ensemble du lot.",
  "cause": "Cause factuelle et réelle de l'événement ou de la situation tirée des documents sources (sans invention).",
  "preuve": "Éléments probants, chiffres concrets, faits tangibles ou constats rapportés par les sources attestant de la situation.",
  "consequence_potentielle": "Risque direct pour la population, les services publics ou l'écosystème.",
  "besoins_reels_detectes": "Besoins prioritaires constatés sur le terrain.",
  "solutions_recommandees": "Actions concrètes préconisées à court/moyen terme adaptées à la situation."
}""",
    2: """{
  "gravite": "faible | modere | grave",
  "resume_consolide": "Synthèse consolidée intégrant les faits saillants des micro-synthèses.",
  "tendance_majeure": "Tendance de fond ou aggravation observée sur cette zone géographique.",
  "cause": "Causes structurelles ou directes communes identifiées à partir des micro-synthèses (sans invention).",
  "preuve": "Preuves tangibles, données chiffrées cumulées ou faits marquants corroborés par les synthèses de terrain.",
  "impacts_territoriaux": "Impacts cumulés sur le fonctionnement des services ou de la population.",
  "actions_prioritaires": "Actions collectives d'urgence ou correctives structurelles requises."
}""",
    3: """{
  "gravite_globale": "faible | modere | grave",
  "bilan_executif": "Bilan complet et structuré du domaine sur l'ensemble du mois pour la Corse.",
  "cause": "Cause structurelle ou facteur déclencheur majeur expliquant les difficultés du domaine ce mois-ci.",
  "preuve": "Données probantes, statistiques globales, indicateurs factuels ou constats clés étayant ce bilan sectoriel.",
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
}""",
    4: """{
  "titre": "Rapport Stratégique Territorial - Corse (Mois)",
  "statut_general": "calme | sous_tension | critique",
  "cause": "Causes profondes, systémiques ou transversales expliquant l'état global du territoire ce mois-ci.",
  "preuve": "Preuves tangibles, indicateurs clés et faits marquants transversaux vérifiables corroborant la situation.",
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
}""",
    5: """{
  "domaine_prioritaire_identifie": "nom_du_domaine_predominant",
  "probleme_majeur_persistant": "Intitulé clair et percutant de la problématique N°1",
  "cause": "Cause racine ou origine structurelle prouvée expliquant pourquoi ce problème persiste.",
  "preuve": "Preuves tangibles, données chiffrées précises ou faits réels documentés attestant de la gravité absolue du problème.",
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
}""",
}


def _extract_section_content(markdown_text: str, stage: int, is_json: bool = False) -> Optional[str]:
    """
    Extrait le contenu d'un stage (1 à 5) depuis le markdown.
    Recherche un header comme `## STAGE X` jusqu'au prochain header ou fin de fichier.
    Extrait en priorité les blocs de code (```text ou ```json ou ```).
    """
    pattern = rf"##\s*STAGE\s*{stage}\b.*?(?=\n##\s*STAGE|\Z)"
    match = re.search(pattern, markdown_text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None

    section_text = match.group(0)

    # Recherche de bloc de code ```json ... ``` ou ```text ... ``` ou ``` ... ```
    if is_json:
        code_block = re.search(r"```(?:json)?\s*\n(.*?)\n```", section_text, flags=re.DOTALL)
    else:
        code_block = re.search(r"```(?:text)?\s*\n(.*?)\n```", section_text, flags=re.DOTALL)

    if code_block:
        return code_block.group(1).strip()

    # Si pas de bloc de code, nettoyer les commentaires HTML et extraire le texte brut
    clean_text = re.sub(r"<!--.*?-->", "", section_text, flags=re.DOTALL)
    # Supprimer la ligne de titre
    clean_text = re.sub(r"^##.*?\n", "", clean_text, flags=re.IGNORECASE).strip()
    return clean_text if clean_text else None


def load_system_prompts() -> Dict[int, str]:
    """Charge tous les system prompts depuis System_Prompt.md."""
    prompts = dict(_DEFAULT_SYSTEM_PROMPTS)
    if not _SYSTEM_PROMPT_FILE.exists():
        return prompts

    try:
        content = _SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
        for stage in range(1, 6):
            extracted = _extract_section_content(content, stage, is_json=False)
            if extracted:
                prompts[stage] = extracted
    except Exception:
        # En cas d'erreur de lecture, conserver les valeurs par défaut
        pass

    return prompts


def load_json_shapes() -> Dict[int, str]:
    """Charge tous les gabarits JSON depuis System_Traitement.md."""
    shapes = dict(_DEFAULT_JSON_SHAPES)
    if not _SYSTEM_TRAITEMENT_FILE.exists():
        return shapes

    try:
        content = _SYSTEM_TRAITEMENT_FILE.read_text(encoding="utf-8")
        for stage in range(1, 6):
            extracted = _extract_section_content(content, stage, is_json=True)
            if extracted:
                shapes[stage] = extracted
    except Exception:
        # En cas d'erreur de lecture, conserver les valeurs par défaut
        pass

    return shapes


def get_system_prompt(stage: int) -> str:
    """Récupère le prompt système pour un stage donné (1 à 5)."""
    prompts = load_system_prompts()
    return prompts.get(stage, _DEFAULT_SYSTEM_PROMPTS.get(stage, ""))


def get_json_shape(stage: int) -> str:
    """Récupère le gabarit JSON pour un stage donné (1 à 5)."""
    shapes = load_json_shapes()
    return shapes.get(stage, _DEFAULT_JSON_SHAPES.get(stage, ""))
