import json
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "browser-checks"
OUT.mkdir(parents=True, exist_ok=True)
PROJECT = ROOT
import argparse
parser = argparse.ArgumentParser(description="Optional browser integration smoke test")
parser.add_argument("--url", default="http://127.0.0.1:5000")
BASE_URL = parser.parse_args().url.rstrip("/")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width":1440,"height":1050}, device_scale_factor=1)
        errors=[]
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.on("console",lambda m:errors.append(m.text) if m.type == "error" else None)
        page.goto(BASE_URL,wait_until="networkidle")
        expect(page.locator("#metric-total")).to_have_text("168")
        page.screenshot(path=str(OUT/"desktop.png"),full_page=True)
        assert page.locator("#app-error").is_hidden()
        page.get_by_role("button",name="Review critical cases").click()
        expect(page.locator("#filter-status")).to_have_value("Active")
        assert page.locator("#filter-severity").input_value()=="Critical"
        assert page.locator("#incidents-body tr").count()>0
        page.locator("#incidents-body .id-link").first.click()
        assert page.locator("#detail-dialog").is_visible()
        assert "Critical severity" in page.locator("#detail-content").inner_text()
        page.screenshot(path=str(OUT/"detail.png"))
        page.get_by_role("button",name="Close details").click()
        page.get_by_role("button",name="Reset filters",exact=True).click()
        expect(page.locator("#result-count")).to_have_text("168")
        page.get_by_role("button",name="Next",exact=True).click()
        assert "16–30" in page.locator("#page-status").inner_text()
        page.locator("#search").fill("no-such-incident-92384")
        expect(page.locator("#result-count")).to_have_text("0")
        assert "No matching incidents" in page.locator("#incidents-body").inner_text()
        page.get_by_role("button",name="Reset filters",exact=True).click()
        expect(page.locator("#result-count")).to_have_text("168")
        page.get_by_role("button",name="Data pipeline",exact=True).click()
        page.screenshot(path=str(OUT/"pipeline.png"),full_page=True)
        page.get_by_role("button",name="Upload CSV",exact=True).click()
        page.locator("#csv-file").set_input_files(str(PROJECT/"data/demo_incidents.csv"))
        page.locator("#as-of").fill("2026-09-24")
        page.get_by_role("button",name="Validate CSV",exact=True).click()
        page.get_by_role("button",name="Apply accepted records").wait_for()
        assert "168" in page.locator("#upload-preview-stage").inner_text()
        page.screenshot(path=str(OUT/"upload.png"))
        page.get_by_role("button",name="Apply accepted records").click()
        expect(page.locator("#upload-dialog")).not_to_be_visible()
        assert page.locator("#dataset-name").inner_text()=="demo_incidents.csv"
        page.get_by_role("button",name="Restore sample").click()
        expect(page.locator("#dataset-name")).to_contain_text("Operations")
        page.get_by_role("button",name="Behind the project",exact=True).click()
        page.screenshot(path=str(OUT/"project.png"),full_page=True)
        page.get_by_role("button",name="Overview",exact=True).click()
        with page.expect_popup() as popup_info:
            page.get_by_role("link",name="Open full report").click()
        report=popup_info.value
        report.wait_for_load_state("networkidle")
        assert report.locator("h1").inner_text()=="A clear view of the evidence."
        report.screenshot(path=str(OUT/"report.png"),full_page=True)
        report.pdf(path=str(OUT/"report-qa.pdf"),format="A4",print_background=True)
        mobile=browser.new_page(viewport={"width":390,"height":844},device_scale_factor=1,is_mobile=True,has_touch=True)
        mobile.goto(BASE_URL,wait_until="networkidle")
        expect(mobile.locator("#metric-total")).to_have_text("168")
        mobile.screenshot(path=str(OUT/"mobile.png"),full_page=True)
        for view in ["overview","incidents","pipeline","project"]:
            mobile.locator(f'.nav-item[data-view="{view}"]').click()
            assert mobile.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"), f"Horizontal overflow: {view}"
        mobile.get_by_role("button",name="Upload CSV",exact=True).click()
        mobile.screenshot(path=str(OUT/"mobile-upload.png"),full_page=True)
        mobile.get_by_role("button",name="Close upload").click()
        mobile.emulate_media(reduced_motion="reduce")
        mobile.locator('.nav-item[data-view="overview"]').click()
        assert mobile.locator(".chart-line").evaluate("e => getComputedStyle(e).strokeDashoffset") == "0px"
        print(json.dumps({"browser_errors":errors,"checks":"navigation, filters, empty state, pagination, detail, CSV validation/activation, reset, report, mobile overflow, reduced motion","font_magic":(PROJECT/'clear/static/fonts/manrope-latin.woff2').read_bytes()[:4].hex()},indent=2))
        browser.close()
        if errors: raise AssertionError(errors)


if __name__=="__main__":main()
