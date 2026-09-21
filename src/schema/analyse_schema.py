"""
Générateurs de documents normalisés pour chaque étape de la pyramide d'analyse.
Conserve la traçabilité intégrale : nom du fournisseur LLM, clé API utilisée,
horodatage exact (ex: '2026/09/21 11:00'), IDs sources, territoire et mois.
"""
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from config import settings


def _format_api_key_name(provider: str) -> str:
    """Retourne le nom explicite de la variable de clé API correspondante."""
    p = (provider or "").lower()
    if p in ("groq", "grok"):
        return "GROQ_API_KEY (ou GROK_AI_API_KEY)"
    if p in ("google", "google_aistudio", "gemini"):
        return "GOOGLE_AI_API_KEY"
    if p == "openrouter":
        return "OPENROUTER_API_KEY"
    if p in ("huggingface", "hf", "hugginface"):
        return "HUGGINGFACE_API_KEY (ou HUGGINFACE_AI_API_KEY)"
    return f"{provider.upper()}_API_KEY"


def build_stage1_document(
    source_docs: List[dict],
    analyse: dict,
    domaine: str,
    run_id: Optional[str] = None,
    lot_numero: int = 1,
    region: Optional[str] = None,
    mois: Optional[str] = None,
    territoire: Optional[str] = None,
    provider: Optional[str] = None,
) -> dict:
    now_utc = datetime.now(timezone.utc)
    document_ids = [str(doc.get("document_id")) for doc in source_docs if doc.get("document_id")]
    
    # Déduction du territoire prédominant du lot
    territoires_detectes = [doc.get("territoire") or doc.get("department") for doc in source_docs if (doc.get("territoire") or doc.get("department"))]
    territoire_val = territoire or (territoires_detectes[0] if territoires_detectes else settings.REGION)
    region_val = region or settings.REGION
    mois_val = mois or settings.MOIS_CIBLE or "general"
    llm_name = (provider or settings.LLM_PROVIDER or "groq").lower()

    sources_associees = [
        {
            "document_id": doc.get("document_id"),
            "title": doc.get("title"),
            "url": doc.get("url"),
            "municipality": doc.get("municipality"),
            "department": doc.get("department"),
            "territoire": doc.get("territoire") or doc.get("department"),
            "region": doc.get("region") or region_val,
            "source_name": doc.get("source_name"),
            "publication_date": doc.get("publication_date"),
        }
        for doc in source_docs
    ]

    date_heure_str = now_utc.strftime("%Y/%m/%d %H:%M")

    return {
        "type": "synthese_l1",
        "stage": 1,
        "region": region_val,
        "source_territoire": territoire_val,
        "department": territoire_val,
        "mois_cible": mois_val,
        "domaine_principal": domaine,
        "lot_taille": len(source_docs),
        "document_ids": document_ids,
        "sources_associees": sources_associees,
        "gravite": analyse.get("gravite", "modere"),
        "resume_court": analyse.get("resume_court", ""),
        "problematique_identifiee": analyse.get("problematique_identifiee", ""),
        "cause": analyse.get("cause", ""),
        "preuve": analyse.get("preuve", ""),
        "consequence_potentielle": analyse.get("consequence_potentielle", ""),
        "besoins_reels_detectes": analyse.get("besoins_reels_detectes", ""),
        "solutions_recommandees": analyse.get("solutions_recommandees", ""),
        "fournisseur_llm": llm_name,
        "cle_api_utilisee": _format_api_key_name(llm_name),
        "date_heure_traitement": date_heure_str,
        "date_analyse": now_utc.strftime("%Y-%m-%d"),
        "date_execution": now_utc.isoformat(),
        "meta_analyse": {
            "analysed_at": now_utc,
            "date_heure_traitement": date_heure_str,
            "run_id": run_id or f"run_l1_{now_utc.strftime('%Y-%m-%d_%Hh%M')}",
            "lot_numero": lot_numero,
            "provider": llm_name,
            "cle_api_utilisee": _format_api_key_name(llm_name),
            "mois_cible": mois_val,
            "region": region_val,
            "source_territoire": territoire_val,
        },
    }


def build_stage2_document(
    l1_docs: List[dict],
    analyse: dict,
    domaine: str,
    run_id: Optional[str] = None,
    lot_numero: int = 1,
    region: Optional[str] = None,
    mois: Optional[str] = None,
    territoire: Optional[str] = None,
    provider: Optional[str] = None,
) -> dict:
    now_utc = datetime.now(timezone.utc)
    territoires = [l1.get("source_territoire") or l1.get("department") for l1 in l1_docs if (l1.get("source_territoire") or l1.get("department"))]
    territoire_val = territoire or (territoires[0] if territoires else settings.REGION)
    region_val = region or settings.REGION
    mois_val = mois or settings.MOIS_CIBLE or "general"
    llm_name = (provider or settings.LLM_PROVIDER or "groq").lower()
    
    all_raw_doc_ids = []
    l1_synthese_ids = []
    for l1 in l1_docs:
        if l1.get("_id"):
            l1_synthese_ids.append(str(l1.get("_id")))
        all_raw_doc_ids.extend(l1.get("document_ids", []))
    
    all_raw_doc_ids = list(dict.fromkeys(all_raw_doc_ids))
    date_heure_str = now_utc.strftime("%Y/%m/%d %H:%M")

    return {
        "type": "synthese_l2",
        "stage": 2,
        "region": region_val,
        "source_territoire": territoire_val,
        "department": territoire_val,
        "mois_cible": mois_val,
        "domaine_principal": domaine,
        "lot_taille_l1": len(l1_docs),
        "total_documents_sources_couverts": len(all_raw_doc_ids),
        "l1_synthese_ids": l1_synthese_ids,
        "document_ids_sources": all_raw_doc_ids,
        "gravite": analyse.get("gravite", "modere"),
        "resume_consolide": analyse.get("resume_consolide", ""),
        "tendance_majeure": analyse.get("tendance_majeure", ""),
        "cause": analyse.get("cause", ""),
        "preuve": analyse.get("preuve", ""),
        "impacts_territoriaux": analyse.get("impacts_territoriaux", ""),
        "actions_prioritaires": analyse.get("actions_prioritaires", ""),
        "fournisseur_llm": llm_name,
        "cle_api_utilisee": _format_api_key_name(llm_name),
        "date_heure_traitement": date_heure_str,
        "date_analyse": now_utc.strftime("%Y-%m-%d"),
        "date_execution": now_utc.isoformat(),
        "meta_analyse": {
            "analysed_at": now_utc,
            "date_heure_traitement": date_heure_str,
            "run_id": run_id or f"run_l2_{now_utc.strftime('%Y-%m-%d_%Hh%M')}",
            "lot_numero": lot_numero,
            "provider": llm_name,
            "cle_api_utilisee": _format_api_key_name(llm_name),
            "mois_cible": mois_val,
            "region": region_val,
            "source_territoire": territoire_val,
        },
    }


def build_stage3_document(
    l2_docs: List[dict],
    analyse: dict,
    domaine: str,
    mois: str = "",
    region: str = "",
    territoire: str = "",
    run_id: Optional[str] = None,
    provider: Optional[str] = None,
) -> dict:
    now_utc = datetime.now(timezone.utc)
    territoire_val = territoire or settings.REGION
    region_val = region or settings.REGION
    mois_val = mois or settings.MOIS_CIBLE or "general"
    llm_name = (provider or settings.LLM_PROVIDER or "groq").lower()
    
    all_raw_doc_ids = []
    for l2 in l2_docs:
        all_raw_doc_ids.extend(l2.get("document_ids_sources", []))
    all_raw_doc_ids = list(dict.fromkeys(all_raw_doc_ids))
    date_heure_str = now_utc.strftime("%Y/%m/%d %H:%M")

    return {
        "type": "bilan_domaine",
        "stage": 3,
        "region": region_val,
        "source_territoire": territoire_val,
        "domaine": domaine,
        "mois_cible": mois_val,
        "total_syntheses_l2_utilisees": len(l2_docs),
        "total_documents_sources_couverts": len(all_raw_doc_ids),
        "document_ids_sources": all_raw_doc_ids,
        "gravite_globale": analyse.get("gravite_globale", "modere"),
        "bilan_executif": analyse.get("bilan_executif", ""),
        "cause": analyse.get("cause", ""),
        "preuve": analyse.get("preuve", ""),
        "points_chauds_geographiques": analyse.get("points_chauds_geographiques", []),
        "principaux_dysfonctionnements": analyse.get("principaux_dysfonctionnements", []),
        "preconisations_strategiques": analyse.get("preconisations_strategiques", []),
        "fournisseur_llm": llm_name,
        "cle_api_utilisee": _format_api_key_name(llm_name),
        "date_heure_traitement": date_heure_str,
        "date_analyse": now_utc.strftime("%Y-%m-%d"),
        "date_execution": now_utc.isoformat(),
        "meta_analyse": {
            "analysed_at": now_utc,
            "date_heure_traitement": date_heure_str,
            "run_id": run_id or f"run_l3_{now_utc.strftime('%Y-%m-%d_%Hh%M')}",
            "provider": llm_name,
            "cle_api_utilisee": _format_api_key_name(llm_name),
            "mois_cible": mois_val,
            "region": region_val,
            "source_territoire": territoire_val,
        },
    }


def build_stage4_document(
    domain_bilans: List[dict],
    analyse: dict,
    mois: str = "",
    region: str = "",
    territoire: str = "",
    run_id: Optional[str] = None,
    provider: Optional[str] = None,
) -> dict:
    now_utc = datetime.now(timezone.utc)
    territoire_val = territoire or settings.REGION
    region_val = region or settings.REGION
    mois_val = mois or settings.MOIS_CIBLE or "general"
    llm_name = (provider or settings.LLM_PROVIDER or "groq").lower()
    
    total_sources = sum(b.get("total_documents_sources_couverts", 0) for b in domain_bilans)
    titre_default = f"Rapport Stratégique Territorial - {territoire_val} ({mois_val})"
    date_heure_str = now_utc.strftime("%Y/%m/%d %H:%M")

    return {
        "type": "rapport_global_mensuel",
        "stage": 4,
        "titre": analyse.get("titre") or titre_default,
        "region": region_val,
        "source_territoire": territoire_val,
        "mois_cible": mois_val,
        "statut_general": analyse.get("statut_general", "calme"),
        "total_domaines_analyses": len(domain_bilans),
        "total_documents_sources_couverts": total_sources,
        "faits_marquants_du_mois": analyse.get("faits_marquants_du_mois", []),
        "synthese_transversale": analyse.get("synthese_transversale", ""),
        "cause": analyse.get("cause", ""),
        "preuve": analyse.get("preuve", ""),
        "tableau_de_bord_domaines": analyse.get("tableau_de_bord_domaines", []),
        "recommandations_prioritaires_decideurs": analyse.get("recommandations_prioritaires_decideurs", []),
        "domaines_details": [
            {
                "domaine": b.get("domaine"),
                "gravite": b.get("gravite_globale"),
                "points_chauds": b.get("points_chauds_geographiques", []),
            }
            for b in domain_bilans
        ],
        "fournisseur_llm": llm_name,
        "cle_api_utilisee": _format_api_key_name(llm_name),
        "date_heure_traitement": date_heure_str,
        "date_analyse": now_utc.strftime("%Y-%m-%d"),
        "date_execution": now_utc.isoformat(),
        "meta_analyse": {
            "analysed_at": now_utc,
            "date_heure_traitement": date_heure_str,
            "run_id": run_id or f"run_l4_{now_utc.strftime('%Y-%m-%d_%Hh%M')}",
            "provider": llm_name,
            "cle_api_utilisee": _format_api_key_name(llm_name),
            "mois_cible": mois_val,
            "region": region_val,
            "source_territoire": territoire_val,
        },
    }


def build_stage5_document(
    rapport_global: dict,
    analyse: dict,
    mois: str = "",
    region: str = "",
    territoire: str = "",
    run_id: Optional[str] = None,
    provider: Optional[str] = None,
) -> dict:
    now_utc = datetime.now(timezone.utc)
    territoire_val = territoire or rapport_global.get("source_territoire") or settings.REGION
    region_val = region or rapport_global.get("region") or settings.REGION
    mois_val = mois or settings.MOIS_CIBLE or rapport_global.get("mois_cible") or "general"
    total_sources = rapport_global.get("total_documents_sources_couverts", 0)
    llm_name = (provider or settings.LLM_PROVIDER or "groq").lower()
    date_heure_str = now_utc.strftime("%Y/%m/%d %H:%M")

    return {
        "type": "rapport_mensuel_finale",
        "stage": 5,
        "region": region_val,
        "source_territoire": territoire_val,
        "mois_cible": mois_val,
        "domaine_prioritaire_identifie": analyse.get("domaine_prioritaire_identifie", "general_territoire"),
        "probleme_majeur_persistant": analyse.get("probleme_majeur_persistant", ""),
        "cause": analyse.get("cause", ""),
        "preuve": analyse.get("preuve", ""),
        "statut_urgence": analyse.get("statut_urgence", "eleve"),
        "justification_priorite_absolue": analyse.get("justification_priorite_absolue", ""),
        "total_documents_sources_couverts": total_sources,
        "faits_saillants_et_recurrences": analyse.get("faits_saillants_et_recurrences", []),
        "impacts_et_risques_inaction": analyse.get("impacts_et_risques_inaction", ""),
        "plan_d_action_et_solutions_recommandees": analyse.get("plan_d_action_et_solutions_recommandees", []),
        "verdict_executif": analyse.get("verdict_executif", ""),
        "fournisseur_llm": llm_name,
        "cle_api_utilisee": _format_api_key_name(llm_name),
        "date_heure_traitement": date_heure_str,
        "date_analyse": now_utc.strftime("%Y-%m-%d"),
        "date_execution": now_utc.isoformat(),
        "meta_analyse": {
            "analysed_at": now_utc,
            "date_heure_traitement": date_heure_str,
            "run_id": run_id or f"run_l5_{now_utc.strftime('%Y-%m-%d_%Hh%M')}",
            "provider": llm_name,
            "cle_api_utilisee": _format_api_key_name(llm_name),
            "source_stage4_titre": rapport_global.get("titre"),
            "mois_cible": mois_val,
            "region": region_val,
            "source_territoire": territoire_val,
        },
    }
