import csv
import io
import json
from decimal import Decimal

from fastapi import HTTPException
from pydantic import ValidationError

from app.analytics.trades import serialize
from app.schemas.trade import TradeInput
from app.services.journal import all_trades, write_trade

FIELDS = [
    "journal_id",
    "pair",
    "exchange",
    "currency",
    "market",
    "direction",
    "entry_at",
    "entry_price",
    "quantity",
    "stop_loss",
    "take_profit",
    "entry_fees",
    "funding",
    "leverage",
    "margin_type",
    "strategy",
    "notes",
    "mistakes",
    "emotion_before",
    "emotion_after",
    "lessons",
    "exits",
]
TEXT_FIELDS = {
    "exchange",
    "strategy",
    "notes",
    "mistakes",
    "emotion_before",
    "emotion_after",
    "lessons",
}


def export_csv(trades):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FIELDS)
    writer.writeheader()
    for trade in trades:
        record = serialize(trade)
        row = {key: record.get(key, "") for key in FIELDS}
        row["journal_id"] = trade.id
        row["exits"] = json.dumps(record["exits"])
        for key in TEXT_FIELDS:
            value = str(row[key] or "")
            # Quoting alone does not prevent spreadsheet formula execution.
            if value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r", "\n")):
                value = "'" + value
            row[key] = value
        writer.writerow(row)
    return buffer.getvalue()


def import_csv(session, payload):
    if len(payload) > 2_000_000:
        raise HTTPException(413, "CSV must be smaller than 2 MB.")
    try:
        reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
        required = {
            "pair",
            "exchange",
            "currency",
            "market",
            "direction",
            "entry_at",
            "entry_price",
            "quantity",
            "exits",
        }
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Missing required headers. Download the CSV template.")
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("Duplicate column headers are not allowed.")
        if set(reader.fieldnames) - set(FIELDS):
            raise ValueError("Unrecognized columns. Use the journal CSV format.")
        parsed = []
        for index, row in enumerate(reader, 2):
            if index > 1001:
                raise ValueError("Import is limited to 1,000 trades at a time.")
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Row {index}: column count does not match the header.")
            journal_id = row.pop("journal_id", "")
            for key in TEXT_FIELDS:
                if row.get(key, "").startswith("'") and row[key][1:].lstrip().startswith(
                    ("=", "+", "-", "@", "\t", "\r", "\n")
                ):
                    row[key] = row[key][1:]
            for key in ("stop_loss", "take_profit", "margin_type"):
                if not row.get(key):
                    row[key] = None
            for key in ("entry_fees", "funding"):
                if not row.get(key):
                    row[key] = "0"
            if not row.get("leverage"):
                row["leverage"] = "1"
            try:
                row["exits"] = json.loads(row["exits"] or "[]")
                parsed.append((journal_id, TradeInput.model_validate(row)))
            except (ValidationError, ValueError) as exc:
                raise ValueError(f"Row {index}: {exc}") from exc
        if not parsed:
            raise ValueError("CSV has no trade rows.")
    except (UnicodeError, ValueError, csv.Error) as exc:
        raise HTTPException(422, str(exc)[:2000]) from exc
    # Validate every row first. A bad row never leaves a half-imported batch.
    existing = all_trades(session)
    ids = {t.id for t in existing}

    def fingerprint(data):
        def normalized(value):
            if isinstance(value, Decimal):
                return format(value.normalize(), "f")
            if isinstance(value, dict):
                return {key: normalized(item) for key, item in value.items()}
            if isinstance(value, list):
                return [normalized(item) for item in value]
            return value.isoformat() if hasattr(value, "isoformat") else value

        return json.dumps(normalized(data.model_dump(exclude={"version"})), sort_keys=True)

    known = {
        fingerprint(
            TradeInput.model_validate(
                {
                    key: value
                    for key, value in serialize(t).items()
                    if key not in ("id", "has_screenshot", "metrics", "version")
                }
            )
        )
        for t in existing
    }
    inserted = skipped = 0
    for journal_id, data in parsed:
        signature = fingerprint(data)
        if signature in known or journal_id and journal_id in ids:
            skipped += 1
            continue
        write_trade(session, data)
        known.add(signature)
        if journal_id:
            ids.add(journal_id)
        inserted += 1
    session.commit()
    return {
        "inserted": inserted,
        "skipped": skipped,
        "message": "CSV import complete. Existing records were not overwritten.",
    }
