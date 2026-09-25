"""Optional real-browser check of language switching and German layouts."""
import argparse
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:5000")
    url = parser.parse_args().url.rstrip("/")
    out = ROOT / "work/browser-checks"
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1050}, reduced_motion="reduce")
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        # Explicit URL preference also has to survive subsequent language changes.
        page.goto(url + "/?lang=en#incidents", wait_until="networkidle")
        page.locator("#search").fill("Samara")
        page.locator("#filter-severity").select_option("High")
        expect(page.locator("#filter-notice")).to_be_visible()
        with page.expect_navigation(wait_until="networkidle"):
            page.locator("#language-select").select_option("de")
        expect(page.locator("html")).to_have_attribute("lang", "de")
        expect(page.locator("#search")).to_have_value("Samara")
        expect(page.locator("#filter-severity")).to_have_value("High")
        expect(page.locator("#incidents-body")).to_contain_text("Hoch")
        page.locator("#incidents-body .id-link").first.click()
        expect(page.locator("#detail-content")).to_contain_text("Zuständigkeit")
        page.get_by_role("button", name="Details schließen").click()
        page.get_by_role("button", name="Filter zurücksetzen", exact=True).click()
        expect(page.locator("#result-count")).to_have_text("168")
        page.get_by_role("button", name="CSV hochladen", exact=True).click()
        page.locator("#csv-file").set_input_files({"name": "bad.csv", "mimeType": "text/csv", "buffer": b"wrong,header\n1,2"})
        page.get_by_role("button", name="CSV prüfen", exact=True).click()
        expect(page.locator("#upload-error")).to_contain_text("Erforderliche Spalten fehlen")
        page.locator("#csv-file").set_input_files(str(ROOT / "data/demo_incidents.csv"))
        page.locator("#as-of").fill("2026-09-24")
        page.get_by_role("button", name="CSV prüfen", exact=True).click()
        expect(page.locator("#upload-preview-stage")).to_contain_text("Prüfung abgeschlossen.")
        page.get_by_role("button", name="Datensätze übernehmen", exact=True).click()
        expect(page.locator("#upload-dialog")).not_to_be_visible()
        page.locator('.nav-item[data-view="overview"]').click()
        expect(page.locator("#summary-text")).to_contain_text("Zum 2026-09-24")
        with page.expect_popup() as popup:
            page.get_by_role("link", name="Vollständigen Bericht öffnen").click()
        report = popup.value
        report.wait_for_load_state("networkidle")
        expect(report.locator("h1")).to_have_text("Ein klarer Blick auf die Daten.")
        expect(report.locator("body")).to_contain_text("387.930,00")
        report.screenshot(path=str(out / "report-de.png"), full_page=True)
        page.goto(url + "/#overview", wait_until="networkidle")
        expect(page.locator("html")).to_have_attribute("lang", "de")
        for width in (320, 390, 768, 1440):
            page.set_viewport_size({"width": width, "height": 1050})
            for view in ("overview", "incidents", "pipeline", "project"):
                page.locator(f'.nav-item[data-view="{view}"]').click()
                if not page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"):
                    page.screenshot(path=str(out / "overflow-de.png"), full_page=True)
                    raise AssertionError((width, view))
        page.locator('.nav-item[data-view="overview"]').click()
        page.screenshot(path=str(out / "overview-de.png"), full_page=True)
        for language in ("ru", "en", "de"):
            with page.expect_navigation(wait_until="networkidle"):
                page.locator("#language-select").select_option(language)
            expect(page.locator("html")).to_have_attribute("lang", language)
            expect(page.locator("#metric-total")).to_have_text("168")
            expect(page.locator("#dataset-name")).to_contain_text("demo_incidents")
        page.get_by_role("button", name="Beispiel laden", exact=True).click()
        expect(page.locator("#dataset-name")).to_have_text("Betrieb · September 2026")
        assert not errors, errors
        browser.close()
        print("Passed: DE/EN/RU switching, filters, active data, CSV errors and activation, German report, 16 responsive layouts.")


if __name__ == "__main__":
    main()
