# ⚙️ SYSTÈME DE TRAITEMENT — FORMATS JSON DE SORTIE (STAGES 1 À 5)

> **GUIDE DE MODIFICATION :**
> - Ce fichier définit les **gabarits JSON (JSON Shapes)** attendus pour chaque étage du traitement.
> - Vous pouvez ajuster les consignes, les descriptions de champs ou les exemples directement ici **sans modifier le code Python**.
> - Chaque étage commence par un titre : `## STAGE X : ...` suivi du bloc de code JSON ```json ... ```.
> - **Attention :** Si vous modifiez les noms de clés JSON fondamentales (ex: `cause`, `preuve`, `gravite`), veillez à vérifier les correspondances avec le schéma MongoDB (`analyse_schema.py`).

---

## STAGE 1 : Micro-synthèse (Niveau 1)

<!--
CHAMPS ATTENDUS :
- gravite : Niveau de sévérité ("faible" | "modere" | "grave")
- resume_court : Résumé concis en 1-2 phrases
- problematique_identifiee : Problème saillant ou récurrent
- cause : Cause factuelle déduite des faits réels (obligatoire)
- preuve : Chiffres, faits tangibles, constats vérifiables (obligatoire)
- consequence_potentielle : Impact prévisible
- besoins_reels_detectes : Besoins exprimés sur le terrain
- solutions_recommandees : Actions recommandées
-->

```json
{
  "gravite": "faible | modere | grave",
  "resume_court": "Synthèse factuelle en 1 à 2 phrases du lot de signalements.",
  "problematique_identifiee": "Problématique récurrente ou incident saillant constaté sur l'ensemble du lot.",
  "cause": "Cause factuelle et réelle de l'événement ou de la situation tirée des documents sources (sans invention).",
  "preuve": "Éléments probants, chiffres concrets, faits tangibles ou constats rapportés par les sources attestant de la situation.",
  "consequence_potentielle": "Risque direct pour la population, les services publics ou l'écosystème.",
  "besoins_reels_detectes": "Besoins prioritaires constatés sur le terrain.",
  "solutions_recommandees": "Actions concrètes préconisées à court/moyen terme adaptées à la situation."
}
```

---

## STAGE 2 : Méso-synthèse Intermédiaire (Niveau 2)

<!--
CHAMPS ATTENDUS :
- gravite : Niveau de sévérité global de la zone/domaine ("faible" | "modere" | "grave")
- resume_consolide : Synthèse intégrant les faits saillants des micro-synthèses L1
- tendance_majeure : Tendance de fond ou dynamique territoriale observée
- cause : Cause structurelle ou directe commune aux micro-synthèses (sans invention)
- preuve : Preuves tangibles et chiffres cumulés corroborés par les synthèses L1
- impacts_territoriaux : Impacts cumulés sur les services ou la population
- actions_prioritaires : Actions collectives d'urgence ou correctives
-->

```json
{
  "gravite": "faible | modere | grave",
  "resume_consolide": "Synthèse consolidée intégrant les faits saillants des micro-synthèses.",
  "tendance_majeure": "Tendance de fond ou aggravation observée sur cette zone géographique.",
  "cause": "Causes structurelles ou directes communes identifiées à partir des micro-synthèses (sans invention).",
  "preuve": "Preuves tangibles, données chiffrées cumulées ou faits marquants corroborés par les synthèses de terrain.",
  "impacts_territoriaux": "Impacts cumulés sur le fonctionnement des services ou de la population.",
  "actions_prioritaires": "Actions collectives d'urgence ou correctives structurelles requises."
}
```

---

## STAGE 3 : Grand Bilan Mensuel de Domaine (Niveau 3)

<!--
CHAMPS ATTENDUS :
- gravite_globale : Niveau global du domaine ("faible" | "modere" | "grave")
- bilan_executif : Bilan complet du domaine sur le mois pour la Corse
- cause : Cause structurelle majeure expliquant les difficultés du secteur
- preuve : Données statistiques globales, indicateurs factuels
- points_chauds_geographiques : Liste des communes/zones en tension
- principaux_dysfonctionnements : Liste des dysfonctionnements critiques
- preconisations_strategiques : Liste des recommandations prioritaires pour les décideurs
-->

```json
{
  "gravite_globale": "faible | modere | grave",
  "bilan_executif": "Bilan complet et structuré du domaine sur l'ensemble du mois pour la Corse.",
  "cause": "Cause structurelle ou facteur déclencheur majeur expliquant les difficultés du domaine ce mois-ci.",
  "preuve": "Données probantes, statistiques globales, indicateurs factuels ou constats clés étayant ce bilan sectoriel.",
  "points_chauds_geographiques": [
    "Lieu/Secteur A : nature des difficultés observées",
    "Lieu/Secteur B : faits notables ou tensions"
  ],
  "principaux_dysfonctionnements": [
    "Dysfonctionnement ou risque critique 1",
    "Dysfonctionnement ou risque critique 2"
  ],
  "preconisations_strategiques": [
    "Mesure structurelle prioritaire 1",
    "Mesure d'urgence ou accompagnement 2"
  ]
}
```

---

## STAGE 4 : Rapport Stratégique Territorial Global (Niveau 4 - Sommet)

<!--
CHAMPS ATTENDUS :
- titre : Titre du rapport (ex: "Rapport Stratégique Territorial - Corse (Août 2026)")
- statut_general : Statut d'ensemble ("calme" | "sous_tension" | "critique")
- cause : Causes profondes transversales expliquant l'état de l'île
- preuve : Preuves tangibles et faits marquants transversaux vérifiables
- faits_marquants_du_mois : Liste des 3 à 5 événements transversaux majeurs
- synthese_transversale : Analyse croisée systémique entre domaines
- tableau_de_bord_domaines : Liste des statuts résumés par grand domaine
- recommandations_prioritaires_decideurs : Liste des arbitrages et décisions d'urgence
-->

```json
{
  "titre": "Rapport Stratégique Territorial - Corse (Mois)",
  "statut_general": "calme | sous_tension | critique",
  "cause": "Causes profondes, systémiques ou transversales expliquant l'état global du territoire ce mois-ci.",
  "preuve": "Preuves tangibles, indicateurs clés et faits marquants transversaux vérifiables corroborant la situation.",
  "faits_marquants_du_mois": [
    "Fait marquant transversal majeur 1",
    "Fait marquant transversal majeur 2",
    "Fait marquant transversal majeur 3"
  ],
  "synthese_transversale": "Analyse systémique globale croisant les dynamiques sectorielles observées sur l'île.",
  "tableau_de_bord_domaines": [
    {
      "domaine": "nom_du_domaine",
      "gravite": "faible | modere | grave",
      "resume_cle": "Synthèse d'impact du domaine en une phrase percutante."
    }
  ],
  "recommandations_prioritaires_decideurs": [
    "Décision d'arbitrage ou action d'urgence 1",
    "Mesure de coordination interservices 2",
    "Plan de résilience ou investissement prioritaire 3"
  ]
}
```

---

## STAGE 5 : Synthèse Exécutive Finale N°1 (Niveau 5 - Sommet Ultime)

<!--
CHAMPS ATTENDUS :
- domaine_prioritaire_identifie : Domaine prédominant (ex: "sante_secours", "environnement_climat_risques")
- probleme_majeur_persistant : Intitulé de la problématique N°1
- cause : Cause racine ou origine structurelle prouvée
- preuve : Preuves formelles chiffrées et faits documentés
- statut_urgence : "critique" | "tres_eleve" | "eleve"
- justification_priorite_absolue : Démonstration factuelle de la supériorité de cette urgence
- faits_saillants_et_recurrences : Liste des incidents et récurrences clés
- impacts_et_risques_inaction : Risques majeurs en cas d'inaction
- plan_d_action_et_solutions_recommandees : Plan d'action chronologique (Urgence 0-30j, Structurel 1-3 mois)
- verdict_executif : Conclusion et arbitrage final
-->

```json
{
  "domaine_prioritaire_identifie": "nom_du_domaine_predominant",
  "probleme_majeur_persistant": "Intitulé clair et percutant de la problématique N°1",
  "cause": "Cause racine ou origine structurelle prouvée expliquant pourquoi ce problème persiste.",
  "preuve": "Preuves tangibles, données chiffrées précises ou faits réels documentés attestant de la gravité absolue du problème.",
  "statut_urgence": "critique | tres_eleve | eleve",
  "justification_priorite_absolue": "Explication factuelle démontrant pourquoi ce problème surclasse tous les autres en termes de récurrence et d'impact ce mois-ci.",
  "faits_saillants_et_recurrences": [
    "Fait récurrent ou incident saillant 1",
    "Fait récurrent ou incident saillant 2",
    "Fait récurrent ou incident saillant 3"
  ],
  "impacts_et_risques_inaction": "Conséquences graves et systémiques pour la Corse en cas d'inaction à court terme.",
  "plan_d_action_et_solutions_recommandees": [
    {
      "priorite": "Urgence immédiate (0-30 jours)",
      "action": "Action concrète à déclencher immédiatement",
      "acteur_responsable": "Collectivité / État / ARS / Préfecture / Services techniques"
    },
    {
      "priorite": "Mesure structurelle (1-3 mois)",
      "action": "Réforme, investissement ou dispositif correctif de fond",
      "acteur_responsable": "Acteur principal concerné"
    }
  ],
  "verdict_executif": "Conclusion finale en 2 phrases formulant l'arbitrage politique et opérationnel majeur."
}
```
