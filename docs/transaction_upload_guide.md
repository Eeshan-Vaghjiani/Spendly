# Transaction CSV Upload Guide

Use `docs/transaction_upload_template.csv` as the template. Files must use
UTF-8 encoding, have a `.csv` extension, and remain below the configured upload
limit (2 MB by default).

## Required columns

| Column | Format | Rules |
|---|---|---|
| `transaction_timestamp` | ISO 8601 date-time | Include a timezone where possible. |
| `amount` | Positive decimal | Must be greater than zero. Currency is KES. |
| `category` | Text | Examples: food, transport, utilities, salary. |
| `transaction_type` | `expense` or `income` | Lowercase values are recommended. |
| `merchant` | Text | May be empty. |
| `is_recurring` | Boolean | Use `true` or `false`. |

## Validation behaviour

- Headers are checked before any rows are imported.
- Dates, amounts, types, booleans, and text lengths are validated.
- Common category names are standardised; for example, `dining` becomes `food`.
- A deterministic fingerprint identifies duplicate rows.
- Valid rows are stored even when other rows are invalid.
- Invalid rows are returned with their CSV row number and explanation.
- Duplicates are counted separately.
- Records are never silently discarded.

Example response:

```json
{
  "success": true,
  "data": {
    "received_rows": 25,
    "created_rows": 23,
    "duplicate_rows": 1,
    "invalid_rows": 1,
    "errors": [
      {
        "row": 8,
        "code": "INVALID_ROW",
        "message": "Amount must be greater than zero."
      }
    ]
  }
}
```
