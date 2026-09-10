# 🏛️ Système d'Analyse et Enrichissement Territorial Pyramidal (Corse)

Système d'intelligence artificielle pyramidal et multi-niveaux conçu pour analyser, catégoriser et synthétiser des milliers d'articles et signalements bruts régionaux, afin de produire des rapports stratégiques pour les décideurs territoriaux.
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
  installe requirements.txt et python.main executer