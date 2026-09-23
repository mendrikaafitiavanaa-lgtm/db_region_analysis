import unittest
from unittest.mock import patch, MagicMock
import tempfile
import os
import shutil

from config import settings
from src.llm import cooldown_manager
from src.llm import client
from src.llm.google_client import GoogleQuotaError
from src.llm.openrouter_client import OpenRouterQuotaError


class TestCooldownAndFailover(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.old_checkpoint_dir = settings.CHECKPOINT_DIR
        settings.CHECKPOINT_DIR = self.test_dir
        cooldown_manager.COOLDOWN_FILE = os.path.join(self.test_dir, "provider_cooldown.json")
        cooldown_manager.reset_cooldown()

    def tearDown(self):
        settings.CHECKPOINT_DIR = self.old_checkpoint_dir
        cooldown_manager.COOLDOWN_FILE = os.path.join(self.old_checkpoint_dir, "provider_cooldown.json")
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_cooldown_marking_and_availability(self):
        settings.LLM_COOLDOWN_HOURS = 24.0
        self.assertTrue(cooldown_manager.is_provider_available("google"))
        self.assertTrue(cooldown_manager.is_provider_available("openrouter"))

        # Mark google on cooldown
        cooldown_manager.mark_cooldown("google", "HTTP 429: Quota exceeded", duration_hours=24.0)

        self.assertFalse(cooldown_manager.is_provider_available("google"))
        self.assertTrue(cooldown_manager.is_provider_available("openrouter"))
        self.assertGreater(cooldown_manager.get_remaining_cooldown_seconds("google"), 0)

        # Reset google
        cooldown_manager.reset_cooldown("google")
        self.assertTrue(cooldown_manager.is_provider_available("google"))

    def test_cooldown_can_be_disabled(self):
        settings.LLM_COOLDOWN_HOURS = 0.0
        cooldown_manager.mark_cooldown("google", "HTTP 429", duration_hours=24.0)

        self.assertTrue(cooldown_manager.is_provider_available("google"))
        self.assertEqual(cooldown_manager.get_remaining_cooldown_seconds("google"), 0.0)

    @patch("src.llm.openrouter_client.call_llm")
    @patch("src.llm.google_client.call_llm")
    def test_failover_and_subsequent_skip(self, mock_google, mock_openrouter):
        settings.LLM_COOLDOWN_HOURS = 24.0
        settings.LLM_PROVIDER = "auto"
        settings.LLM_PROVIDER_ORDER = ["google", "openrouter"]
        mock_google.side_effect = GoogleQuotaError("HTTP 429 Quota Exceeded")
        mock_openrouter.return_value = '{"synthese": "test"}'

        # Call 1: Google fails with 429 -> marks cooldown -> failover to OpenRouter
        messages = [{"role": "user", "content": "hello"}]
        result = client.call_llm(messages)
        self.assertEqual(result, '{"synthese": "test"}')
        self.assertEqual(mock_google.call_count, 1)
        self.assertEqual(mock_openrouter.call_count, 1)
        self.assertFalse(cooldown_manager.is_provider_available("google"))

        # Call 2: Google is in 24h cooldown -> should NOT even be called! OpenRouter called directly.
        mock_google.reset_mock()
        mock_openrouter.reset_mock()

        result2 = client.call_llm(messages)
        self.assertEqual(result2, '{"synthese": "test"}')
        self.assertEqual(mock_google.call_count, 0)  # Google was completely skipped!
        self.assertEqual(mock_openrouter.call_count, 1)

    @patch("src.llm.openrouter_client.call_llm")
    @patch("src.llm.google_client.call_llm")
    def test_both_in_cooldown_raises_error(self, mock_google, mock_openrouter):
        settings.LLM_COOLDOWN_HOURS = 24.0
        for p in ("google", "openrouter", "nvidia"):
            cooldown_manager.mark_cooldown(p, "429", 24)

        messages = [{"role": "user", "content": "hello"}]
        with self.assertRaises(client.LLMError) as ctx:
            client.call_llm(messages)

        self.assertIn("Tous les fournisseurs LLM sont actuellement bloqués par un cooldown", str(ctx.exception))
        self.assertEqual(mock_google.call_count, 0)
        self.assertEqual(mock_openrouter.call_count, 0)

    def test_api_key_change_lifts_cooldown_immediately(self):
        settings.LLM_COOLDOWN_HOURS = 24.0
        old_key = getattr(settings, "NVIDIA_API_KEY", "old_nvidia_key")
        settings.NVIDIA_API_KEY = "initial_key_123"

        # Marquer Nvidia en cooldown 24h
        cooldown_manager.mark_cooldown("nvidia", "HTTP 429 Quota Exceeded", duration_hours=24.0)
        self.assertFalse(cooldown_manager.is_provider_available("nvidia"))
        self.assertGreater(cooldown_manager.get_remaining_cooldown_seconds("nvidia"), 0.0)

        # L'utilisateur change sa clé API Nvidia
        settings.NVIDIA_API_KEY = "new_fresh_key_456"

        # Le cooldown doit être immédiatement levé !
        self.assertTrue(cooldown_manager.is_provider_available("nvidia"))
        self.assertEqual(cooldown_manager.get_remaining_cooldown_seconds("nvidia"), 0.0)

        # Rétablir la clé originale
        settings.NVIDIA_API_KEY = old_key

    def test_legacy_cooldown_without_fingerprint_is_lifted(self):
        settings.LLM_COOLDOWN_HOURS = 24.0
        # Simuler un fichier de cooldown existant sans champ key_fingerprint
        legacy_state = {
            "google": {
                "cooldown_until": 9999999999.0,
                "duration_hours": 24.0,
                "reason": "Old legacy 429 without fingerprint",
            }
        }
        import json
        with open(cooldown_manager.COOLDOWN_FILE, "w", encoding="utf-8") as f:
            json.dump(legacy_state, f)

        # Doit être immédiatement disponible et le cooldown levé
        self.assertTrue(cooldown_manager.is_provider_available("google"))
        self.assertEqual(cooldown_manager.get_remaining_cooldown_seconds("google"), 0.0)


if __name__ == "__main__":
    unittest.main()
