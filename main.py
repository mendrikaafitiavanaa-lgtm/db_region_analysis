"""
Point d'entrée principal du système d'analyse et synthèse territoriale Corse.

Utilisation :
    # Exécuter l'ensemble de la pyramide (Stages 1 à 5)
    python main.py

    # Exécuter un étage spécifique
    python main.py --stage 1    # 2 000 docs bruts -> 250 micro-synthèses L1
    python main.py --stage 2    # 250 synthèses L1 -> 32 méso-synthèses L2
    python main.py --stage 3    # 32 synthèses L2  -> 9 bilans de domaine L3
    python main.py --stage 4    # 9 bilans domaine -> 1 Rapport Global Territorial
    python main.py --stage 5    # Rapport Global   -> 1 Synthèse Finale Problème N°1

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
        description="Système d'analyse et enrichissement pyramidal multi-niveaux (Corse)"
    )
    parser.add_argument(
        "--stage",
        type=str,
        default="all",
        choices=["1", "2", "3", "4", "5", "all"],
        help="Étage à exécuter (1: micro, 2: méso, 3: bilans domaines, 4: rapport global, 5: synthèse finale problème N°1, all: tout)",
    )
    parser.add_argument(
        "--mois",
        type=str,
        default="",
        help="Mois cible au format YYYY-MM (ex: 2026-08). Écrase la valeur du .env si fourni.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    logger = get_logger()

    if args.mois:
        settings.MOIS_CIBLE = args.mois.strip()
        logger.info(f"Filtre temporel forcé : {settings.MOIS_CIBLE}")

    try:
        run_pipeline(stage=args.stage)
    except KeyboardInterrupt:
        logger.warning("\nArrêt manuel demandé par l'utilisateur (Ctrl+C).")
        sys.exit(0)
    except Exception as exc:
        logger.error(f"Arrêt sur exception non gérée : {exc}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
