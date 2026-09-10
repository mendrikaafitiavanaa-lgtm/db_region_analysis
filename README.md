# 🏛️ Système d'Analyse et Enrichissement Territorial Pyramidal (Corse)

Système d'intelligence artificielle pyramidal et multi-niveaux conçu pour analyser, catégoriser et synthétiser des milliers d'articles et signalements bruts régionaux, afin de produire des rapports stratégiques pour les décideurs territoriaux.

---

## 🏗️ Architecture Pyramidale (5 Niveaux)

Le pipeline transforme les données non structurées en décisions concrètes à travers 5 étages de consolidation progressive :

```text
[ Sommet Ultime - Stage 5 ]   db_france_rapport_mensuel_finale  --> 1 Synthèse Arbitrage Problème N°1
               ▲
[ Sommet Global - Stage 4 ]   db_france_rapport_mensuel         --> 1 Rapport Transversal Global
               ▲
[ Niveau 3 (L3) - Stage 3 ]   db_france_bilans_domaines         --> 9 Grands Bilans Sectoriels
               ▲
[ Niveau 2 (L2) - Stage 2 ]   db_france_syntheses_l2            --> ~36 Méso-synthèses consolidées
               ▲
[ Niveau 1 (L1) - Stage 1 ]   db_france_syntheses_l1            --> ~266 Micro-synthèses par lot
               ▲
[ Niveau 0 (Brut) - Source]   db_france                         --> +2 000 Articles bruts collectés
```

---

## 🗄️ Rôle des Collections MongoDB

| Étape | Nom de la Collection | Description & Contenu |
| :--- | :--- | :--- |
| **Source** | `db_france` | Données brutes (+2 100 articles / arrêtés municipaux). |
| **Stage 1** | `db_france_syntheses_l1` | Micro-synthèses par lots homogènes de 6 à 8 articles du même domaine. |
| **Stage 2** | `db_france_syntheses_l2` | Méso-synthèses consolidées par zone et domaine d'action. |
| **Stage 3** | `db_france_bilans_domaines` | 9 grands bilans officiels (Santé, Transports, Risques, Économie, etc.). |
| **Stage 4** | `db_france_rapport_mensuel` | Rapport stratégique transversal global croisant tous les domaines. |
| **Stage 5** | `db_france_rapport_mensuel_finale` | **Synthèse d'arbitrage ultime** : identifie l'unique problème N°1 le plus persistant avec plan d'action d'urgence. |

---

## ⚡ Caractéristiques Techniques & Résilience

- **Zero-Token Clustering** : Regroupement thématique instantané via `flashtext` (arbre de recherche Trie) sans consommer de tokens LLM.
- **Multi-Provider & Failover** : Basculement automatique entre Google Gemini et OpenRouter en cas d'indisponibilité ou d'épuisement de quota.
- **Anti-429 & Rate Limiter** : Algorithme Token-Bucket global (14 req/min) pour protéger les clés gratuites contre les erreurs de limitation de débit.
- **Reprise sur Incident (Idempotence)** : Déduplication automatique évitant de retraiter les documents déjà synthétisés en cas de relance.

---

## 🚀 Installation & Configuration

### 1. Prérequis
- Python 3.10+
- MongoDB local ou distant

### 2. Installation des dépendances
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configuration de l'environnement
Copiez `.env.example` vers `.env` et renseignez vos clés d'API :
```bash
cp .env.example .env
```

---

## 💻 Utilisation

```bash
# Exécuter l'ensemble de la pyramide (Stages 1 à 5)
python main.py

# Exécuter un étage spécifique
python main.py --stage 1    # Articles bruts -> Micro-synthèses L1
python main.py --stage 2    # Synthèses L1   -> Méso-synthèses L2
python main.py --stage 3    # Synthèses L2   -> Bilans de domaines L3
python main.py --stage 4    # Bilans domaine -> Rapport Global Territorial
python main.py --stage 5    # Rapport Global -> Synthèse Arbitrage Problème N°1

# Filtrer sur un mois spécifique (ex: août 2026)
python main.py --stage all --mois 2026-08
```

---

## 🧪 Tests Unitaires

Pour valider l'ensemble du pipeline hors ligne (0 token consommé, mocks complets) :
```bash
python -m unittest tests/test_pipeline_stages.py
```