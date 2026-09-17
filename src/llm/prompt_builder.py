"""
Constructeur de prompts optimisé pour chaque étage de la pyramide d'analyse.
Réexporte les fonctions des modules spécialisés dans src/llm/prompts/.
"""
from src.llm.prompts.prompt_loader import (
    get_system_prompt,
    get_json_shape,
    load_system_prompts,
    load_json_shapes,
)
from src.llm.prompts.prompt_stage1 import build_stage1_messages, STAGE1_JSON_SHAPE, STAGE1_SYSTEM_PROMPT
from src.llm.prompts.prompt_stage2 import build_stage2_messages, STAGE2_JSON_SHAPE, STAGE2_SYSTEM_PROMPT
from src.llm.prompts.prompt_stage3 import build_stage3_messages, STAGE3_JSON_SHAPE, STAGE3_SYSTEM_PROMPT
from src.llm.prompts.prompt_stage4 import build_stage4_messages, STAGE4_JSON_SHAPE, STAGE4_SYSTEM_PROMPT
from src.llm.prompts.prompt_stage5 import build_stage5_messages, STAGE5_JSON_SHAPE, STAGE5_SYSTEM_PROMPT

__all__ = [
    "get_system_prompt",
    "get_json_shape",
    "load_system_prompts",
    "load_json_shapes",
    "build_stage1_messages",
    "STAGE1_JSON_SHAPE",
    "STAGE1_SYSTEM_PROMPT",
    "build_stage2_messages",
    "STAGE2_JSON_SHAPE",
    "STAGE2_SYSTEM_PROMPT",
    "build_stage3_messages",
    "STAGE3_JSON_SHAPE",
    "STAGE3_SYSTEM_PROMPT",
    "build_stage4_messages",
    "STAGE4_JSON_SHAPE",
    "STAGE4_SYSTEM_PROMPT",
    "build_stage5_messages",
    "STAGE5_JSON_SHAPE",
    "STAGE5_SYSTEM_PROMPT",
]
