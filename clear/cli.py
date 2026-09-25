"""Run the same pipeline without a browser: python -m clear.cli --help."""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

from .analysis import DISCLOSURE, RULES, enrich, summarize
from .pipeline import ValidationError, validate_csv


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate synthetic incident CSV and create a reproducible JSON report.")
    parser.add_argument("input", type=Path, help="UTF-8 CSV with synthetic incident data")
    parser.add_argument("--as-of", required=True, type=date.fromisoformat, help="Analysis date (YYYY-MM-DD)")
    parser.add_argument("--output", required=True, type=Path, help="New JSON report file; existing files are not overwritten")
    args = parser.parse_args(argv)
    try:
        if not date(2000, 1, 1) <= args.as_of <= date.today():
            raise ValidationError("Choose an analysis date between 2000-01-01 and today.")
        with args.input.open("rb") as source:
            raw = source.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024:
            raise ValidationError("CSV exceeds 2 MB.")
        result = validate_csv(raw, args.as_of)
        records = enrich(result["records"], args.as_of)
        report = {"dataset": {"name": args.input.name, "as_of": args.as_of.isoformat(), "quality": result["quality"]},
                  "summary": summarize(records, args.as_of), "records": records, "rules": RULES, "disclosure": DISCLOSURE}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as target:
            json.dump(report, target, indent=2, ensure_ascii=False)
        print(f"Saved {args.output}: {len(records)} accepted, {result['quality']['rejected']} rejected.")
        return 0
    except (OSError, ValidationError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
