"""
Medical text improvement engine.
1. Masks PII before any external call.
2. Structures text into standard sections.
3. If ANTHROPIC_API_KEY is set — calls Claude Haiku for quality rewriting.
   Otherwise falls back to rule-based structuring (still useful).
"""
import re
import os
from typing import Optional

# ---------------------------------------------------------------------------
# PII masking
# ---------------------------------------------------------------------------

_PII_RULES = [
    # Full names: Иванов Иван Иванович
    (re.compile(r'\b[А-ЯЁ][а-яё]+-?[А-ЯЁ]?[а-яё]*\s[А-ЯЁ][а-яё]+\.?\s?(?:[А-ЯЁ][а-яё]+\.?)?\b'), '[ФИО]'),
    # Dates: 01.01.1990 or 01/01/1990
    (re.compile(r'\b\d{1,2}[./]\d{1,2}[./]\d{4}\b'), '[ДАТА]'),
    # Russian phone numbers
    (re.compile(r'(?:\+?[78][\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}'), '[ТЕЛЕФОН]'),
    # Passport/SNILS-like numbers
    (re.compile(r'\b\d{2}\s?\d{2}\s?\d{6}\b'), '[ДОКУМЕНТ]'),
    # INN-like 12-digit numbers
    (re.compile(r'\b\d{12}\b'), '[ДОКУМЕНТ]'),
    # Ages: 45 лет / 45-летн
    (re.compile(r'\b\d{1,3}[\s-]лет[а-я]*\b', re.IGNORECASE), '[ВОЗРАСТ]'),
]


def mask_pii(text: str) -> tuple[str, list[str]]:
    """Returns (masked_text, list_of_warnings)."""
    masked = text
    found = []
    for pattern, replacement in _PII_RULES:
        if pattern.search(masked):
            found.append(f"Обнаружены персональные данные: заменено на {replacement}")
            masked = pattern.sub(replacement, masked)
    return masked, found


# ---------------------------------------------------------------------------
# Section templates
# ---------------------------------------------------------------------------

SECTION_KEYWORDS = {
    "ЖАЛОБЫ": ["жалоб", "жалуется", "беспокоит", "беспокоят"],
    "АНАМНЕЗ": ["анамнез", "история болезни", "болеет", "страдает"],
    "ОБЪЕКТИВНО": ["осмотр", "объективно", "состояние", "аускультация", "перкуссия"],
    "ДИАГНОЗ": ["диагноз", "ds:", "мкб", "диагностирован"],
    "ЛЕЧЕНИЕ": ["назначен", "лечение", "рекомендован", "препарат", "терапия"],
}

SECTION_TEMPLATES = {
    "ЖАЛОБЫ": "Жалобы: [заполнить — основные жалобы пациента]",
    "АНАМНЕЗ": "Анамнез: [заполнить — когда началось, как развивалось]",
    "ОБЪЕКТИВНО": "Объективно: состояние [заполнить]. АД [заполнить] мм рт. ст.",
    "ДИАГНОЗ": "Диагноз: [заполнить — основной диагноз по МКБ-10]",
    "ЛЕЧЕНИЕ": "Лечение: [заполнить — препараты, дозы, длительность]",
}


def _find_missing_sections(text: str) -> list[str]:
    text_lower = text.lower()
    missing = []
    for section, keywords in SECTION_KEYWORDS.items():
        if not any(kw in text_lower for kw in keywords):
            missing.append(section)
    return missing


def _rule_based_improve(text: str) -> str:
    """Structure text and add missing section templates."""
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    structured = "\n".join(lines)

    missing = _find_missing_sections(text)
    if missing:
        structured += "\n\n--- Требуется заполнить ---\n"
        for section in missing:
            structured += f"\n{SECTION_TEMPLATES[section]}"

    return structured


# ---------------------------------------------------------------------------
# LLM improvement (Claude Haiku — cheapest, fast)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """Ты — медицинский редактор. Твоя задача: улучшить структуру и читаемость медицинского документа на русском языке.

Правила:
1. Сохраняй ВСЕ медицинские факты без изменений.
2. Структурируй текст по разделам: ЖАЛОБЫ, АНАМНЕЗ, ОБЪЕКТИВНО, ДИАГНОЗ, ЛЕЧЕНИЕ.
3. Если раздел отсутствует в исходном тексте — добавь шаблон [требует заполнения].
4. Исправляй грамматические ошибки, раскрывай сокращения там где это понятно из контекста.
5. НЕ придумывай медицинские данные — только структурируй существующие.
6. Отвечай ТОЛЬКО улучшенным текстом документа, без пояснений."""


def _llm_improve(masked_text: str) -> Optional[str]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": masked_text}],
        )
        return message.content[0].text
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def improve_text(original_text: str) -> dict:
    """
    Main entry point. Returns dict with:
    - masked_text: PII-free version
    - improved_text: structured/improved version
    - missing_sections: list of sections not found
    - pii_warnings: list of PII types that were masked
    - method: 'llm' or 'rules'
    """
    masked, pii_warnings = mask_pii(original_text)
    missing = _find_missing_sections(masked)

    llm_result = _llm_improve(masked)
    if llm_result:
        improved = llm_result
        method = "llm"
    else:
        improved = _rule_based_improve(masked)
        method = "rules"

    return {
        "masked_text": masked,
        "improved_text": improved,
        "missing_sections": missing,
        "pii_warnings": pii_warnings,
        "method": method,
    }
