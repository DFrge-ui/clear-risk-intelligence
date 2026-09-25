from datetime import date

from clear.analysis import enrich, summarize

BASE = dict(incident_id="INC-1", occurred_on="2026-09-01", category="Process", business_unit="Payments",
            severity="Critical", status="Open", loss_cents=1000000, owner="Unassigned", description="Test", source_row=2)
AS_OF = date(2026,9,24)


def test_rule_boundaries_and_resolved_cases():
    rows=[BASE,BASE|{"incident_id":"INC-2","status":"Resolved"},
          BASE|{"incident_id":"INC-3","severity":"Low","occurred_on":"2026-09-10","owner":"Team A","loss_cents":999999}]
    result={r["incident_id"]:r for r in enrich(rows,AS_OF)}
    assert result["INC-1"]["score"] == 90
    assert set(result["INC-1"]["flags"]) == {"critical","high_loss","aging","unassigned"}
    assert result["INC-2"]["flags"] == ["high_loss"]
    assert result["INC-3"]["flags"] == []  # Exactly 14 days is not older than 14 days.


def test_outlier_uses_category_and_minimum_sample_size():
    rows=[BASE|{"incident_id":f"P-{i}","loss_cents":value,"status":"Resolved"} for i,value in enumerate([100,200,300,400,500,600,700,20000])]
    result=enrich(rows,AS_OF)
    assert result[0]["flags"] == ["outlier"]
    assert result[0]["outlier_threshold_eur"] == 11.5
    assert not any("outlier" in r["flags"] for r in enrich(rows[:7],AS_OF))
    assert not any("outlier" in r["flags"] for r in enrich([r|{"loss_cents":100} for r in rows],AS_OF))


def test_aggregates_and_partial_week():
    result=summarize(enrich([BASE, BASE|{"incident_id":"INC-2","status":"Resolved","loss_cents":500}],AS_OF),AS_OF)
    assert result["metrics"]["loss"] == 10005
    assert result["metrics"]["active_loss"] == 10000
    assert result["metrics"]["active"] == 1
    assert result["trend"][-1]["partial"]
    assert result["trend"][-1]["end"] == "2026-09-24"
    assert sum(w["count"] for w in result["trend"]) == 2


def test_empty_selection_has_no_invented_actions():
    result=summarize([],AS_OF)
    assert result["metrics"]["total"] == 0
    assert result["actions"] == []
    assert "No incidents" in result["narrative"]
