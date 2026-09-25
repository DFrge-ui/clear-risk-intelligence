import re

import pytest

from clear.i18n import messages_for


def test_russian_ui_preference_and_invalid_language_fallback(client):
    client.set_cookie("clear_language", "ru")
    page=client.get("/")
    assert '<html lang="ru">' in page.text
    assert "Обработка данных" in page.text
    assert 'id="language-select"' in page.text
    client.set_cookie("clear_language", "unsupported")
    assert '<html lang="en">' in client.get("/").text


def test_localization_preserves_facts_and_filter_values(client):
    english=client.get("/api/dashboard?severity=High&lang=en").json
    russian=client.get("/api/dashboard?severity=High&lang=ru").json
    assert english["records"] == russian["records"]
    assert english["summary"]["metrics"] == russian["summary"]["metrics"]
    assert english["summary"]["categories"] == russian["summary"]["categories"]
    assert russian["summary"]["narrative"].startswith("На ")
    assert russian["filters"]["severity"] == "High"


def test_localized_report_and_project_disclosure(client):
    report=client.get("/report?lang=ru&severity=Critical")
    assert report.status_code == 200
    assert "Приоритетные случаи" in report.text
    assert "Учебный проект" in report.text
    assert "Важность = Критическая" in report.text
    assert "Компания / подразделение" not in report.text  # No invented table column.
    assert "Company names are placeholders" in client.get("/").text


def test_german_ui_report_and_preference(client):
    client.set_cookie("clear_language", "de")
    page = client.get("/").text
    assert '<html lang="de">' in page
    assert "Datenaufbereitung" in page
    assert 'value="de" selected' in page
    report = client.get("/report?severity=Critical").text
    assert "Priorisierte Prüfliste" in report
    assert "KI-unterstütztes Lernprojekt" in report
    assert "Schweregrad = Kritisch" in report
    assert '<html lang="en">' in client.get("/?lang=en").text


@pytest.mark.parametrize("filters", ["", "severity=Critical", "q=missing-id-999999", "status=Resolved"])
def test_german_analysis_preserves_facts(client, filters):
    english = client.get(f"/api/dashboard?lang=en&{filters}").json
    german = client.get(f"/api/dashboard?lang=de&{filters}").json
    assert english["records"] == german["records"]
    assert english["filters"] == german["filters"]
    assert english["summary"]["metrics"] == german["summary"]["metrics"]
    assert english["summary"]["categories"] == german["summary"]["categories"]
    assert english["summary"]["narrative"] != german["summary"]["narrative"]
    if german["summary"]["metrics"]["total"]:
        assert german["summary"]["narrative"].startswith("Zum ")
        assert german["summary"]["actions"]
    else:
        assert german["summary"]["narrative"].startswith("Keine Vorfälle")


def test_german_catalog_coverage_and_placeholders():
    german = messages_for("de")
    assert german.keys() == messages_for("ru").keys()
    for source, translation in german.items():
        assert translation.strip()
        assert set(re.findall(r"\{\w+\}", source)) == set(re.findall(r"\{\w+\}", translation)), source


def test_german_report_number_format(client):
    assert "387.930,00" in client.get("/report?lang=de").text
import re

import pytest

from clear.i18n import messages_for

