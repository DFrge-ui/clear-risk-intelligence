# Local API

Base address: `http://127.0.0.1:5000`. JSON endpoints are under `/api/`. This is a local browser-session API, not a public service.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Application name, version and process status |
| GET | `/api/dashboard` | Active dataset metadata, filtered records, aggregates, rules |
| POST | `/api/uploads/preview` | Multipart CSV validation and session-owned preview |
| POST | `/api/uploads/<id>/activate` | Select an owned preview/previous dataset |
| POST | `/api/demo` | Return the current browser session to the seeded demo |
| GET | `/api/sample.csv` | Download the original synthetic sample with deliberate defects |
| GET | `/api/export/clean.csv` | All selected accepted records with review flags |
| GET | `/api/export/report.json` | Complete structured analysis for selected records |
| GET | `/api/export/issues.csv` | Full-dataset validation log, independent of filters |
| GET | `/report` | Server-rendered printable management report |

## Filtering

`/api/dashboard`, both record/report exports, and `/report` accept identical query arguments:

- `q`: case-insensitive substring of ID, description, business unit or owner.
- `category`: exact category label.
- `severity`: Low, Medium, High or Critical.
- `status`: Open, In progress, Resolved, or **Active** (Open + In progress).
- `flagged=1`: records with one or more review flags.

Example: `/api/dashboard?severity=Critical&status=Active`.

No matches is a valid result: zero metrics, empty records, no invented review actions. Outlier thresholds are computed on the full accepted dataset before these filters.

## Mutations

Visit `/` to establish the session, keep its cookie, and read the CSRF token from `<meta name="csrf-token">`. Send it as `X-CSRF-Token` on every POST. A script that simply needs automation should use `python -m clear.cli` instead.

The preview accepts multipart fields:

- `file`: UTF-8 `.csv` file.
- `as_of`: ISO analysis date, not in the future.
- `synthetic`: the string `true` (explicit synthetic-data confirmation).

Success returns an opaque dataset `id`, normalized filename, analysis date, `quality` and five example accepted records. The active dashboard remains unchanged. The activation endpoint checks session ownership before changing the active dataset.

## Errors

All API errors contain `{"error": "Human-readable explanation"}`.

| HTTP status | Meaning |
| --- | --- |
| 400 | Missing file, wrong extension, invalid analysis date, or missing synthetic confirmation |
| 403 | CSRF token missing or invalid |
| 404 | Dataset absent/not owned, or endpoint unknown |
| 413 | Whole request exceeds 2 MiB |
| 422 | CSV cannot produce a valid preview |
| 500 | Unexpected server failure; details are logged locally, not returned to the browser |

The health endpoint confirms that the process responds; it is not a full dependency/readiness probe. The application does not expose arbitrary SQL, paths, filesystem uploads, or an authentication system.
