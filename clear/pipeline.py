"""Deterministic CSV validation. Invalid records never enter the accepted data."""
import csv
import io
import re
from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

REQUIRED = ("incident_id", "occurred_on", "category", "business_unit", "severity", "status", "loss_eur")
OPTIONAL = ("owner", "description")
FIELDS = REQUIRED + OPTIONAL
MAX_ROWS = 10000
STATUSES = {"open": "Open", "in progress": "In progress", "in_progress": "In progress", "resolved": "Resolved", "closed": "Resolved"}
SEVERITIES = {key.lower(): key for key in ("Low", "Medium", "High", "Critical")}
CATEGORIES = {key.lower(): key for key in ("Process", "Technology", "Third party", "People", "Compliance")}


class ValidationError(ValueError):
    pass


def clean_text(value):
    return " ".join(value.strip().split())


def parse_date(value):
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValidationError("Use YYYY-MM-DD, DD.MM.YYYY or DD/MM/YYYY for occurred_on.")


def parse_money(value):
    value = value.replace("€", "").replace("EUR", "").replace("eur", "").replace(" ", "").replace("\u00a0", "")
    if re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d{1,2})?", value):
        value = value.replace(",", "")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d{1,2})?", value):
        value = value.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d+(,\d{1,2})", value):
        value = value.replace(",", ".")
    if not re.fullmatch(r"\d+(\.\d{1,2})?", value):
        raise ValidationError("loss_eur must be a non-negative amount with at most two decimal places.")
    try:
        amount = Decimal(value)
        if amount > Decimal("100000000"):
            raise ValidationError("loss_eur exceeds the demo limit of EUR 100,000,000.")
        return int(amount * 100)
    except InvalidOperation:
        raise ValidationError("Invalid loss_eur amount.") from None


def validate_csv(content: bytes, as_of: date):
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValidationError("Save your CSV with UTF-8 encoding, then upload it again.") from None
    if not text.strip() or "\x00" in text:
        raise ValidationError("The file is empty or contains binary data.")
    if any(ord(c) < 32 and c not in "\n\r\t" for c in text):
        raise ValidationError("The file contains unsupported control characters.")
    first = text.splitlines()[0]
    delimiter = ";" if first.count(";") > first.count(",") else ","
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
    try:
        raw_headers = next(reader)
        headers = [re.sub(r"[\s-]+", "_", h.strip().lower()) for h in raw_headers]
        if len(headers) != len(set(headers)):
            raise ValidationError("Duplicate column names were found. Each column must be unique.")
        missing = sorted(set(REQUIRED) - set(headers))
        if missing:
            raise ValidationError("Missing required columns: " + ", ".join(missing) + ". Download the sample CSV for the expected format.")
        if len(headers) > 30:
            raise ValidationError("Too many columns. Use the sample schema.")
        unknown = sorted(set(headers) - set(FIELDS))
        accepted, issues, seen = [], [], {}
        counts = Counter()
        changes = Counter()
        for row_number, values in enumerate(reader, start=2):
            if not values or not any(v.strip() for v in values):
                counts["blank"] += 1
                continue
            counts["total"] += 1
            if counts["total"] > MAX_ROWS:
                raise ValidationError("The demo supports up to 10,000 non-empty rows per file.")
            if len(values) != len(headers):
                counts["rejected"] += 1
                issues.append({"row": row_number, "type": "rejected", "message": "Column count does not match the header."})
                continue
            original = dict(zip(headers, values))
            row = {key: clean_text(original.get(key, "")) for key in FIELDS}
            row_changes = set()
            if any(original.get(k, "") != row[k] for k in FIELDS):
                row_changes.add("Whitespace normalized")
            try:
                if any(len(v) > 500 for v in row.values()):
                    raise ValidationError("A cell exceeds the 500-character limit.")
                if any(not row[key] for key in REQUIRED):
                    raise ValidationError("A required value is missing.")
                if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", row["incident_id"]):
                    raise ValidationError("incident_id must contain 1–40 letters, digits, underscores or hyphens.")
                normalized_id = row["incident_id"].upper()
                if normalized_id != row["incident_id"]:
                    row_changes.add("Incident IDs standardized")
                row["incident_id"] = normalized_id
                parsed = parse_date(row["occurred_on"])
                if parsed > as_of:
                    raise ValidationError("Incident date is later than the analysis date.")
                if parsed.year < 2000:
                    raise ValidationError("Incident date must be in 2000 or later.")
                if parsed.isoformat() != row["occurred_on"]:
                    row_changes.add("Dates standardized")
                row["occurred_on"] = parsed.isoformat()
                severity = SEVERITIES.get(row["severity"].lower())
                status = STATUSES.get(row["status"].lower())
                if not severity:
                    raise ValidationError("severity must be Low, Medium, High or Critical.")
                if not status:
                    raise ValidationError("status must be Open, In progress or Resolved (Closed is also accepted).")
                category = CATEGORIES.get(row["category"].lower(), row["category"])
                if (severity, status, category) != (row["severity"], row["status"], row["category"]):
                    row_changes.add("Labels standardized")
                row.update(severity=severity, status=status, category=category)
                cents = parse_money(row["loss_eur"])
                if row["loss_eur"] != f"{cents / 100:.2f}":
                    row_changes.add("Amounts standardized")
                row.pop("loss_eur")
                row["loss_cents"] = cents
                if not row["owner"] or row["owner"].lower() == "unassigned":
                    if row["owner"] != "Unassigned":
                        row_changes.add("Missing owners marked")
                    row["owner"] = "Unassigned"
                if row["incident_id"] in seen:
                    if seen[row["incident_id"]] == row:
                        counts["duplicates"] += 1
                        issues.append({"row": row_number, "type": "duplicate", "message": f"Exact duplicate of {row['incident_id']} removed."})
                    else:
                        counts["rejected"] += 1
                        issues.append({"row": row_number, "type": "rejected", "message": f"Conflicting duplicate ID {row['incident_id']}; first valid record retained."})
                    continue
                seen[row["incident_id"]] = row.copy()
                row["source_row"] = row_number
                accepted.append(row)
                if row_changes:
                    counts["cleaned"] += 1
                    changes.update(row_changes)
            except ValidationError as error:
                counts["rejected"] += 1
                issues.append({"row": row_number, "type": "rejected", "message": str(error)})
    except csv.Error as error:
        raise ValidationError("Malformed CSV. Check quotation marks and separators.") from error
    if not accepted:
        raise ValidationError("No valid records found. " + (issues[0]["message"] if issues else "Add at least one incident."))
    return {
        "records": accepted,
        "quality": {"total": counts["total"], "accepted": len(accepted), "rejected": counts["rejected"],
                    "duplicates": counts["duplicates"], "cleaned": counts["cleaned"], "blank": counts["blank"],
                    "changes": dict(changes), "ignored_columns": unknown,
                    "headers_normalized": headers != raw_headers, "delimiter": delimiter,
                    "issues": issues, "acceptance_rate": round(len(accepted) / counts["total"] * 100, 1)},
    }
