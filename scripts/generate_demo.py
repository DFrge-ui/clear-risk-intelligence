"""Recreate the public synthetic CSV with a fixed seed. No personal/bank data."""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    rng = random.Random(42)
    categories = ["Technology", "Process", "Third party", "Compliance", "People"]
    units = ["Digital channels", "Payments", "Operations", "Client services", "Group support"]
    # Real names are display placeholders, never claims about these companies.
    # Keep the original random choices so amounts, dates and flags stay reproducible.
    company_placeholders = {
        "Digital channels": "Electroshield Samara",
        "Payments": "Samara BKK",
        "Operations": "Zhigulevskoye Pivo",
        "Client services": "Samara BKK",
        "Group support": "Electroshield Samara",
    }
    descriptions = {
        "Technology": ["Batch processing delay", "Service availability interruption", "Access provisioning exception"],
        "Process": ["Reconciliation mismatch", "Manual handover exception", "Duplicate processing detected"],
        "Third party": ["Supplier service interruption", "Vendor delivery delay", "External feed unavailable"],
        "Compliance": ["Control evidence missing", "Scheduled review incomplete", "Documentation gap"],
        "People": ["Training completion overdue", "Approval handover delay", "Capacity planning exception"],
    }
    rows = []
    for i in range(168):
        category = rng.choices(categories, weights=[30, 28, 18, 16, 8])[0]
        amount = rng.choice([0, 120, 350, 480, 750, 1200, 1850, 2400, 3200, 4500])
        if i in (3, 11, 26, 53, 80, 112):
            amount = rng.choice([12400, 18600, 24500, 31800])
        status = rng.choices(["Open", "In progress", "Resolved"], weights=[21, 24, 55])[0]
        severity = rng.choices(["Low", "Medium", "High", "Critical"], weights=[25, 46, 24, 5])[0]
        row = {"incident_id": f"SYN-{1001+i}", "occurred_on": (date(2026, 8, 3) + timedelta(days=rng.randrange(53))).isoformat(),
               "category": category, "business_unit": rng.choice(units), "severity": severity,
               "status": status, "loss_eur": f"{amount:.2f}", "owner": rng.choice(["Control team A", "Control team B", "Operations desk", ""]),
               "description": rng.choice(descriptions[category])}
        row["business_unit"] = company_placeholders[row["business_unit"]]
        # Small, intentional quality defects make the cleaning step inspectable.
        if i % 11 == 0:
            row["category"] = " " + category.lower() + " "
        if i % 13 == 0:
            row["occurred_on"] = date.fromisoformat(row["occurred_on"]).strftime("%d.%m.%Y")
        if i % 17 == 0:
            row["loss_eur"] = f"€ {amount:,.2f}"
        rows.append(row)
    rows.extend([rows[i].copy() for i in (8, 31, 65, 94)])
    for i, (key, value) in enumerate([("loss_eur", "not recorded"), ("occurred_on", "2026-02-30"), ("severity", "Urgent")]):
        row = rows[i+20].copy()
        row.update(incident_id=f"SYN-BAD-{i+1}")
        row[key] = value
        rows.append(row)
    (ROOT / "data").mkdir(exist_ok=True)
    with (ROOT / "data/demo_incidents.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Generated {len(rows)} synthetic source rows.")


if __name__ == "__main__":
    main()
