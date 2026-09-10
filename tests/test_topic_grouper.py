"""
Tests unitaires pour la classification et le partitionnement thématique local (FlashText).
"""
import unittest
from src.pipeline.topic_grouper import classify_document, group_documents_into_batches


class TestTopicGrouper(unittest.TestCase):
    def test_classify_known_domains(self):
        # 1. Santé
        d_sante = classify_document(
            title="Pénurie de médecins généralistes",
            raw_text="Les urgences de l'hôpital d'Ajaccio et les praticiens de santé alertent sur le manque de soins.",
        )
        self.assertEqual(d_sante, "sante_secours")

        # 2. Environnement / Risques
        d_env = classify_document(
            title="Incendie de forêt attisé par le vent",
            raw_text="Les sapeurs-pompiers et le SDIS luttent contre les flammes et la sécheresse dans le maquis.",
        )
        self.assertEqual(d_env, "environnement_climat_risques")

        # 3. Transports
        d_trans = classify_document(
            title="Perturbations maritimes et ferroviaires",
            raw_text="Les ferries de Corsica Linea et les trains CFC subissent des retards importants au port.",
        )
        self.assertEqual(d_trans, "transport_mobilite")

        # 4. Sécurité & Justice
        d_sec = classify_document(
            title="Enquête judiciaire après une fusillade",
            raw_text="La gendarmerie et le parquet mènent l'enquête suite à un vol à main armée.",
        )
        self.assertEqual(d_sec, "securite_justice")

        # 5. Économie & Tourisme
        d_eco = classify_document(
            title="Bilan touristique et fréquentation des hôtels",
            raw_text="Les commerces et restaurants constatent une saison en demi-teinte et la baisse du pouvoir d'achat.",
        )
        self.assertEqual(d_eco, "economie_tourisme")

    def test_classify_out_of_domain_and_unknown_words(self):
        # Mot économique spécifique comme 'inflation'
        d_inf = classify_document(
            title="Impact de l'inflation sur les ménages",
            raw_text="La hausse des prix et du carburant pèse sur les artisans et entreprises.",
        )
        self.assertEqual(d_inf, "economie_tourisme")

        # Texte complètement exotique ou sans mot-clé -> fallback automatique
        d_unknown = classify_document(
            title="Un événement insolite dans le cosmos",
            raw_text="Astronomie quantique et télescopes orbitaux lointains.",
        )
        self.assertEqual(d_unknown, "politique_societe_vie_locale")

        # Texte vide
        d_empty = classify_document(title="", raw_text="")
        self.assertEqual(d_empty, "politique_societe_vie_locale")

    def test_group_documents_into_batches_strict_domain_separation(self):
        docs = []
        # 10 docs Santé
        for i in range(10):
            docs.append({
                "document_id": f"sante_{i}",
                "title": f"Médecin {i}",
                "raw_text": "Hôpital et urgences de garde.",
            })
        # 8 docs Transports
        for i in range(8):
            docs.append({
                "document_id": f"trans_{i}",
                "title": f"Route {i}",
                "raw_text": "Circulation sur la voirie et ferry au port.",
            })
        # 4 docs Incendie
        for i in range(4):
            docs.append({
                "document_id": f"feu_{i}",
                "title": f"Incendie {i}",
                "raw_text": "Feu de forêt et pompiers mobilisés.",
            })

        batches = group_documents_into_batches(docs, batch_size=8, min_batch_size=2)
        
        # Doit contenir :
        # - Santé : 1 lot de 8 + 1 lot de 2 (reliquat rattaché au même domaine)
        # - Transports : 1 lot de 8
        # - Incendie : 1 lot de 4
        self.assertEqual(len(batches), 4)

        # Vérification de l'étanchéité absolue (aucun mélange)
        domains_in_batches = [b["domaine"] for b in batches]
        self.assertEqual(domains_in_batches.count("sante_secours"), 2)
        self.assertEqual(domains_in_batches.count("transport_mobilite"), 1)
        self.assertEqual(domains_in_batches.count("environnement_climat_risques"), 1)

        # Vérifier que les documents de chaque lot ont tous le bon préfixe
        for b in batches:
            dom = b["domaine"]
            for d in b["documents"]:
                if dom == "sante_secours":
                    self.assertTrue(d["document_id"].startswith("sante_"))
                elif dom == "transport_mobilite":
                    self.assertTrue(d["document_id"].startswith("trans_"))
                elif dom == "environnement_climat_risques":
                    self.assertTrue(d["document_id"].startswith("feu_"))


if __name__ == "__main__":
    unittest.main()
