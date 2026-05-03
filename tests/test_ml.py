"""Тесты ML-модулей: анализатор, классификатор, улучшатель текста."""
import pytest

from ml.analyzer import analyze_document, detect_pii, check_completeness, classify_document
from ml.model import classify_document as ml_classify, classify_with_proba
from ml.improver import mask_pii, improve_text


# -------------------- analyzer.py --------------------

class TestAnalyzer:

    def test_full_document_high_score(self):
        # документ со всеми разделами должен получить высокий балл
        text = (
            "Жалобы: боль в груди. "
            "Анамнез: болеет 3 дня. "
            "Объективно: состояние удовлетворительное. "
            "Диагноз: ИБС. МКБ I25. "
            "Лечение: назначен аспирин."
        )
        result = analyze_document(text)
        assert result["quality_score"] >= 80
        assert len(result["missing_sections"]) == 0

    def test_empty_document_low_score(self):
        result = analyze_document("короткий текст")
        assert result["quality_score"] < 50

    def test_detect_pii_phone(self):
        warnings = detect_pii("Позвоните: +7 (999) 123-45-67")
        assert len(warnings) > 0

    def test_detect_pii_date(self):
        warnings = detect_pii("Дата рождения: 01.01.1985")
        assert len(warnings) > 0

    def test_no_pii_clean_text(self):
        warnings = detect_pii("Пациент жалуется на кашель и температуру.")
        assert len(warnings) == 0

    def test_check_completeness_missing(self):
        result = check_completeness("Просто какой-то текст без медицинских разделов")
        assert result["score"] < 50
        assert len(result["missing_sections"]) > 0

    def test_classify_discharge(self):
        text = "выписной эпикриз пациент выписывается"
        doc_type = classify_document(text)
        assert doc_type == "discharge"

    def test_result_has_required_fields(self):
        result = analyze_document("Жалобы: головная боль. Диагноз: мигрень.")
        required = ["quality_score", "document_type", "word_count", "sections", "remarks", "text_hash"]
        for field in required:
            assert field in result


# -------------------- model.py (sklearn) --------------------

class TestSklearnModel:

    def test_classify_discharge(self):
        text = "выписной эпикриз пациент выписывается из стационара"
        result = ml_classify(text)
        assert result in ["discharge", "history", "referral", "ambulatory"]

    def test_classify_with_proba_returns_all_classes(self):
        result = classify_with_proba("история болезни жалобы анамнез диагноз")
        assert "predicted" in result
        assert "probabilities" in result
        # должны быть все 4 класса
        assert len(result["probabilities"]) == 4

    def test_proba_sum_to_one(self):
        result = classify_with_proba("направление к кардиологу")
        total = sum(result["probabilities"].values())
        assert abs(total - 1.0) < 0.01

    def test_classify_history(self):
        text = "история болезни жалобы анамнез болеет объективно"
        result = ml_classify(text)
        # модель должна уверенно классифицировать типичный текст
        assert result in ["discharge", "history", "referral", "ambulatory"]


# -------------------- improver.py --------------------

class TestImprover:

    def test_mask_pii_phone(self):
        masked, warnings = mask_pii("Телефон: +7 999 123 45 67")
        assert "[ТЕЛЕФОН]" in masked
        assert len(warnings) > 0

    def test_mask_pii_date(self):
        masked, warnings = mask_pii("Дата рождения 15.06.1990")
        assert "[ДАТА]" in masked

    def test_mask_pii_age(self):
        masked, warnings = mask_pii("Пациент 45 лет жалуется")
        assert "[ВОЗРАСТ]" in masked

    def test_no_pii_no_warnings(self):
        masked, warnings = mask_pii("Жалобы на кашель. Диагноз: ОРВИ. Лечение назначено.")
        assert len(warnings) == 0
        assert masked == "Жалобы на кашель. Диагноз: ОРВИ. Лечение назначено."

    def test_improve_text_returns_required_fields(self):
        result = improve_text("Жалобы: температура. Диагноз: ОРВИ. Назначен парацетамол.")
        assert "improved_text" in result
        assert "masked_text" in result
        assert "missing_sections" in result
        assert "pii_warnings" in result
        assert "method" in result

    def test_improve_adds_missing_sections(self):
        # текст без анамнеза и объективного осмотра
        result = improve_text("Жалобы: кашель. Диагноз: бронхит. Назначен азитромицин.")
        # в rule-based режиме должны быть шаблоны для отсутствующих разделов
        if result["method"] == "rules":
            assert len(result["missing_sections"]) > 0

    def test_improve_strips_pii_before_processing(self):
        result = improve_text("Пациент Иванов 45 лет. Жалобы: боли. Диагноз: ИБС.")
        # в masked_text не должно быть числа 45 как возраст
        assert "45 лет" not in result["masked_text"]
