"""
PROMPT STAGE 1 : Faits bruts (Niveau 0) -> Micro-synthèse (Niveau 1).

Analyse un lot de 6 à 8 documents d'un même domaine pour en extraire
une micro-synthèse factuelle et structurée.

Les prompts et formats sont configurables dans :
- System_Prompt.md (section ## STAGE 1)
- System_Traitement.md (section ## STAGE 1)
"""
from typing import List, Dict
from config import settings
from src.llm.prompts.prompt_loader import get_system_prompt, get_json_shape

# Chargement dynamique depuis System_Prompt.md et System_Traitement.md
STAGE1_SYSTEM_PROMPT = get_system_prompt(1)
STAGE1_JSON_SHAPE = get_json_shape(1)


def build_stage1_messages(documents: List[Dict], domaine: str) -> list:
    """Construit la liste des messages (system + user) pour le Stage 1."""
    system_prompt = get_system_prompt(1)
    json_shape = get_json_shape(1)

    items = []
    for idx, doc in enumerate(documents, start=1):
        title = doc.get("title", "Sans titre")
        muni = doc.get("municipality") or doc.get("department") or "Corse"
        raw_text = (doc.get("raw_text", "") or "")[: settings.RAW_TEXT_MAX_CHARS]
        pub_date = str(doc.get("publication_date") or "")[:10]
        items.append(f"[{idx}] Lieu: {muni} ({pub_date}) | Titre: {title}\nExtrait: {raw_text}")
    
    docs_block = "\n\n".join(items)
    user_content = (
        f"THÉMATIQUE EXCLUSIVE : {domaine.upper()}\n"
        f"Voici {len(documents)} faits bruts collectés sur ce domaine, numérotés [1] à [{len(documents)}] :\n\n"
        f"{docs_block}\n\n"
        f"IMPORTANT : chaque document numéroté ci-dessus peut décrire un événement DIFFÉRENT "
        f"(dates différentes, lieux différents, causes différentes), même s'ils partagent le même "
        f"domaine thématique. Ne fusionne JAMAIS deux faits qui n'apparaissent pas dans le MÊME "
        f"document numéroté (ex: n'attribue pas une évacuation due à un orage [doc X] à un incendie "
        f"décrit dans un autre document [doc Y]).\n\n"
        f"Pour le champ \"documents_cites\", indique la liste des numéros [1..{len(documents)}] "
        f"des documents qui appuient réellement ta \"cause\" et ta \"preuve\".\n\n"
        f"Produis la micro-synthèse d'analyse au format JSON strict suivant :\n{json_shape}"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]