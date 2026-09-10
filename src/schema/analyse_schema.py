"""
Générateurs de documents normalisés pour chaque étape de la pyramide d'analyse.
Conserve la traçabilité des IDs sources à tous les niveaux.
"""
from datetime import datetime, timezone
from typing import List, Optional, Dict
from config import settings


def build_stage1_document(
    source_docs: List[dict],
    analyse: dict,
    domaine: str,
    run_id: Optional[str] = None,
    lot_numero: int = 1,
) -> dict:
    now_utc = datetime.now(timezone.utc)
    document_ids = [str(doc.get("document_id")) for doc in source_docs if doc.get("document_id")]

    sources_associees = [
        {
            "document_id": doc.get("document_id"),
            "title": doc.get("title"),
            "url": doc.get("url"),
            "municipality": doc.get("municipality"),
            "department": doc.get("department"),
            "region": doc.get("region"),
            "source_name": doc.get("source_name"),
            "publication_date": doc.get("publication_date"),
        }
        for doc in source_docs
    ]

    return {
        "type": "synthese_l1",
        "stage": 1,
        "domaine_principal": domaine,
        "lot_taille": len(source_docs),
        "document_ids": document_ids,
        "sources_associees": sources_associees,
        "gravite": analyse.get("gravite", "modere"),
        "resume_court": analyse.get("resume_court", ""),
        "problematique_identifiee": analyse.get("problematique_identifiee", ""),
        "consequence_potentielle": analyse.get("consequence_potentielle", ""),
        "besoins_reels_detectes": analyse.get("besoins_reels_detectes", ""),
        "solutions_recommandees": analyse.get("solutions_recommandees", ""),
        "date_analyse": now_utc.strftime("%Y-%m-%d"),
        "meta_analyse": {
            "analysed_at": now_utc,
            "run_id": run_id or f"run_l1_{now_utc.strftime('%Y-%m-%d_%Hh%M')}",
            "lot_numero": lot_numero,
            "provider": settings.LLM_PROVIDER,
            "mois_cible": settings.MOIS_CIBLE or None,
        },
    }


def build_stage2_document(
    l1_docs: List[dict],
    analyse: dict,
    domaine: str,
    run_id: Optional[str] = None,
    lot_numero: int = 1,
) -> dict:
    now_utc = datetime.now(timezone.utc)
    
    # Agrégation de tous les document_ids bruts sous-jacents
    all_raw_doc_ids = []
    l1_synthese_ids = []
    for l1 in l1_docs:
        if l1.get("_id"):
            l1_synthese_ids.append(str(l1.get("_id")))
        all_raw_doc_ids.extend(l1.get("document_ids", []))
    
    # Déduplication
    all_raw_doc_ids = list(dict.fromkeys(all_raw_doc_ids))

    return {
        "type": "synthese_l2",
        "stage": 2,
        "domaine_principal": domaine,
        "lot_taille_l1": len(l1_docs),
        "total_documents_sources_couverts": len(all_raw_doc_ids),
        "l1_synthese_ids": l1_synthese_ids,
        "document_ids_sources": all_raw_doc_ids,
        "gravite": analyse.get("gravite", "modere"),
        "resume_consolide": analyse.get("resume_consolide", ""),
        "tendance_majeure": analyse.get("tendance_majeure", ""),
        "impacts_territoriaux": analyse.get("impacts_territoriaux", ""),
        "actions_prioritaires": analyse.get("actions_prioritaires", ""),
        "date_analyse": now_utc.strftime("%Y-%m-%d"),
        "meta_analyse": {
            "analysed_at": now_utc,
            "run_id": run_id or f"run_l2_{now_utc.strftime('%Y-%m-%d_%Hh%M')}",
            "lot_numero": lot_numero,
            "provider": settings.LLM_PROVIDER,
            "mois_cible": settings.MOIS_CIBLE or None,
        },
    }


def build_stage3_document(
    l2_docs: List[dict],
    analyse: dict,
    domaine: str,
    mois: str = "",
    run_id: Optional[str] = None,
) -> dict:
    now_utc = datetime.now(timezone.utc)
    
    all_raw_doc_ids = []
    for l2 in l2_docs:
        all_raw_doc_ids.extend(l2.get("document_ids_sources", []))
    all_raw_doc_ids = list(dict.fromkeys(all_raw_doc_ids))

    return {
        "type": "bilan_domaine",
        "stage": 3,
        "domaine": domaine,
        "mois_cible": mois or settings.MOIS_CIBLE or "general",
        "total_syntheses_l2_utilisees": len(l2_docs),
        "total_documents_sources_couverts": len(all_raw_doc_ids),
        "document_ids_sources": all_raw_doc_ids,
        "gravite_globale": analyse.get("gravite_globale", "modere"),
        "bilan_executif": analyse.get("bilan_executif", ""),
        "points_chauds_geographiques": analyse.get("points_chauds_geographiques", []),
        "principaux_dysfonctionnements": analyse.get("principaux_dysfonctionnements", []),
        "preconisations_strategiques": analyse.get("preconisations_strategiques", []),
        "date_analyse": now_utc.strftime("%Y-%m-%d"),
        "meta_analyse": {
            "analysed_at": now_utc,
            "run_id": run_id or f"run_l3_{now_utc.strftime('%Y-%m-%d_%Hh%M')}",
            "provider": settings.LLM_PROVIDER,
        },
    }


def build_stage4_document(
    domain_bilans: List[dict],
    analyse: dict,
    mois: str = "",
    region: str = "Corse",
    run_id: Optional[str] = None,
) -> dict:
    now_utc = datetime.now(timezone.utc)
    
    total_sources = sum(b.get("total_documents_sources_couverts", 0) for b in domain_bilans)

    return {
        "type": "rapport_global_mensuel",
        "stage": 4,
        "titre": analyse.get("titre", f"Rapport Stratégique Territorial - {region}"),
        "region": region,
        "mois_cible": mois or settings.MOIS_CIBLE or "general",
        "statut_general": analyse.get("statut_general", "calme"),
        "total_domaines_analyses": len(domain_bilans),
        "total_documents_sources_couverts": total_sources,
        "faits_marquants_du_mois": analyse.get("faits_marquants_du_mois", []),
        "synthese_transversale": analyse.get("synthese_transversale", ""),
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
        "date_analyse": now_utc.strftime("%Y-%m-%d"),
        "meta_analyse": {
            "analysed_at": now_utc,
            "run_id": run_id or f"run_l4_{now_utc.strftime('%Y-%m-%d_%Hh%M')}",
            "provider": settings.LLM_PROVIDER,
        },
    }


def build_stage5_document(
    rapport_global: dict,
    analyse: dict,
    mois: str = "",
    region: str = "Corse",
    run_id: Optional[str] = None,
) -> dict:
    now_utc = datetime.now(timezone.utc)
    total_sources = rapport_global.get("total_documents_sources_couverts", 0)

    return {
        "type": "rapport_mensuel_finale",
        "stage": 5,
        "region": region,
        "mois_cible": mois or settings.MOIS_CIBLE or "general",
        "domaine_prioritaire_identifie": analyse.get("domaine_prioritaire_identifie", "general_territoire"),
        "probleme_majeur_persistant": analyse.get("probleme_majeur_persistant", ""),
        "statut_urgence": analyse.get("statut_urgence", "eleve"),
        "justification_priorite_absolue": analyse.get("justification_priorite_absolue", ""),
        "total_documents_sources_couverts": total_sources,
        "faits_saillants_et_recurrences": analyse.get("faits_saillants_et_recurrences", []),
        "impacts_et_risques_inaction": analyse.get("impacts_et_risques_inaction", ""),
        "plan_d_action_et_solutions_recommandees": analyse.get("plan_d_action_et_solutions_recommandees", []),
        "verdict_executif": analyse.get("verdict_executif", ""),
        "date_analyse": now_utc.strftime("%Y-%m-%d"),
        "meta_analyse": {
            "analysed_at": now_utc,
            "run_id": run_id or f"run_l5_{now_utc.strftime('%Y-%m-%d_%Hh%M')}",
            "provider": settings.LLM_PROVIDER,
            "source_stage4_titre": rapport_global.get("titre"),
        },
    }

