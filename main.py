"""
Point d'entrée principal du système d'analyse et synthèse territoriale Corse.

Utilisation :
    # Exécuter l'ensemble de la pyramide pour toutes les collections (Stages 1 à 5)
    python main.py

    # Exécuter un territoire spécifique
    python main.py --dept Haute-Corse
    python main.py --dept "Corse-du-Sud"

    # Exécuter avec une limite de lots pour la session (ex: pause après 50 lots)
    python main.py --stage 1 --limit 50

    # Exécuter un étage spécifique
    python main.py --stage 1    # Docs bruts -> micro-synthèses L1
    python main.py --stage 2    # Synthèses L1 -> méso-synthèses L2
    python main.py --stage 3    # Synthèses L2 -> bilans de domaine L3
    python main.py --stage 4    # Bilans domaine -> Rapport Global Territorial L4
    python main.py --stage 5    # Rapport Global -> Synthèse Finale Problème N°1 L5

    # Filtrer sur un mois spécifique
    python main.py --stage all --mois 2026-08
"""
import argparse
import sys
from config import settings
from src.pipeline.orchestrator import run_pipeline
from src.utils.logger import get_logger


def parse_args():
    parser = argparse.ArgumentParser(
        description="Système d'analyse et enrichissement pyramidal multi-territoires (Corse)"
    )
    parser.add_argument(
        "--stage",
        type=str,
        default="all",
        choices=["1", "2", "3", "4", "5", "all"],
        help="Étage à exécuter (1: micro, 2: méso, 3: bilans domaines, 4: rapport global, 5: synthèse finale problème N°1, all: tout)",
    )
    parser.add_argument(
        "--dept",
        type=str,
        default="all",
        help="Territoire ou collection source cible (ex: 'Haute-Corse', 'Corse-du-Sud', 'Region-Corse', 'Corse', ou 'all' par défaut)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Nombre maximum de lots/documents à traiter lors de cette session (0 = illimité). Idéal pour les pauses et les quotas.",
    )
    parser.add_argument(
        "--mois",
        type=str,
        default="",
        help="Mois cible au format YYYY-MM (ex: 2026-08). Écrase la valeur du .env si fourni.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force la ré-analyse et la mise à jour de tous les documents même s'ils sont déjà présents.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    logger = get_logger()

    if args.mois:
        settings.MOIS_CIBLE = args.mois.strip()
        logger.info(f"Filtre temporel forcé : {settings.MOIS_CIBLE}")

    try:
        run_pipeline(
            stage=args.stage,
            force=args.force,
            dept=args.dept,
            limit=args.limit,
        )
    except KeyboardInterrupt:
        logger.warning("\nArrêt manuel demandé par l'utilisateur (Ctrl+C).")
        sys.exit(0)
    except Exception as exc:
        logger.error(f"Arrêt sur exception : {exc}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
