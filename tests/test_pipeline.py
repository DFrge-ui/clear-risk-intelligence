import csv
import io
from datetime import date

import pytest

from clear.pipeline import FIELDS, ValidationError, parse_money, validate_csv

AS_OF = date(2026, 9, 24)
BASE = dict(incident_id="INC-1", occurred_on="2026-09-01", category="Process", business_unit="Payments",
            severity="High", status="Open", loss_eur="1250.00", owner="Team A", description="Test incident")


def csv_bytes(rows, delimiter=","):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FIELDS, delimiter=delimiter)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


@pytest.mark.parametrize("value,cents", [("€ 1,250.50",125050),("1.250,50",125050),("1250,50",125050),
                                         ("0",0),("100.01",10001),("1,250",125000),("1.250",125000)])
def test_currency_normalization_preserves_cents(value,cents):
    assert parse_money(value) == cents


@pytest.mark.parametrize("value", ["-5", "NaN", "Infinity", "1e6", "12,3456", "1.2.3", "", "100000001", "=SUM(A1)"])
def test_bad_amounts_are_not_guessed(value):
    with pytest.raises(ValidationError):
        parse_money(value)


def test_cleaning_duplicates_conflicts_and_rejections():
    dirty = BASE | {"incident_id":" inc-1 ","occurred_on":"01.09.2026","category":" process ","severity":"high", "owner":""}
    duplicate = dirty.copy()
    conflict = dirty | {"loss_eur":"999.00"}
    invalid = BASE | {"incident_id":"INC-2","occurred_on":"2026-02-30"}
    result = validate_csv(csv_bytes([dirty,duplicate,conflict,invalid]), AS_OF)
    q = result["quality"]
    assert (q["total"],q["accepted"],q["duplicates"],q["rejected"],q["cleaned"]) == (4,1,1,2,1)
    assert q["total"] == q["accepted"] + q["duplicates"] + q["rejected"]
    assert result["records"][0]["source_row"] == 2
    assert result["records"][0]["owner"] == "Unassigned"
    assert result["records"][0]["loss_cents"] == 125000


def test_semicolon_bom_optional_fields_and_closed_alias():
    row = BASE | {"status":"Closed","loss_eur":"1.250,50"}
    result = validate_csv(csv_bytes([row],delimiter=";"),AS_OF)
    assert result["records"][0]["status"] == "Resolved"
    assert result["records"][0]["loss_cents"] == 125050


@pytest.mark.parametrize("raw", [b"", b"x,y\n1,2", b"\x00abc", b"\xff\xfe", b"incident_id,incident_id\nx,x"])
def test_invalid_schema_and_encoding(raw):
    with pytest.raises(ValidationError):
        validate_csv(raw,AS_OF)


def test_future_date_rejected_but_other_rows_survive():
    result=validate_csv(csv_bytes([BASE,BASE|{"incident_id":"INC-2","occurred_on":"2026-09-25"}]),AS_OF)
    assert result["quality"]["rejected"] == 1
    assert "later than" in result["quality"]["issues"][0]["message"]


def test_column_mismatch_is_a_logged_rejection():
    content=csv_bytes([BASE])+b"wrong,columns\r\n"
    result=validate_csv(content,AS_OF)
    assert result["quality"]["rejected"] == 1


def test_row_limit():
    rows=[BASE|{"incident_id":f"INC-{i}"} for i in range(10001)]
    with pytest.raises(ValidationError,match="10,000"):
        validate_csv(csv_bytes(rows),AS_OF)


def test_duplicate_comparison_ignores_source_row():
    result=validate_csv(csv_bytes([BASE,BASE,BASE]),AS_OF)
    assert result["quality"]["duplicates"] == 2
