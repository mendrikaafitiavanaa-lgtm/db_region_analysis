"""
Point de compatibilité pour lancer le pipeline complet ou par étape.
Délègue directement à src.pipeline.orchestrator.run_pipeline.
"""
from src.pipeline.orchestrator import run_pipeline


def run(stage: str = "all"):
    """Exécute le pipeline pyramidal."""
    return run_pipeline(stage=stage)


if __name__ == "__main__":
    run()
