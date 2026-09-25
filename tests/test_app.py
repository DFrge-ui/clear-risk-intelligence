import csv
import io

from test_pipeline import BASE, csv_bytes


def preview(client,csrf,rows=None,**overrides):
    data={"file":(io.BytesIO(csv_bytes(rows or [BASE])),"test.csv"),"synthetic":"true","as_of":"2026-09-24"}
    data.update(overrides)
    return client.post("/api/uploads/preview",data=data,headers=csrf)


def test_demo_is_consistent(client):
    response=client.get("/api/dashboard")
    assert response.status_code == 200
    data=response.json
    assert data["dataset"]["quality"]["total"] == 175
    assert data["summary"]["metrics"]["total"] == 168
    assert data["dataset"]["quality"]["duplicates"] == 4
    assert data["dataset"]["quality"]["rejected"] == 3
    assert data["summary"]["metrics"]["loss"] == sum(r["loss_cents"] for r in data["records"])/100
    assert "AI-assisted" in data["disclosure"]


def test_upload_preview_is_non_destructive_then_activate(client,csrf):
    response=preview(client,csrf)
    assert response.status_code == 200
    assert client.get("/api/dashboard").json["dataset"]["is_demo"]
    assert client.post(f"/api/uploads/{response.json['id']}/activate",headers=csrf).status_code == 200
    data=client.get("/api/dashboard").json
    assert data["summary"]["metrics"]["total"] == 1
    assert not data["dataset"]["is_demo"]
    assert client.post("/api/demo",headers=csrf).status_code == 200
    assert client.get("/api/dashboard").json["dataset"]["is_demo"]


def test_upload_and_activation_cannot_cross_sessions(app,client,csrf):
    uploaded=preview(client,csrf).json
    other=app.test_client();other.get("/")
    with other.session_transaction() as session:
        other_csrf={"X-CSRF-Token":session["csrf"]}
    assert other.post(f"/api/uploads/{uploaded['id']}/activate",headers=other_csrf).status_code == 404
    assert other.get("/api/dashboard").json["dataset"]["is_demo"]


def test_csrf_and_synthetic_confirmation_required(client,csrf):
    assert client.post("/api/demo").status_code == 403
    assert preview(client,csrf,synthetic="false").status_code == 400


def test_upload_errors_leave_active_dataset_unchanged(client,csrf):
    assert preview(client,csrf,file=(io.BytesIO(b"bad"),"bad.csv")).status_code == 422
    assert preview(client,csrf,file=(io.BytesIO(b"bad"),"bad.exe")).status_code == 400
    assert preview(client,csrf,as_of="2099-01-01").status_code == 400
    oversized=client.post("/api/uploads/preview",data={"file":(io.BytesIO(b"x"*(2*1024*1024)),"big.csv")},headers=csrf)
    assert oversized.status_code == 413
    assert client.get("/api/dashboard").json["dataset"]["is_demo"]


def test_filtered_exports_match_dashboard(client):
    query="?severity=High&status=Active&flagged=1"
    data=client.get("/api/dashboard"+query).json
    assert all(r["severity"] == "High" and r["status"] != "Resolved" and r["flags"] for r in data["records"])
    exported=client.get("/api/export/clean.csv"+query).data.decode("utf-8-sig")
    rows=list(csv.DictReader(io.StringIO(exported)))
    assert len(rows) == data["summary"]["metrics"]["total"]
    assert {r["incident_id"] for r in rows} == {r["incident_id"] for r in data["records"]}
    assert all(r["data_type"] == "synthetic" for r in rows)
    assert client.get("/api/export/report.json"+query).json["summary"] == data["summary"]
    report=client.get("/report"+query)
    assert report.status_code == 200
    assert "status = Active" in report.text


def test_outlier_flags_do_not_change_when_filtering(client):
    data=client.get("/api/dashboard").json
    flags={r["incident_id"]:r["flags"] for r in data["records"]}
    selection=client.get("/api/dashboard?severity=High").json
    assert all(r["flags"] == flags[r["incident_id"]] for r in selection["records"])


def test_exports_escape_spreadsheet_formulas_and_html(client,csrf):
    row=BASE|{"owner":"=HYPERLINK(\"https://example.com\")","description":"<script>alert(1)</script>"}
    uploaded=preview(client,csrf,[row]).json
    client.post(f"/api/uploads/{uploaded['id']}/activate",headers=csrf)
    exported=client.get("/api/export/clean.csv").data.decode("utf-8-sig")
    parsed=list(csv.DictReader(io.StringIO(exported)))
    assert parsed[0]["owner"].startswith("'=")
    assert '<script>alert(1)</script>' not in client.get("/report").text


def test_security_headers_and_missing_route(client):
    response=client.get("/")
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "script-src 'self'" in response.headers["Content-Security-Policy"]
    assert "no-store" in response.headers["Cache-Control"]
    assert client.get("/missing").status_code == 404


def test_empty_filter_result_has_valid_reports(client):
    data=client.get("/api/dashboard?q=no-matching-incident-here").json
    assert data["summary"]["metrics"]["total"] == 0
    assert client.get("/report?q=no-matching-incident-here").status_code == 200


def test_many_previews_cannot_evict_current_dataset(client,csrf):
    active=preview(client,csrf).json["id"]
    client.post(f"/api/uploads/{active}/activate",headers=csrf)
    for _ in range(22):
        assert preview(client,csrf).status_code == 200
    assert client.get("/api/dashboard").json["dataset"]["id"] == active
