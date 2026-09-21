"""
Tests unitaires pour la normalisation multi-sources (Format Pivot)
et le routeur multi-LLM 4 providers avec failover sur erreur 429.
"""
import unittest
from unittest.mock import patch
from datetime import datetime, timezone
from src.db.normalizer import normalize_document, parse_datetime_flexible
from src.llm import client, groq_client, google_client, openrouter_client, huggingface_client


class TestMultiSourceNormalizer(unittest.TestCase):

    def test_normalize_collection_a_english_bson(self):
        doc_a = {
            "document_id": "ce7848ac5f66c9bcd118b1a3bad1affcceb2699c511c737765195bcd89cb7597",
            "url": "https://france3-regions.franceinfo.fr/corse/la-paillote.html",
            "source_name": "France 3 Corse ViaStella",
            "region": "Corse",
            "department": "Corse-du-Sud",
            "title": "Incendie de paillote à Ajaccio",
            "raw_text": "Le feu s'est déclaré au milieu de la nuit...",
            "publication_date": {"$date": "2026-08-12T09:37:34.000Z"},
        }
        normalized = normalize_document(doc_a, default_source_collection="Corse-du-Sud")
        
        self.assertEqual(normalized["document_id"], "ce7848ac5f66c9bcd118b1a3bad1affcceb2699c511c737765195bcd89cb7597")
        self.assertEqual(normalized["title"], "Incendie de paillote à Ajaccio")
        self.assertEqual(normalized["raw_text"], "Le feu s'est déclaré au milieu de la nuit...")
        self.assertEqual(normalized["territoire"], "Corse-du-Sud")
        self.assertEqual(normalized["mois_publication"], "2026-08")
        self.assertIsInstance(normalized["publication_date"], datetime)

    def test_normalize_collection_c_french_iso(self):
        doc_c = {
            "url_source": "https://france3-regions.franceinfo.fr/corse/vacances.html",
            "titre": "Vacances scolaires en Corse",
            "texte_complet": "Le calendrier des vacances 2026-2027 a été publié.",
            "date_publication": "2026-09-04T06:50:37+00:00",
            "departement_detecte": ["Région Corse"],
            "source_nom": "France 3 Corse",
        }
        normalized = normalize_document(doc_c, default_source_collection="Region-Corse")

        self.assertEqual(normalized["title"], "Vacances scolaires en Corse")
        self.assertEqual(normalized["raw_text"], "Le calendrier des vacances 2026-2027 a été publié.")
        self.assertEqual(normalized["url"], "https://france3-regions.franceinfo.fr/corse/vacances.html")
        self.assertEqual(normalized["source_name"], "France 3 Corse")
        self.assertEqual(normalized["territoire"], "Région Corse")
        self.assertEqual(normalized["mois_publication"], "2026-09")
        self.assertIsInstance(normalized["publication_date"], datetime)

    def test_empty_or_malformed_doc(self):
        normalized = normalize_document({}, default_source_collection="Corse")
        self.assertEqual(normalized["territoire"], "Corse")
        self.assertEqual(normalized["title"], "")


class TestMultiLLMFailover(unittest.TestCase):

    def test_quota_exceptions_defined(self):
        self.assertIn(groq_client.GroqQuotaError, client.QUOTA_EXCEPTIONS)
        self.assertIn(google_client.GoogleQuotaError, client.QUOTA_EXCEPTIONS)
        self.assertIn(openrouter_client.OpenRouterQuotaError, client.QUOTA_EXCEPTIONS)
        self.assertIn(huggingface_client.HuggingFaceQuotaError, client.QUOTA_EXCEPTIONS)

    @patch("config.settings.LLM_PROVIDER", "auto")
    @patch("config.settings.LLM_PROVIDER_ORDER", ["groq", "google", "openrouter", "huggingface"])
    def test_provider_pipeline_resolution(self):
        pipeline = client._get_provider_pipeline()
        self.assertEqual(len(pipeline), 4)
        names = [p[0] for p in pipeline]
        self.assertEqual(names, ["groq", "google", "openrouter", "huggingface"])


if __name__ == "__main__":
    unittest.main()
