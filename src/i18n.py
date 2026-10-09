import json
from pathlib import Path

LANG = "de"
_TRANSLATIONS = json.loads((Path(__file__).parent / "translations.json").read_text(encoding="utf-8"))

def set_language(language):
    global LANG
    LANG = language if language in ("de", "en") else "de"

def tr(text):
    return _TRANSLATIONS.get(text, text) if LANG == "en" else text
