import re
import hashlib
from typing import Dict, Any

REQUIRED_SECTIONS = {
    "complaints":   ["жалоб", "жалобы", "жалуется"],
    "anamnesis":    ["анамнез", "история болезни", "болеет"],
    "examination":  ["осмотр", "объективно", "состояние"],
    "diagnosis":    ["диагноз", "ds:", "мкб"],
    "treatment":    ["назначен", "лечение", "рекомендован", "препарат"],
}

DOCUMENT_KEYWORDS = {
    "discharge":   ["выписной", "эпикриз", "выписка"],
    "history":     ["история болезни", "история заболевания"],
    "referral":    ["направление", "направляется"],
    "ambulatory":  ["амбулаторн", "поликлиник"],
}

PII_PATTERNS = [
    r"\b\d{2}[./]\d{2}[./]\d{4}\b",      # dates like 01.01.1990
    r"\+?[78]\s?\(?\d{3}\)?\s?\d{3}[-\s]?\d{2}[-\s]?\d{2}",  # phone numbers
    r"\b[А-ЯЁ][а-яё]+\s[А-ЯЁ][а-яё]+\s[А-ЯЁ][а-яё]+\b",    # full names (3 words)
]


def detect_pii(text: str) -> list[str]:
    warnings = []
    for pattern in PII_PATTERNS:
        if re.search(pattern, text):
            warnings.append("Обнаружены возможные персональные данные. Удалите их перед отправкой.")
            break
    return warnings


def classify_document(text: str) -> str:
    text_lower = text.lower()
    for doc_type, keywords in DOCUMENT_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return doc_type
    return "unknown"


def check_completeness(text: str) -> Dict[str, Any]:
    text_lower = text.lower()
    found = {}
    missing = []

    for section, keywords in REQUIRED_SECTIONS.items():
        found[section] = any(kw in text_lower for kw in keywords)
        if not found[section]:
            missing.append(section)

    score = round((sum(found.values()) / len(found)) * 100, 1)
    return {"sections_found": found, "missing_sections": missing, "score": score}


def analyze_document(text: str) -> Dict[str, Any]:
    pii_warnings = detect_pii(text)
    completeness = check_completeness(text)
    doc_type = classify_document(text)

    word_count = len(text.split())
    quality_score = completeness["score"]
    if word_count < 50:
        quality_score = max(0, quality_score - 20)

    remarks = []
    for section in completeness["missing_sections"]:
        remarks.append(f"Отсутствует раздел: {section}")
    if word_count < 50:
        remarks.append("Документ слишком короткий (менее 50 слов)")
    if pii_warnings:
        remarks.extend(pii_warnings)

    return {
        "quality_score": round(quality_score, 1),
        "document_type": doc_type,
        "word_count": word_count,
        "sections": completeness["sections_found"],
        "missing_sections": completeness["missing_sections"],
        "remarks": remarks,
        "pii_warnings": pii_warnings,
        "text_hash": hashlib.sha256(text.encode()).hexdigest()[:16],
    }
