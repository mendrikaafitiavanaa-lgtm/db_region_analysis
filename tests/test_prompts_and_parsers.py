"""
Tests unitaires pour les prompts (Stages 1 à 5) et les parseurs de réponses JSON.
"""
import unittest
from unittest.mock import MagicMock, patch

import requests

from config import settings
from src.llm import openrouter_client
from src.llm.prompts.prompt_stage1 import build_stage1_messages
from src.llm.prompts.prompt_stage2 import build_stage2_messages
from src.llm.prompts.prompt_stage3 import build_stage3_messages
from src.llm.prompts.prompt_stage4 import build_stage4_messages
from src.llm.prompts.prompt_stage5 import build_stage5_messages
from src.llm.response_parser import (
    parse_stage1_response,
    parse_stage2_response,
    parse_stage3_response,
    parse_stage4_response,
    parse_stage5_response,
    ParsingError,
)
from src.schema.analyse_schema import (
    build_stage1_document,
    build_stage2_document,
    build_stage3_document,
    build_stage4_document,
    build_stage5_document,
)


class TestPromptsAndParsers(unittest.TestCase):
    def test_openrouter_falls_back_to_supported_model_when_configured_model_is_missing(self):
        original_model = settings.OPENROUTER_MODEL
        settings.OPENROUTER_MODEL = "minimax/minimax-m3:free"

        not_found = MagicMock(status_code=404)
        not_found.text = '{"error":{"message":"model not found"}}'
        not_found.raise_for_status.side_effect = requests.HTTPError("404")

        ok_response = MagicMock(status_code=200)
        ok_response.json.return_value = {"choices": [{"message": {"content": '{"ok": true}'}}]}

        with patch("src.llm.openrouter_client._SESSION.post", side_effect=[not_found, ok_response]) as mock_post:
            result = openrouter_client.call_llm([{"role": "user", "content": "test"}])

        self.assertEqual(result, '{"ok": true}')
        self.assertEqual(mock_post.call_args_list[1].kwargs["json"]["model"], settings.OPENROUTER_FALLBACK_MODELS[0])
        settings.OPENROUTER_MODEL = original_model

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
          "cause": "Départs massifs à la retraite non compensés.",
          "preuve": "3 postes vacants sur 4 signalés à Corte.",
          "consequence_potentielle": "Retard de prise en charge.",
          "besoins_reels_detectes": "Médecins régulateurs.",
          "solutions_recommandees": "Aides à l'installation."
        }
        ```"""
        parsed = parse_stage1_response(raw_llm_json)
        self.assertEqual(parsed["gravite"], "grave")
        self.assertEqual(parsed["resume_court"], "Forte tension sur les urgences en Corse.")
        self.assertEqual(parsed["cause"], "Départs massifs à la retraite non compensés.")
        self.assertEqual(parsed["preuve"], "3 postes vacants sur 4 signalés à Corte.")

        doc_l1 = build_stage1_document(docs, parsed, domaine="sante_secours", run_id="run_test", lot_numero=1)
        self.assertEqual(doc_l1["type"], "synthese_l1")
        self.assertEqual(doc_l1["stage"], 1)
        self.assertEqual(doc_l1["document_ids"], ["doc1", "doc2"])
        self.assertEqual(doc_l1["cause"], "Départs massifs à la retraite non compensés.")
        self.assertEqual(doc_l1["preuve"], "3 postes vacants sur 4 signalés à Corte.")
        self.assertEqual(len(doc_l1["sources_associees"]), 2)

    def test_stage2_prompt_and_parser(self):
        l1_list = [
            {
                "resume_court": "Synthèse A",
                "problematique_identifiee": "Problème A",
                "cause": "Cause A",
                "preuve": "Preuve A",
                "gravite": "grave",
                "besoins_reels_detectes": "Besoin A",
            },
            {
                "resume_court": "Synthèse B",
                "problematique_identifiee": "Problème B",
                "cause": "Cause B",
                "preuve": "Preuve B",
                "gravite": "modere",
                "besoins_reels_detectes": "Besoin B",
            },
        ]
        messages = build_stage2_messages(l1_list, domaine="sante_secours")
        self.assertEqual(len(messages), 2)
        self.assertIn("SANTE_SECOURS", messages[1]["content"])
        self.assertIn("Synthèse A", messages[1]["content"])
        self.assertIn("Cause A", messages[1]["content"])
        self.assertIn("Preuve A", messages[1]["content"])

        raw_llm_json = """{
          "gravite": "critique",
          "resume_consolide": "Consolidation départementale des urgences.",
          "tendance_majeure": "Saturation continue.",
          "cause": "Déficit d'attractivité territoriale et manque d'internes.",
          "preuve": "Fermeture nocturne des urgences 15 jours consécutifs.",
          "impacts_territoriaux": "Isolement des zones rurales.",
          "actions_prioritaires": "Permanence des soins."
        }"""
        parsed = parse_stage2_response(raw_llm_json)
        self.assertEqual(parsed["gravite"], "grave")  # Normalisé depuis critique
        self.assertEqual(parsed["tendance_majeure"], "Saturation continue.")
        self.assertEqual(parsed["cause"], "Déficit d'attractivité territoriale et manque d'internes.")
        self.assertEqual(parsed["preuve"], "Fermeture nocturne des urgences 15 jours consécutifs.")

        doc_l2 = build_stage2_document(
            [{"_id": "l1_id1", "document_ids": ["doc1", "doc2"]}, {"_id": "l1_id2", "document_ids": ["doc3"]}],
            parsed,
            domaine="sante_secours",
        )
        self.assertEqual(doc_l2["type"], "synthese_l2")
        self.assertEqual(doc_l2["stage"], 2)
        self.assertEqual(doc_l2["cause"], "Déficit d'attractivité territoriale et manque d'internes.")
        self.assertEqual(doc_l2["preuve"], "Fermeture nocturne des urgences 15 jours consécutifs.")
        self.assertEqual(doc_l2["total_documents_sources_couverts"], 3)
        self.assertEqual(doc_l2["l1_synthese_ids"], ["l1_id1", "l1_id2"])

    def test_stage3_prompt_and_parser(self):
        l2_list = [
            {
                "resume_consolide": "Meso 1",
                "tendance_majeure": "Tendance 1",
                "cause": "Sécheresse prolongée",
                "preuve": "2000 hectares brûlés",
                "gravite": "grave",
                "impacts_territoriaux": "Impact 1",
            },
        ]
        messages = build_stage3_messages(l2_list, domaine="environnement_climat_risques", mois="2026-08")
        self.assertEqual(len(messages), 2)
        self.assertIn("ENVIRONNEMENT_CLIMAT_RISQUES", messages[1]["content"])
        self.assertIn("2026-08", messages[1]["content"])
        self.assertIn("Sécheresse prolongée", messages[1]["content"])
        self.assertIn("2000 hectares brûlés", messages[1]["content"])

        raw_llm_json = """{
          "gravite_globale": "grave",
          "bilan_executif": "Mois d'août marqué par 12 feux majeurs.",
          "cause": "Canicule historique couplée à des vents supérieurs à 90 km/h.",
          "preuve": "2000 hectares de forêt et maquis brûlés en Balagne.",
          "points_chauds_geographiques": ["Balagne", "Plaine orientale"],
          "principaux_dysfonctionnements": ["Stress hydrique", "Vents violents"],
          "preconisations_strategiques": ["Surveillance par drone", "Renforts Canadair"]
        }"""
        parsed = parse_stage3_response(raw_llm_json, fallback_domain="environnement_climat_risques")
        self.assertEqual(parsed["gravite_globale"], "grave")
        self.assertEqual(parsed["cause"], "Canicule historique couplée à des vents supérieurs à 90 km/h.")
        self.assertEqual(parsed["preuve"], "2000 hectares de forêt et maquis brûlés en Balagne.")
        self.assertEqual(len(parsed["points_chauds_geographiques"]), 2)

        doc_l3 = build_stage3_document(
            [{"document_ids_sources": ["doc1", "doc2", "doc3"]}],
            parsed,
            domaine="environnement_climat_risques",
            mois="2026-08",
        )
        self.assertEqual(doc_l3["type"], "bilan_domaine")
        self.assertEqual(doc_l3["stage"], 3)
        self.assertEqual(doc_l3["cause"], "Canicule historique couplée à des vents supérieurs à 90 km/h.")
        self.assertEqual(doc_l3["preuve"], "2000 hectares de forêt et maquis brûlés en Balagne.")
        self.assertEqual(doc_l3["total_documents_sources_couverts"], 3)

    def test_stage4_prompt_and_parser(self):
        domain_bilans = [
            {
                "domaine": "sante_secours",
                "gravite_globale": "grave",
                "bilan_executif": "Urgences sous tension.",
                "cause": "Manque d'effectifs médicaux",
                "preuve": "40% de postes vacants",
                "points_chauds_geographiques": ["Ajaccio"],
                "principaux_dysfonctionnements": ["Pénurie de soignants"],
                "preconisations_strategiques": ["Aide financière"],
                "total_documents_sources_couverts": 120,
            },
            {
                "domaine": "environnement_climat_risques",
                "gravite_globale": "grave",
                "bilan_executif": "Feux de maquis récurrents.",
                "cause": "Stress hydrique et fortes chaleurs",
                "preuve": "12 départs de feu en 48h",
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
        self.assertIn("Manque d'effectifs médicaux", messages[1]["content"])

        raw_llm_json = """{
          "titre": "Rapport Stratégique Territorial - Corse (Août 2026)",
          "statut_general": "critique",
          "cause": "Conjonction d'un afflux touristique massif et d'un épisode caniculaire intense.",
          "preuve": "Hausse de 35% des interventions de secours et 2000 ha sinistrés.",
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
        self.assertEqual(parsed["cause"], "Conjonction d'un afflux touristique massif et d'un épisode caniculaire intense.")
        self.assertEqual(parsed["preuve"], "Hausse de 35% des interventions de secours et 2000 ha sinistrés.")
        self.assertEqual(len(parsed["faits_marquants_du_mois"]), 2)

        doc_l4 = build_stage4_document(domain_bilans, parsed, mois="2026-08", region="Corse")
        self.assertEqual(doc_l4["type"], "rapport_global_mensuel")
        self.assertEqual(doc_l4["stage"], 4)
        self.assertEqual(doc_l4["cause"], "Conjonction d'un afflux touristique massif et d'un épisode caniculaire intense.")
        self.assertEqual(doc_l4["preuve"], "Hausse de 35% des interventions de secours et 2000 ha sinistrés.")
        self.assertEqual(doc_l4["total_domaines_analyses"], 2)
        self.assertEqual(doc_l4["total_documents_sources_couverts"], 270)

    def test_stage5_prompt_and_parser(self):
        rapport_global = {
            "titre": "Rapport Global Corse",
            "statut_general": "critique",
            "cause": "Tension multifactorielle",
            "preuve": "Indicateurs au rouge",
            "total_documents_sources_couverts": 270,
            "faits_marquants_du_mois": ["Crise des feux"],
            "synthese_transversale": "Forte vulnérabilité.",
        }
        domain_bilans = [
            {
                "domaine": "environnement_climat_risques",
                "gravite_globale": "grave",
                "bilan_executif": "Incendies dévastateurs.",
                "cause": "Sécheresse prolongée",
                "preuve": "2000 ha détruits",
                "principaux_dysfonctionnements": ["Manque de Canadairs"],
            }
        ]
        messages = build_stage5_messages(rapport_global, domain_bilans, mois="2026-08", region="Corse")
        self.assertEqual(len(messages), 2)
        self.assertIn("Rapport Global Corse", messages[1]["content"])

        raw_llm_json = """{
          "domaine_prioritaire_identifie": "environnement_climat_risques",
          "probleme_majeur_persistant": "Crise des incendies et vulnérabilité forestière",
          "cause": "Changement climatique aggravant le déficit pluviométrique estival.",
          "preuve": "2000 hectares détruits d'après les relevés satellitaires et du SDIS.",
          "statut_urgence": "critique",
          "justification_priorite_absolue": "Menace directe sur les habitations et la biodiversité.",
          "faits_saillants_et_recurrences": ["12 départs de feu simultanés"],
          "impacts_et_risques_inaction": "Perte irréversible d'écosystèmes.",
          "plan_d_action_et_solutions_recommandees": [
            {"priorite": "Urgence immédiate (0-30 jours)", "action": "Renforts de patrouilles", "acteur_responsable": "Préfecture"}
          ],
          "verdict_executif": "Action immédiate requise pour préserver le massif corse."
        }"""
        parsed = parse_stage5_response(raw_llm_json)
        self.assertEqual(parsed["domaine_prioritaire_identifie"], "environnement_climat_risques")
        self.assertEqual(parsed["cause"], "Changement climatique aggravant le déficit pluviométrique estival.")
        self.assertEqual(parsed["preuve"], "2000 hectares détruits d'après les relevés satellitaires et du SDIS.")

        doc_l5 = build_stage5_document(rapport_global, parsed, mois="2026-08", region="Corse")
        self.assertEqual(doc_l5["type"], "rapport_mensuel_finale")
        self.assertEqual(doc_l5["stage"], 5)
        self.assertEqual(doc_l5["cause"], "Changement climatique aggravant le déficit pluviométrique estival.")
        self.assertEqual(doc_l5["preuve"], "2000 hectares détruits d'après les relevés satellitaires et du SDIS.")
        self.assertEqual(doc_l5["total_documents_sources_couverts"], 270)

    def test_parser_invalid_json_raises_parsing_error(self):
        with self.assertRaises(ParsingError):
            parse_stage1_response("Ce n'est pas du JSON valide du tout !")

    def test_prompt_loader_stages_1_to_5(self):
        from src.llm.prompts.prompt_loader import (
            get_system_prompt,
            get_json_shape,
            load_system_prompts,
            load_json_shapes,
        )

        sys_prompts = load_system_prompts()
        json_shapes = load_json_shapes()

        for stage in range(1, 6):
            p = get_system_prompt(stage)
            s = get_json_shape(stage)
            self.assertTrue(len(p) > 20, f"Le prompt du Stage {stage} ne doit pas être vide")
            self.assertTrue(len(s) > 20, f"Le gabarit JSON du Stage {stage} ne doit pas être vide")
            self.assertIn("Corse", p, f"Le prompt du Stage {stage} doit faire référence à la Corse")
            self.assertIn("cause", s, f"Le gabarit JSON du Stage {stage} doit inclure le champ cause")
            self.assertIn("preuve", s, f"Le gabarit JSON du Stage {stage} doit inclure le champ preuve")


if __name__ == "__main__":
    unittest.main()


