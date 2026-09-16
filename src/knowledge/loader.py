import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "processed"

def load_terms():
    return json.loads((DATA_DIR / "terms.json").read_text(encoding="utf-8"))

def load_morphemes():
    return json.loads((DATA_DIR / "morphemes.json").read_text(encoding="utf-8"))

def get_chapters():
    terms = load_terms()
    return sorted(set(t["chapter"] for t in terms if t.get("chapter")))

def get_terms_by_chapter(chapter):
    return [t for t in load_terms() if t.get("chapter") == chapter]

def get_terms_by_morpheme(morpheme_id):
    return [t for t in load_terms() if morpheme_id in t.get("morphemes", [])]