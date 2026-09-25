"""Explainable demonstration rules; these are not RBI policies or a risk model."""
from collections import Counter, defaultdict
from datetime import date, timedelta
from statistics import quantiles

DISCLOSURE = "AI-assisted learning project by Dmitrii Kataev. Synthetic data only. Company names are display placeholders: all incidents and amounts are fictional and unrelated to the named companies' actual activities. Independent portfolio demo; not affiliated with or endorsed by RBI or the named companies. Review flags are illustrative, not regulatory or bank-approved decisions."

RULES = [
    {"id": "critical", "label": "Critical severity", "description": "Active incident with Critical severity.", "weight": 40},
    {"id": "high_loss", "label": "High recorded loss", "description": "Recorded loss is at least EUR 10,000, regardless of status.", "weight": 25},
    {"id": "aging", "label": "Aging case", "description": "Active incident is more than 14 days old on the analysis date.", "weight": 15},
    {"id": "unassigned", "label": "No owner", "description": "Active incident has no assigned owner.", "weight": 10},
    {"id": "outlier", "label": "Loss outlier", "description": "Loss exceeds Q3 + 1.5 × IQR within its category (at least 8 records; IQR > 0).", "weight": 10},
]


def enrich(records, as_of):
    groups = defaultdict(list)
    for row in records:
        groups[row["category"]].append(row["loss_cents"])
    thresholds = {}
    for category, losses in groups.items():
        if len(losses) >= 8:
            q1, _, q3 = quantiles(losses, n=4, method="inclusive")
            if q3 > q1:
                thresholds[category] = q3 + 1.5 * (q3 - q1)
    enriched = []
    for original in records:
        row = original.copy()
        age = (as_of - date.fromisoformat(row["occurred_on"])).days
        active = row["status"] != "Resolved"
        conditions = {"critical": active and row["severity"] == "Critical", "high_loss": row["loss_cents"] >= 1000000,
                      "aging": active and age > 14, "unassigned": active and row["owner"] == "Unassigned",
                      "outlier": row["category"] in thresholds and row["loss_cents"] > thresholds[row["category"]]}
        flags = [rule for rule in RULES if conditions[rule["id"]]]
        row.update(age_days=age, flags=[r["id"] for r in flags], flag_labels=[r["label"] for r in flags],
                   score=sum(r["weight"] for r in flags), loss_eur=row["loss_cents"] / 100,
                   outlier_threshold_eur=round(thresholds[row["category"]] / 100, 2) if row["category"] in thresholds else None)
        enriched.append(row)
    return sorted(enriched, key=lambda r: (-r["score"], -r["loss_cents"], r["incident_id"]))


def summarize(records, as_of):
    active = [r for r in records if r["status"] != "Resolved"]
    flagged = [r for r in records if r["flags"]]
    total_loss = sum(r["loss_cents"] for r in records) / 100
    active_loss = sum(r["loss_cents"] for r in active) / 100
    categories = []
    for category in sorted({r["category"] for r in records}):
        rows = [r for r in records if r["category"] == category]
        categories.append({"name": category, "count": len(rows), "loss": sum(r["loss_cents"] for r in rows) / 100,
                           "flagged": sum(bool(r["flags"]) for r in rows)})
    categories.sort(key=lambda r: -r["loss"])
    trend = []
    monday = as_of - timedelta(days=as_of.weekday())
    for offset in range(7, -1, -1):
        start = monday - timedelta(weeks=offset)
        end = min(start + timedelta(days=6), as_of)
        rows = [r for r in records if start.isoformat() <= r["occurred_on"] <= end.isoformat()]
        trend.append({"start": start.isoformat(), "end": end.isoformat(), "count": len(rows), "flagged": sum(bool(r["flags"]) for r in rows), "partial": end < start + timedelta(days=6)})
    aging = sum("aging" in r["flags"] for r in records)
    critical = sum("critical" in r["flags"] for r in records)
    unassigned = sum("unassigned" in r["flags"] for r in records)
    metrics = {"total": len(records), "active": len(active), "flagged": len(flagged), "loss": total_loss,
               "active_loss": active_loss, "resolved": len(records) - len(active), "aging": aging,
               "critical": critical, "unassigned": unassigned}
    if not records:
        narrative = "No incidents match these filters. Broaden the selection to generate a management summary."
    else:
        top = categories[0]
        narrative = (f"As of {as_of:%d %b %Y}, the selected dataset contains {len(records)} incidents, "
                     f"of which {len(active)} remain active. Recorded loss totals EUR {total_loss:,.2f}. "
                     f"{len(flagged)} incidents trigger at least one review rule; {critical} active cases have critical severity. "
                     f"{top['name']} accounts for the largest recorded loss (EUR {top['loss']:,.2f}). "
                     f"{aging} active cases are older than 14 days and {unassigned} have no owner.")
    actions = []
    if critical:
        actions.append(f"Review the {critical} active critical-severity cases and confirm the next action.")
    if unassigned:
        actions.append(f"Assign an owner to {unassigned} active cases.")
    if aging:
        actions.append(f"Check progress on {aging} active cases older than 14 days.")
    if flagged and not actions:
        actions.append("Review the flagged loss amounts against the source records.")
    if records and not actions:
        actions.append("No demonstration rules triggered. Continue routine review; this is not a guarantee of low risk.")
    return {"metrics": metrics, "categories": categories, "trend": trend, "narrative": narrative, "actions": actions,
            "status_counts": dict(Counter(r["status"] for r in records))}
