"""Parse et valide les réponses JSON du LLM pour chaque étage de la pyramide."""
import json
import re
from typing import List, Union, Dict


class ParsingError(Exception):
    pass


def _clean_json_text(raw_response: str) -> str:
    cleaned = raw_response.strip()
    
    # 1. Si format ```json ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # 2. Chercher le premier '{' et le dernier '}'
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return cleaned[first_brace : last_brace + 1].strip()

    return cleaned


def _normalize_gravite(val: str) -> str:
    v = str(val or "").lower().strip()
    if any(k in v for k in ["grave", "eleve", "critique", "severe"]):
        return "grave"
    elif any(k in v for k in ["faible", "mineur", "bas"]):
        return "faible"
    return "modere"


def parse_stage1_response(raw_response: str) -> dict:
    """Parse et valide la réponse du Stage 1 (micro-synthèse)."""
    cleaned = _clean_json_text(raw_response)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ParsingError(f"JSON invalide (Stage 1): {exc}") from exc

    if isinstance(data, list) and data:
        data = data[0]
    if not isinstance(data, dict):
        raise ParsingError(f"Format JSON invalide (Stage 1), attendu dict, reçu: {type(data)}")

    data["gravite"] = _normalize_gravite(data.get("gravite", "modere"))
    for field in ["resume_court", "problematique_identifiee", "consequence_potentielle", "besoins_reels_detectes", "solutions_recommandees"]:
        if not data.get(field):
            data[field] = f"Information non consolidée pour {field}"

    return data


def parse_stage2_response(raw_response: str) -> dict:
    """Parse et valide la réponse du Stage 2 (méso-synthèse)."""
    cleaned = _clean_json_text(raw_response)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ParsingError(f"JSON invalide (Stage 2): {exc}") from exc

    if isinstance(data, list) and data:
        data = data[0]
    if not isinstance(data, dict):
        raise ParsingError(f"Format JSON invalide (Stage 2), attendu dict, reçu: {type(data)}")

    data["gravite"] = _normalize_gravite(data.get("gravite", "modere"))
    for field in ["resume_consolide", "tendance_majeure", "impacts_territoriaux", "actions_prioritaires"]:
        if not data.get(field):
            data[field] = f"Information non consolidée pour {field}"

    return data


def parse_stage3_response(raw_response: str, fallback_domain: str = "") -> dict:
    """Parse et valide la réponse du Stage 3 (bilan de domaine)."""
    cleaned = _clean_json_text(raw_response)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ParsingError(f"JSON invalide (Stage 3): {exc}") from exc

    if isinstance(data, list) and data:
        data = data[0]
    if not isinstance(data, dict):
        raise ParsingError(f"Format JSON invalide (Stage 3), attendu dict, reçu: {type(data)}")

    data["gravite_globale"] = _normalize_gravite(data.get("gravite_globale", "modere"))
    data["bilan_executif"] = data.get("bilan_executif") or "Bilan non consolidé"
    
    for list_field in ["points_chauds_geographiques", "principaux_dysfonctionnements", "preconisations_strategiques"]:
        val = data.get(list_field)
        if not isinstance(val, list):
            data[list_field] = [str(val)] if val else []

    return data


def parse_stage4_response(raw_response: str) -> dict:
    """Parse et valide la réponse du Stage 4 (rapport global final)."""
    cleaned = _clean_json_text(raw_response)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ParsingError(f"JSON invalide (Stage 4): {exc}") from exc

    if isinstance(data, list) and data:
        data = data[0]
    if not isinstance(data, dict):
        raise ParsingError(f"Format JSON invalide (Stage 4), attendu dict, reçu: {type(data)}")

    statut = str(data.get("statut_general", "")).lower()
    if "critique" in statut:
        data["statut_general"] = "critique"
    elif "tension" in statut:
        data["statut_general"] = "sous_tension"
    else:
        data["statut_general"] = "calme"

    data["titre"] = data.get("titre") or "Rapport Stratégique Territorial Corse"
    data["synthese_transversale"] = data.get("synthese_transversale") or "Synthèse transversale non disponible"
    
    if not isinstance(data.get("faits_marquants_du_mois"), list):
        data["faits_marquants_du_mois"] = []
    if not isinstance(data.get("tableau_de_bord_domaines"), list):
        data["tableau_de_bord_domaines"] = []
    if not isinstance(data.get("recommandations_prioritaires_decideurs"), list):
        data["recommandations_prioritaires_decideurs"] = []

    return data


def parse_stage5_response(raw_response: str) -> dict:
    """Parse et valide la réponse du Stage 5 (synthèse finale ciblée problème N°1)."""
    cleaned = _clean_json_text(raw_response)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ParsingError(f"JSON invalide (Stage 5): {exc}") from exc

    if isinstance(data, list) and data:
        data = data[0]
    if not isinstance(data, dict):
        raise ParsingError(f"Format JSON invalide (Stage 5), attendu dict, reçu: {type(data)}")

    statut = str(data.get("statut_urgency") or data.get("statut_urgence", "")).lower()
    if "critique" in statut:
        data["statut_urgence"] = "critique"
    elif "tres" in statut or "très" in statut or "severe" in statut:
        data["statut_urgence"] = "tres_eleve"
    else:
        data["statut_urgence"] = "eleve"

    data["domaine_prioritaire_identifie"] = str(data.get("domaine_prioritaire_identifie") or "general_territoire").lower().strip()
    data["probleme_majeur_persistant"] = data.get("probleme_majeur_persistant") or "Problématique territoriale majeure non spécifiée"
    data["justification_priorite_absolue"] = data.get("justification_priorite_absolue") or "Justification non consolidée"
    data["impacts_et_risques_inaction"] = data.get("impacts_et_risques_inaction") or "Risques en cours d'évaluation"
    data["verdict_executif"] = data.get("verdict_executif") or "Verdict exécutif en attente"

    if not isinstance(data.get("faits_saillants_et_recurrences"), list):
        val = data.get("faits_saillants_et_recurrences")
        data["faits_saillants_et_recurrences"] = [str(val)] if val else []

    if not isinstance(data.get("plan_d_action_et_solutions_recommandees"), list):
        val = data.get("plan_d_action_et_solutions_recommandees")
        data["plan_d_action_et_solutions_recommandees"] = [val] if isinstance(val, dict) else []

    return data

