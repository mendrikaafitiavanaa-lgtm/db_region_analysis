"""
Tests d'intégration mockés pour les étages 1, 2, 3, 4, 5 et l'orchestrateur.
"""
import unittest
from unittest.mock import patch, MagicMock
from src.pipeline.orchestrator import run_pipeline


class TestPipelineOrchestrator(unittest.TestCase):
    @patch("time.sleep")
    @patch("src.db.target_writer.ensure_all_indexes")
    @patch("src.db.source_reader.get_already_processed_ids")
    @patch("src.db.source_reader.read_all_pending_sources")
    @patch("src.db.source_reader.read_stage_documents")
    @patch("src.db.target_writer.save_synthese_l1")
    @patch("src.db.target_writer.save_synthese_l2")
    @patch("src.db.target_writer.save_bilan_domaine")
    @patch("src.db.target_writer.save_rapport_global")
    @patch("src.db.target_writer.save_rapport_mensuel_finale")
    @patch("src.pipeline.stage1_micro.call_llm_with_meta")
    @patch("src.pipeline.stage2_meso.call_llm_with_meta")
    @patch("src.pipeline.stage3_domaines.call_llm_with_meta")
    @patch("src.pipeline.stage4_global.call_llm_with_meta")
    @patch("src.pipeline.stage5_finale.call_llm_with_meta")
    def test_run_full_pipeline_mocked(
        self,
        mock_llm_s5,
        mock_llm_s4,
        mock_llm_s3,
        mock_llm_s2,
        mock_llm_s1,
        mock_save_finale,
        mock_save_global,
        mock_save_bilan,
        mock_save_l2,
        mock_save_l1,
        mock_read_stage,
        mock_read_sources,
        mock_get_processed,
        mock_ensure_indexes,
        mock_sleep,
    ):
        # Configuration des mocks
        mock_get_processed.return_value = set()
        
        # 16 documents sources bruts
        mock_read_sources.return_value = [
            {"document_id": f"sante_{i}", "title": f"Médecin {i}", "raw_text": "Désert médical et urgences.", "municipality": "Ajaccio"}
            for i in range(8)
        ] + [
            {"document_id": f"trans_{i}", "title": f"Route {i}", "raw_text": "Bouchons et routes.", "municipality": "Bastia"}
            for i in range(8)
        ]

        # Stage documents returns
        mock_read_stage.side_effect = [
            # Lecture L1 pour Stage 2
            [
                {
                    "_id": "l1_1",
                    "domaine_principal": "sante_secours",
                    "document_ids": [f"sante_{i}" for i in range(8)],
                    "resume_court": "Synthèse santé",
                    "problematique_identifiee": "Désert médical",
                    "cause": "Manque de médecins",
                    "preuve": "3 cabinets fermés",
                },
                {
                    "_id": "l1_2",
                    "domaine_principal": "transport_mobilite",
                    "document_ids": [f"trans_{i}" for i in range(8)],
                    "resume_court": "Synthèse transport",
                    "problematique_identifiee": "Bouchons",
                    "cause": "Travaux non coordonnés",
                    "preuve": "2h d'attente sur RN193",
                },
            ],
            # Lecture L2 pour Stage 3
            [
                {
                    "domaine_principal": "sante_secours",
                    "document_ids_sources": [f"sante_{i}" for i in range(8)],
                    "resume_consolide": "Meso santé",
                    "gravite": "grave",
                    "cause": "Déficit d'attractivité territoriale",
                    "preuve": "Fermeture nocturne des urgences",
                },
                {
                    "domaine_principal": "transport_mobilite",
                    "document_ids_sources": [f"trans_{i}" for i in range(8)],
                    "resume_consolide": "Meso transport",
                    "gravite": "modere",
                    "cause": "Saturation du réseau routier",
                    "preuve": "Ralentissements quotidiens",
                },
            ],
            # Lecture Bilans pour Stage 4
            [
                {
                    "domaine": "sante_secours",
                    "gravite_globale": "grave",
                    "bilan_executif": "Santé en tension",
                    "cause": "Pénurie médicale globale",
                    "preuve": "40% postes vacants",
                    "total_documents_sources_couverts": 8,
                },
                {
                    "domaine": "transport_mobilite",
                    "gravite_globale": "modere",
                    "bilan_executif": "Transports sous tension",
                    "cause": "Axes côtiers saturés",
                    "preuve": "Bouchons records",
                    "total_documents_sources_couverts": 8,
                },
            ],
            # Lecture Global (Stage 4) pour Stage 5
            [
                {
                    "titre": "Rapport Stratégique Territorial",
                    "statut_general": "critique",
                    "cause": "Tension infrastructurelle et médicale",
                    "preuve": "Indicateurs au rouge sur toute l'île",
                    "total_documents_sources_couverts": 16,
                    "faits_marquants_du_mois": ["Pénurie médicale"],
                    "synthese_transversale": "Tension",
                },
            ],
            # Lecture Bilans (Stage 3) pour Stage 5
            [
                {
                    "domaine": "sante_secours",
                    "gravite_globale": "grave",
                    "bilan_executif": "Santé en tension",
                    "cause": "Pénurie médicale",
                    "preuve": "40% postes vacants",
                    "principaux_dysfonctionnements": ["Déserts médicaux"],
                },
                {
                    "domaine": "transport_mobilite",
                    "gravite_globale": "modere",
                    "bilan_executif": "Transports fluides",
                    "cause": "Axes saturés",
                    "preuve": "Embouteillages",
                    "principaux_dysfonctionnements": ["Voirie"],
                },
            ],
        ]

        # Réponses mockées du LLM avec métadonnées (texte, nom_provider)
        mock_llm_s1.side_effect = [
            ('{"gravite": "grave", "resume_court": "Micro santé", "problematique_identifiee": "Problème", "cause": "Manque praticiens", "preuve": "3 postes non pourvus", "consequence_potentielle": "Risque", "besoins_reels_detectes": "Soins", "solutions_recommandees": "Aides"}', "groq"),
            ('{"gravite": "modere", "resume_court": "Micro transport", "problematique_identifiee": "Problème", "cause": "Travaux", "preuve": "Bouchons 10km", "consequence_potentielle": "Risque", "besoins_reels_detectes": "Voirie", "solutions_recommandees": "Travaux"}', "groq"),
        ]
        mock_llm_s2.side_effect = [
            ('{"gravite": "grave", "resume_consolide": "Meso santé", "tendance_majeure": "Tendance", "cause": "Déficit général", "preuve": "Saturation continue", "impacts_territoriaux": "Impacts", "actions_prioritaires": "Actions"}', "google"),
            ('{"gravite": "modere", "resume_consolide": "Meso transport", "tendance_majeure": "Tendance", "cause": "Goulot d\'étranglement", "preuve": "Pics horaires", "impacts_territoriaux": "Impacts", "actions_prioritaires": "Actions"}', "google"),
        ]
        mock_llm_s3.side_effect = [
            ('{"gravite_globale": "grave", "bilan_executif": "Bilan santé", "cause": "Désertification rurale", "preuve": "Urgences fermées 15j", "points_chauds_geographiques": ["Ajaccio"], "principaux_dysfonctionnements": ["Pénurie"], "preconisations_strategiques": ["Aide"]}', "openrouter"),
            ('{"gravite_globale": "modere", "bilan_executif": "Bilan transport", "cause": "Infrastructures vétustes", "preuve": "Temps de trajet doublé", "points_chauds_geographiques": ["Bastia"], "principaux_dysfonctionnements": ["Voirie"], "preconisations_strategiques": ["Plan"]}', "openrouter"),
        ]
        mock_llm_s4.side_effect = [
            ('{"titre": "Rapport Stratégique Territorial", "statut_general": "critique", "cause": "Afflux estival et sous-capacité", "preuve": "Hausse 30% des interventions", "faits_marquants_du_mois": ["Fait 1"], "synthese_transversale": "Transversale", "tableau_de_bord_domaines": [], "recommandations_prioritaires_decideurs": ["Action 1"]}', "huggingface"),
        ]
        mock_llm_s5.side_effect = [
            ('{"domaine_prioritaire_identifie": "sante_secours", "probleme_majeur_persistant": "Crise aiguë des déserts médicaux", "cause": "Non-remplacement départs retraite", "preuve": "3 hôpitaux en grève et 40% postes vacants", "statut_urgence": "critique", "justification_priorite_absolue": "Urgence sanitaire vitale", "faits_saillants_et_recurrences": ["Saturation urgences"], "impacts_et_risques_inaction": "Rupture de soins", "plan_d_action_et_solutions_recommandees": [{"priorite": "Urgence", "action": "Plan renfort", "acteur_responsable": "ARS"}], "verdict_executif": "La santé requiert une mobilisation immédiate."}', "groq"),
        ]

        # Exécuter l'ensemble du pipeline
        result = run_pipeline(stage="all", run_id="test_run_unit")

        self.assertEqual(result["statut"], "succes")
        self.assertIn("stage_1", result["stages"])
        self.assertIn("stage_2", result["stages"])
        self.assertIn("stage_3", result["stages"])
        self.assertIn("stage_4", result["stages"])
        self.assertIn("stage_5", result["stages"])

        self.assertEqual(mock_save_l1.call_count, 2)
        self.assertEqual(mock_save_l2.call_count, 2)
        self.assertEqual(mock_save_bilan.call_count, 2)
        self.assertEqual(mock_save_global.call_count, 1)
        self.assertEqual(mock_save_finale.call_count, 1)

        # Vérifier que les documents sauvegardés contiennent les champs de traçabilité demandés
        saved_l1 = mock_save_l1.call_args_list[0][0][0]
        self.assertEqual(saved_l1["fournisseur_llm"], "groq")
        self.assertIn("GROQ", saved_l1["cle_api_utilisee"])
        self.assertIn("date_heure_traitement", saved_l1)
        self.assertEqual(saved_l1["cause"], "Manque praticiens")

        saved_l2 = mock_save_l2.call_args_list[0][0][0]
        self.assertEqual(saved_l2["fournisseur_llm"], "google")
        self.assertIn("GOOGLE", saved_l2["cle_api_utilisee"])
        self.assertIn("date_heure_traitement", saved_l2)

        saved_l3 = mock_save_bilan.call_args_list[0][0][0]
        self.assertEqual(saved_l3["fournisseur_llm"], "openrouter")
        self.assertIn("OPENROUTER", saved_l3["cle_api_utilisee"])
        self.assertIn("date_heure_traitement", saved_l3)

        saved_l4 = mock_save_global.call_args_list[0][0][0]
        self.assertEqual(saved_l4["fournisseur_llm"], "huggingface")
        self.assertIn("HUGGINGFACE", saved_l4["cle_api_utilisee"])
        self.assertIn("date_heure_traitement", saved_l4)

        saved_l5 = mock_save_finale.call_args_list[0][0][0]
        self.assertEqual(saved_l5["fournisseur_llm"], "groq")
        self.assertIn("date_heure_traitement", saved_l5)
        self.assertEqual(saved_l5["cause"], "Non-remplacement départs retraite")
        self.assertEqual(saved_l5["preuve"], "3 hôpitaux en grève et 40% postes vacants")


if __name__ == "__main__":
    unittest.main()
