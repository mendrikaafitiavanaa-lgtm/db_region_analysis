"""
Package des prompts spécialisés par étage de la pyramide d'analyse.
"""
from src.llm.prompts.prompt_stage1 import build_stage1_messages, STAGE1_JSON_SHAPE
from src.llm.prompts.prompt_stage2 import build_stage2_messages, STAGE2_JSON_SHAPE
from src.llm.prompts.prompt_stage3 import build_stage3_messages, STAGE3_JSON_SHAPE
from src.llm.prompts.prompt_stage4 import build_stage4_messages, STAGE4_JSON_SHAPE

__all__ = [
    "build_stage1_messages",
    "STAGE1_JSON_SHAPE",
    "build_stage2_messages",
    "STAGE2_JSON_SHAPE",
    "build_stage3_messages",
    "STAGE3_JSON_SHAPE",
    "build_stage4_messages",
    "STAGE4_JSON_SHAPE",
]
