# Validation evidence

Checks performed on **24–25 September 2026**, on Windows with **Python 3.14.6**, Flask **3.1.3**, Waitress **3.0.2**, pytest **9.1.1**, and Playwright **1.63.0** using installed Google Chrome **153.0.8010.53**.

## Python checks

**54 tests passed.** The suite covers:

- Accepted money formats, integer-cent precision and rejected malformed/nonfinite/negative values.
- Header/encoding failures, future dates, invalid record lengths, row limit.
- Normalized exact duplicates versus conflicting IDs; source-row preservation.
- Critical, loss, aging and owner rules; exact 14-day and EUR 10,000 boundaries.
- Category IQR outliers, minimum sample size and zero-IQR behavior.
- Empty selections, total/active loss and partial-week buckets.
- Preview without replacing the active dataset, activation and reset.
- Cross-session activation rejection, CSRF and synthetic-data confirmation.
- Oversized uploads and invalid uploads leaving current data intact.
- Filtered CSV/JSON matching the dashboard, stable flags across filters, HTML/formula escaping.
- Active dataset preservation when more than 20 previews are created.
- Browser-independent CLI output, invalid input and overwrite refusal.
- English/Russian/German language selection, fallback, translated reports and unchanged underlying metrics and record values. German checks include empty selections, number formatting, catalog coverage and interpolation placeholders.

## Browser integration

Completed a real Chromium browser flow at desktop **1440 × 1050** and mobile emulation **390 × 844**:

- Overview loads the seeded 168 accepted incidents without console or script errors.
- Critical-case shortcut selects Critical + Active.
- Details show the matching evidence; dialog closes correctly.
- Reset, pagination, search and a no-results selection work.
- Sample CSV validates with 168 accepted records, four duplicates and three rejected rows.
- Applying the preview changes the dataset; reset restores the sample.
- Project notes and pipeline views render.
- Report opens, renders and produces a PDF through browser printing.
- Mobile navigation works without horizontal page overflow; tables have their own scroll area.
- Reduced-motion media preference disables chart drawing animation.

Optional browser test (requires Chrome and a running app):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-browser.txt
.\.venv\Scripts\python.exe scripts/browser_smoke.py --url http://127.0.0.1:5000
```

The script writes review screenshots to `work/browser-checks/`. This optional tooling is not required by the application.

Additional responsive checks passed in all four views at widths **320, 390, 768, 1024 and 1440 pixels** (20 view/width combinations).

The 25 September bilingual update also passed an English → Russian → English browser flow: filters and the active section survived switching, Russian CSV errors and previews rendered, the Russian report opened, and the language preference survived reload. All four Russian views passed horizontal-overflow checks at **320, 390, 768 and 1440 pixels**. The updated English browser smoke test passed again with no browser errors.

The German update passed the same four viewport widths across all four views, CSV validation errors and activation, German report rendering, persistent language selection, explicit URL language changes, and switching DE → RU → EN → DE while preserving the active uploaded dataset. Run `python scripts/language_smoke.py --url http://127.0.0.1:5000` with Chrome and the optional browser dependencies installed to reproduce this check.

## Accessibility spot check

axe-core **4.10.3**, WCAG 2 A/AA and 2.1 AA rule tags: **zero automated violations** in the four desktop views and the initial upload dialog after contrast fixes. Also checked visible keyboard focus, native modal dialogs, table headings, labels, chart text alternatives and reduced motion. This is a bounded automated check, not a claim of comprehensive WCAG certification or screen-reader testing.

## Fresh Windows setup

Extracted a release candidate into a separate folder without an existing virtual environment. `run_windows.bat --help` successfully created the environment, installed the pinned runtime dependencies and forwarded arguments to the app. In that new environment, verified application/database initialization, health endpoint, 168-record dashboard, report rendering, and CLI report generation.

The working local preview uses Waitress on loopback. Public hosting, macOS/Linux execution, other Python versions, production load, real banking data and browser combinations other than the tested Chrome installation have not been validated.
