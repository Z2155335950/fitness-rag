from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=False)

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PARSED_DIR = DATA_DIR / "parsed"
EVAL_DIR = DATA_DIR / "eval"
DB_DIR = PROJECT_ROOT / "db"
CHAT_DB_PATH = DB_DIR / "chat_history.sqlite3"
AUTH_SECRET_PATH = DB_DIR / ".auth_secret"

DEFAULT_MODEL = "BAAI/bge-small-zh-v1.5"
COLLECTION_NAME = "fitness"
FIELD_COLLECTION_NAME = "fitness_action_fields"
