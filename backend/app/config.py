from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / 'data'
UPLOADS_DIR = DATA_DIR / 'uploads'
SAMPLES_DIR = DATA_DIR / 'samples'
RUNS_DIR = DATA_DIR / 'runs'
DB_PATH = DATA_DIR / 'multi_agent.sqlite3'
FRONTEND_DIST_DIR = BASE_DIR / 'frontend' / 'dist'


def _load_dotenv() -> None:
    for candidate in (BASE_DIR / '.env', BASE_DIR / 'backend' / '.env'):
        if not candidate.exists():
            continue
        for raw_line in candidate.read_text(encoding='utf-8-sig').splitlines():
            line = raw_line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            key = key.strip().lstrip('\ufeff')
            value = value.strip().strip('"').strip("'")
            current_value = os.environ.get(key)
            if current_value is None or current_value == '':
                os.environ[key] = value


_load_dotenv()

MAX_RETRIES = int(os.getenv('MAX_RETRIES', '2'))
REAL_MODE_DEFAULT_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

_DEFAULT_MODELS = ['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo', 'gpt-4', 'o1-mini', 'o3-mini']
_RAW_MODEL_OPTIONS = [item.strip() for item in os.getenv('OPENAI_MODEL_OPTIONS', '').split(',') if item.strip()]
REAL_MODE_MODEL_OPTIONS = list(dict.fromkeys(_RAW_MODEL_OPTIONS or _DEFAULT_MODELS))
if REAL_MODE_DEFAULT_MODEL not in REAL_MODE_MODEL_OPTIONS:
    REAL_MODE_MODEL_OPTIONS.insert(0, REAL_MODE_DEFAULT_MODEL)
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')


def ensure_directories() -> None:
    for path in (DATA_DIR, UPLOADS_DIR, SAMPLES_DIR, RUNS_DIR):
        path.mkdir(parents=True, exist_ok=True)

