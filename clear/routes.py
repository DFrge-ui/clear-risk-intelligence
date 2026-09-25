import csv
import io
from datetime import date
from pathlib import Path

from flask import Blueprint, Response, abort, current_app, jsonify, render_template, request, send_file, session
from werkzeug.utils import secure_filename

from . import repository
from .analysis import DISCLOSURE, RULES, enrich, summarize
from .pipeline import FIELDS, ValidationError, validate_csv
from .i18n import language, localize_summary

bp = Blueprint("web", __name__)


def current_dataset():
    dataset = repository.get_dataset(session.get("dataset", "demo"), session["owner"])
    if dataset is None or dataset["state"] != "active":
        session["dataset"] = "demo"
        dataset = repository.get_dataset("demo", session["owner"])
    return dataset


def filtered_analysis():
    dataset = current_dataset()
    all_records = enrich(dataset["records"], date.fromisoformat(dataset["as_of"]))
    filters = {key: request.args.get(key, "").strip()[:100] for key in ("q", "category", "severity", "status", "flagged")}
    records = all_records
    for key in ("category", "severity", "status"):
        if filters[key]:
            if key == "status" and filters[key] == "Active":
                records = [r for r in records if r["status"] != "Resolved"]
            else:
                records = [r for r in records if r[key] == filters[key]]
    if filters["flagged"] == "1":
        records = [r for r in records if r["flags"]]
    if filters["q"]:
        q = filters["q"].casefold()
        records = [r for r in records if q in " ".join(str(r[k]) for k in ("incident_id", "owner", "description", "business_unit")).casefold()]
    summary = summarize(records, date.fromisoformat(dataset["as_of"]))
    summary = localize_summary(summary, dataset["as_of"], language())
    metadata = {k: v for k, v in dataset.items() if k != "records"}
    return {"dataset": metadata, "records": records, "summary": summary, "filters": filters,
            "options": {k: sorted({r[k] for r in all_records} | ({"Active"} if k == "status" else set())) for k in ("category", "severity", "status")},
            "rules": RULES, "disclosure": DISCLOSURE}


@bp.get("/")
def index():
    return render_template("index.html", csrf=session["csrf"], today=date.today().isoformat())


@bp.get("/api/health")
def health():
    return jsonify(status="ok", application="CLEAR", version="1.0.0")


@bp.get("/api/dashboard")
def dashboard():
    return jsonify(filtered_analysis())


@bp.post("/api/uploads/preview")
def upload_preview():
    upload = request.files.get("file")
    if not upload or not upload.filename or not upload.filename.lower().endswith(".csv"):
        return jsonify(error="Choose a .csv file to continue."), 400
    if request.form.get("synthetic") != "true":
        return jsonify(error="Confirm that the file contains synthetic data only."), 400
    try:
        as_of = date.fromisoformat(request.form.get("as_of", ""))
        if not date(2000, 1, 1) <= as_of <= date.today():
            raise ValueError
    except ValueError:
        return jsonify(error="Choose an analysis date between 2000-01-01 and today."), 400
    try:
        result = validate_csv(upload.read(), as_of)
    except ValidationError as error:
        return jsonify(error=str(error)), 422
    filename = secure_filename(upload.filename)[:120] or "uploaded-data.csv"
    dataset_id = repository.save_dataset(session["owner"], filename, as_of, result)
    repository.prune(session["owner"], session.get("dataset", "demo"))
    return jsonify(id=dataset_id, name=filename, as_of=as_of.isoformat(), quality=result["quality"], sample=result["records"][:5])


@bp.post("/api/uploads/<dataset_id>/activate")
def upload_activate(dataset_id):
    if not repository.activate(dataset_id, session["owner"]):
        abort(404, "This upload is unavailable. Upload the CSV again.")
    session["dataset"] = dataset_id
    return jsonify(ok=True)


@bp.post("/api/demo")
def demo():
    session["dataset"] = "demo"
    return jsonify(ok=True)


@bp.get("/api/sample.csv")
def sample():
    return send_file(Path(current_app.root_path).parent / "data" / "demo_incidents.csv", as_attachment=True, download_name="clear_synthetic_incidents.csv")


def csv_safe(value):
    text = str(value)
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r", "\n")) else text


def csv_response(rows, fields, name):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: csv_safe(row.get(k, "")) for k in fields})
    return Response("\ufeff" + buffer.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f'attachment; filename="{name}"'})


@bp.get("/api/export/clean.csv")
def export_csv():
    data = filtered_analysis()
    rows = []
    for record in data["records"]:
        row = record.copy()
        row.update(loss_eur=f"{row['loss_cents'] / 100:.2f}", review_flags="; ".join(row["flag_labels"]),
                   analysis_date=data["dataset"]["as_of"], data_type="synthetic", project_type="AI-assisted learning project")
        rows.append(row)
    return csv_response(rows, [*FIELDS, "review_flags", "score", "source_row", "analysis_date", "data_type", "project_type"], "clear_reviewed_incidents.csv")


@bp.get("/api/export/issues.csv")
def export_issues():
    return csv_response(current_dataset()["quality"]["issues"], ["row", "type", "message"], "clear_validation_log.csv")


@bp.get("/api/export/report.json")
def export_json():
    response = jsonify(filtered_analysis())
    response.headers["Content-Disposition"] = 'attachment; filename="clear_management_report.json"'
    return response


@bp.get("/report")
def report():
    return render_template("report_localized.html", data=filtered_analysis())
