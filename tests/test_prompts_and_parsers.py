"""
Tests unitaires pour les prompts (Stages 1 à 4) et les parseurs de réponses JSON.
"""
import unittest
from src.llm.prompts.prompt_stage1 import build_stage1_messages
from src.llm.prompts.prompt_stage2 import build_stage2_messages
from src.llm.prompts.prompt_stage3 import build_stage3_messages
from src.llm.prompts.prompt_stage4 import build_stage4_messages
from src.llm.response_parser import (
    parse_stage1_response,
    parse_stage2_response,
    parse_stage3_response,
    parse_stage4_response,
    ParsingError,
)
from src.schema.analyse_schema import (
    build_stage1_document,
    build_stage2_document,
    build_stage3_document,
    build_stage4_document,
)


class TestPromptsAndParsers(unittest.TestCase):
    def test_stage1_prompt_and_parser(self):
        docs = [
            {"document_id": "doc1", "title": "Urgences fermées", "municipality": "Bastia", "raw_text": "Texte brut...", "publication_date": "2026-08-10"},
            {"document_id": "doc2", "title": "Manque de médecins", "municipality": "Corte", "raw_text": "Texte brut...", "publication_date": "2026-08-11"},
        ]
        messages = build_stage1_messages(docs, domaine="sante_secours")
        self.assertEqual(len(messages), 2)
        self.assertIn("SANTE_SECOURS", messages[1]["content"])
        self.assertIn("Urgences fermées", messages[1]["content"])

        raw_llm_json = """```json
        {
          "gravite": "grave",
          "resume_court": "Forte tension sur les urgences en Corse.",
          "problematique_identifiee": "Désertification médicale aiguë.",
          "consequence_potentielle": "Retard de prise en charge.",
          "besoins_reels_detectes": "Médecins régulateurs.",
          "solutions_recommandees": "Aides à l'installation."
        }
        ```"""
        parsed = parse_stage1_response(raw_llm_json)
        self.assertEqual(parsed["gravite"], "grave")
        self.assertEqual(parsed["resume_court"], "Forte tension sur les urgences en Corse.")

        doc_l1 = build_stage1_document(docs, parsed, domaine="sante_secours", run_id="run_test", lot_numero=1)
        self.assertEqual(doc_l1["type"], "synthese_l1")
        self.assertEqual(doc_l1["stage"], 1)
        self.assertEqual(doc_l1["document_ids"], ["doc1", "doc2"])
        self.assertEqual(len(doc_l1["sources_associees"]), 2)

    def test_stage2_prompt_and_parser(self):
        l1_list = [
            {"resume_court": "Synthèse A", "problematique_identifiee": "Problème A", "gravite": "grave", "besoins_reels_detectes": "Besoin A"},
            {"resume_court": "Synthèse B", "problematique_identifiee": "Problème B", "gravite": "modere", "besoins_reels_detectes": "Besoin B"},
        ]
        messages = build_stage2_messages(l1_list, domaine="sante_secours")
        self.assertEqual(len(messages), 2)
        self.assertIn("SANTE_SECOURS", messages[1]["content"])
        self.assertIn("Synthèse A", messages[1]["content"])

        raw_llm_json = """{
          "gravite": "critique",
          "resume_consolide": "Consolidation départementale des urgences.",
          "tendance_majeure": "Saturation continue.",
          "impacts_territoriaux": "Isolement des zones rurales.",
          "actions_prioritaires": "Permanence des soins."
        }"""
        parsed = parse_stage2_response(raw_llm_json)
        self.assertEqual(parsed["gravite"], "grave")  # Normalisé depuis critique
        self.assertEqual(parsed["tendance_majeure"], "Saturation continue.")

        doc_l2 = build_stage2_document(
            [{"_id": "l1_id1", "document_ids": ["doc1", "doc2"]}, {"_id": "l1_id2", "document_ids": ["doc3"]}],
            parsed,
            domaine="sante_secours",
        )
        self.assertEqual(doc_l2["type"], "synthese_l2")
        self.assertEqual(doc_l2["stage"], 2)
        self.assertEqual(doc_l2["total_documents_sources_couverts"], 3)
        self.assertEqual(doc_l2["l1_synthese_ids"], ["l1_id1", "l1_id2"])

    def test_stage3_prompt_and_parser(self):
        l2_list = [
            {"resume_consolide": "Meso 1", "tendance_majeure": "Tendance 1", "gravite": "grave", "impacts_territoriaux": "Impact 1"},
        ]
        messages = build_stage3_messages(l2_list, domaine="environnement_climat_risques", mois="2026-08")
        self.assertEqual(len(messages), 2)
        self.assertIn("ENVIRONNEMENT_CLIMAT_RISQUES", messages[1]["content"])
        self.assertIn("2026-08", messages[1]["content"])

        raw_llm_json = """{
          "gravite_globale": "grave",
          "bilan_executif": "Mois d'août marqué par 12 feux majeurs.",
          "points_chauds_geographiques": ["Balagne", "Plaine orientale"],
          "principaux_dysfonctionnements": ["Stress hydrique", "Vents violents"],
          "preconisations_strategiques": ["Surveillance par drone", "Renforts Canadair"]
        }"""
        parsed = parse_stage3_response(raw_llm_json, fallback_domain="environnement_climat_risques")
        self.assertEqual(parsed["gravite_globale"], "grave")
        self.assertEqual(len(parsed["points_chauds_geographiques"]), 2)

        doc_l3 = build_stage3_document(
            [{"document_ids_sources": ["doc1", "doc2", "doc3"]}],
            parsed,
            domaine="environnement_climat_risques",
            mois="2026-08",
        )
        self.assertEqual(doc_l3["type"], "bilan_domaine")
        self.assertEqual(doc_l3["stage"], 3)
        self.assertEqual(doc_l3["total_documents_sources_couverts"], 3)

    def test_stage4_prompt_and_parser(self):
        domain_bilans = [
            {
                "domaine": "sante_secours",
                "gravite_globale": "grave",
                "bilan_executif": "Urgences sous tension.",
                "points_chauds_geographiques": ["Ajaccio"],
                "principaux_dysfonctionnements": ["Pénurie de soignants"],
                "preconisations_strategiques": ["Aide financière"],
                "total_documents_sources_couverts": 120,
            },
            {
                "domaine": "environnement_climat_risques",
                "gravite_globale": "grave",
                "bilan_executif": "Feux de maquis récurrents.",
                "points_chauds_geographiques": ["Balagne"],
                "principaux_dysfonctionnements": ["Sécheresse"],
                "preconisations_strategiques": ["Vigilance accrue"],
                "total_documents_sources_couverts": 150,
            },
        ]
        messages = build_stage4_messages(domain_bilans, mois="2026-08", region="Corse")
        self.assertEqual(len(messages), 2)
        self.assertIn("SANTE_SECOURS", messages[1]["content"])
        self.assertIn("ENVIRONNEMENT_CLIMAT_RISQUES", messages[1]["content"])

        raw_llm_json = """{
          "titre": "Rapport Stratégique Territorial - Corse (Août 2026)",
          "statut_general": "critique",
          "faits_marquants_du_mois": ["Pression touristique record", "Crise hydrique"],
          "synthese_transversale": "Croisement des flux touristiques et des ressources en tension.",
          "tableau_de_bord_domaines": [
            {"domaine": "sante_secours", "gravite": "grave", "resume_cle": "Urgences saturées."},
            {"domaine": "environnement_climat_risques", "gravite": "grave", "resume_cle": "Sécheresse et feux."}
          ],
          "recommandations_prioritaires_decideurs": ["Cellule de crise", "Plan eau"]
        }"""
        parsed = parse_stage4_response(raw_llm_json)
        self.assertEqual(parsed["statut_general"], "critique")
        self.assertEqual(len(parsed["faits_marquants_du_mois"]), 2)

        doc_l4 = build_stage4_document(domain_bilans, parsed, mois="2026-08", region="Corse")
        self.assertEqual(doc_l4["type"], "rapport_global_mensuel")
        self.assertEqual(doc_l4["stage"], 4)
        self.assertEqual(doc_l4["total_domaines_analyses"], 2)
        self.assertEqual(doc_l4["total_documents_sources_couverts"], 270)

    def test_parser_invalid_json_raises_parsing_error(self):
        with self.assertRaises(ParsingError):
            parse_stage1_response("Ce n'est pas du JSON valide du tout !")


if __name__ == "__main__":
    unittest.main()
