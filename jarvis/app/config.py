"""
Global configuration and naming settings for NIVA.
All assistant branding and wake words are dynamically configurable.
"""

import os
from typing import List

# Assistant Name (Configurable via environment variable or settings)
DEFAULT_NAME = "NIVA"
ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", DEFAULT_NAME).strip() or DEFAULT_NAME

# Default Wake Words based on configured name
DEFAULT_WAKE_WORDS: List[str] = [
    ASSISTANT_NAME.lower(),
    f"hey {ASSISTANT_NAME.lower()}",
    f"ok {ASSISTANT_NAME.lower()}",
    f"hi {ASSISTANT_NAME.lower()}",
    "niva",
    "hey niva",
    "ok niva",
]

# Storage & Database Paths
STORAGE_DIR = os.path.join(os.path.expanduser("~"), f".{ASSISTANT_NAME.lower()}")
DATABASE_PATH = os.path.join(STORAGE_DIR, f"{ASSISTANT_NAME.lower()}.db")

# NLU Model Paths
MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai", "models")
NLU_MODEL_PATH = os.path.join(MODELS_DIR, "nlu_model.joblib")
NLU_METADATA_PATH = os.path.join(MODELS_DIR, "nlu_metadata.json")
DATASET_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "niva_commands_dataset.jsonl")
