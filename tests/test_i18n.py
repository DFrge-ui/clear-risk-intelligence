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
