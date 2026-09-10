"""
Tests d'intégration mockés pour les étages 1, 2, 3, 4, 5 et l'orchestrateur.
"""
import unittest
from unittest.mock import patch, MagicMock
from src.pipeline.orchestrator import run_pipeline


class TestPipelineOrchestrator(unittest.TestCase):
    @patch("src.db.target_writer.ensure_all_indexes")
    @patch("src.db.source_reader.get_already_processed_ids")
    @patch("src.db.source_reader.read_all_pending_sources")
    @patch("src.db.source_reader.read_stage_documents")
    @patch("src.db.target_writer.save_synthese_l1")
    @patch("src.db.target_writer.save_synthese_l2")
    @patch("src.db.target_writer.save_bilan_domaine")
    @patch("src.db.target_writer.save_rapport_global")
    @patch("src.db.target_writer.save_rapport_mensuel_finale")
    @patch("src.llm.client.call_llm")
    def test_run_full_pipeline_mocked(
        self,
        mock_call_llm,
        mock_save_finale,
        mock_save_global,
        mock_save_bilan,
        mock_save_l2,
        mock_save_l1,
        mock_read_stage,
        mock_read_sources,
        mock_get_processed,
        mock_ensure_indexes,
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
                {"_id": "l1_1", "domaine_principal": "sante_secours", "document_ids": [f"sante_{i}" for i in range(8)], "resume_court": "Synthèse santé", "problematique_identifiee": "Désert médical"},
                {"_id": "l1_2", "domaine_principal": "transport_mobilite", "document_ids": [f"trans_{i}" for i in range(8)], "resume_court": "Synthèse transport", "problematique_identifiee": "Bouchons"},
            ],
            # Lecture L2 pour Stage 3
            [
                {"domaine_principal": "sante_secours", "document_ids_sources": [f"sante_{i}" for i in range(8)], "resume_consolide": "Meso santé", "gravite": "grave"},
                {"domaine_principal": "transport_mobilite", "document_ids_sources": [f"trans_{i}" for i in range(8)], "resume_consolide": "Meso transport", "gravite": "modere"},
            ],
            # Lecture Bilans pour Stage 4
            [
                {"domaine": "sante_secours", "gravite_globale": "grave", "bilan_executif": "Santé en tension", "total_documents_sources_couverts": 8},
                {"domaine": "transport_mobilite", "gravite_globale": "modere", "bilan_executif": "Transports fluides", "total_documents_sources_couverts": 8},
            ],
            # Lecture Global (Stage 4) pour Stage 5
            [
                {"titre": "Rapport Stratégique Territorial", "statut_general": "critique", "total_documents_sources_couverts": 16, "faits_marquants_du_mois": ["Pénurie médicale"], "synthese_transversale": "Tension"},
            ],
            # Lecture Bilans (Stage 3) pour Stage 5
            [
                {"domaine": "sante_secours", "gravite_globale": "grave", "bilan_executif": "Santé en tension", "principaux_dysfonctionnements": ["Déserts médicaux"]},
                {"domaine": "transport_mobilite", "gravite_globale": "modere", "bilan_executif": "Transports fluides", "principaux_dysfonctionnements": ["Voirie"]},
            ],
        ]

        # Réponses mockées du LLM pour chaque appel
        mock_call_llm.side_effect = [
            # Stage 1 (Lot Santé)
            '{"gravite": "grave", "resume_court": "Micro santé", "problematique_identifiee": "Problème", "consequence_potentielle": "Risque", "besoins_reels_detectes": "Soins", "solutions_recommandees": "Aides"}',
            # Stage 1 (Lot Transport)
            '{"gravite": "modere", "resume_court": "Micro transport", "problematique_identifiee": "Problème", "consequence_potentielle": "Risque", "besoins_reels_detectes": "Voirie", "solutions_recommandees": "Travaux"}',
            # Stage 2 (Lot Santé)
            '{"gravite": "grave", "resume_consolide": "Meso santé", "tendance_majeure": "Tendance", "impacts_territoriaux": "Impacts", "actions_prioritaires": "Actions"}',
            # Stage 2 (Lot Transport)
            '{"gravite": "modere", "resume_consolide": "Meso transport", "tendance_majeure": "Tendance", "impacts_territoriaux": "Impacts", "actions_prioritaires": "Actions"}',
            # Stage 3 (Bilan Santé)
            '{"gravite_globale": "grave", "bilan_executif": "Bilan santé", "points_chauds_geographiques": ["Ajaccio"], "principaux_dysfonctionnements": ["Pénurie"], "preconisations_strategiques": ["Aide"]}',
            # Stage 3 (Bilan Transport)
            '{"gravite_globale": "modere", "bilan_executif": "Bilan transport", "points_chauds_geographiques": ["Bastia"], "principaux_dysfonctionnements": ["Voirie"], "preconisations_strategiques": ["Plan"]}',
            # Stage 4 (Rapport Global)
            '{"titre": "Rapport Stratégique Territorial", "statut_general": "critique", "faits_marquants_du_mois": ["Fait 1"], "synthese_transversale": "Transversale", "tableau_de_bord_domaines": [], "recommandations_prioritaires_decideurs": ["Action 1"]}',
            # Stage 5 (Synthèse Finale N°1)
            '{"domaine_prioritaire_identifie": "sante_secours", "probleme_majeur_persistant": "Crise aiguë des déserts médicaux", "statut_urgence": "critique", "justification_priorite_absolue": "Urgence sanitaire vitale", "faits_saillants_et_recurrences": ["Saturation urgences"], "impacts_et_risques_inaction": "Rupture de soins", "plan_d_action_et_solutions_recommandees": [{"priorite": "Urgence", "action": "Plan renfort", "acteur_responsable": "ARS"}], "verdict_executif": "La santé requiert une mobilisation immédiate."}',
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


if __name__ == "__main__":
    unittest.main()

