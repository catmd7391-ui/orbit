# extractors/invoice.py
"""
Extracts structured fields from an INVOICE PDF text.
Returns consistent columns regardless of invoice layout.
"""

import re
from brain import ask_ai


# The canonical columns EVERY invoice will produce.
# Every invoice, no matter the layout, gets mapped to THESE columns.
INVOICE_COLUMNS = [
    "Invoice No",
    "Date",
    "Customer",
    "Amount",
    "GST",
    "Total",
]


def extract_invoice(text: str, filename: str = "") -> dict:
    """
    Extract invoice fields from text.
    Returns:
      {
        "success": True,
        "document_type": "Invoice",
        "sheet_name": "Invoices",
        "columns": [...],
        "rows": [[...]],
        "fields": {...},
        "confidence": 0.0..1.0,
        "warnings": [...]
      }
    """
    if not text or len(text.strip()) < 20:
        return {"success": False, "error": "Text too short", "fields": {}}

    # Give the model the first 8000 chars
    sample = text[:8000]

    prompt = f"""You are an invoice extractor.

Read the invoice below and extract EXACTLY these fields.
If a field is missing, use empty string "".

DOCUMENT: {filename}

TEXT:
---
{sample}
---

Return ONLY JSON in this exact shape:
{{
  "invoice_no": "",
  "date": "",
  "customer": "",
  "amount": "",
  "gst": "",
  "total": "",
  "confidence": 0.0
}}

RULES:
1. invoice_no: the invoice number/ID (e.g. "INV-001")
2. date: the invoice date in DD-MM-YYYY format if possible
3. customer: who the invoice is billed TO (company/person name)
4. amount: the subtotal BEFORE tax (numbers only, no ₹ symbol, no commas)
5. gst: the tax amount (numbers only, no ₹ symbol, no commas). If no tax, use "0".
6. total: the final amount including tax (numbers only, no ₹ symbol, no commas)
7. confidence: 0.0 to 1.0 — how sure you are
8. Return ONLY the JSON. No extra text.

If a value has a currency symbol or commas, strip them.
Example: "₹10,000.00" → "10000.00"
"""

    try:
        response = ask_ai(prompt)
        parsed = _parse_json(response)

        if not parsed:
            return {"success": False, "error": "Invalid JSON from AI", "fields": {}}

        # Extract the 6 canonical fields
        invoice_no = _clean_str(parsed.get("invoice_no", ""))
        date_val   = _clean_str(parsed.get("date", ""))
        customer   = _clean_str(parsed.get("customer", ""))
        amount     = _clean_number(parsed.get("amount", ""))
        gst        = _clean_number(parsed.get("gst", "")) or "0"
        total      = _clean_number(parsed.get("total", ""))
        confidence = float(parsed.get("confidence", 0.5) or 0.5)

        warnings = []

        # ---- Validate the math ----
        try:
            amt_f = float(amount) if amount else 0.0
            gst_f = float(gst) if gst else 0.0
            tot_f = float(total) if total else 0.0

            if amt_f and gst_f and tot_f:
                expected = amt_f + gst_f
                diff = abs(expected - tot_f)
                if diff > 1.0:  # allow 1 unit rounding
                    warnings.append(
                        f"Math mismatch: {amt_f} + {gst_f} = {expected}, but total is {tot_f}"
                    )
                    confidence = max(0.3, confidence - 0.2)
        except Exception:
            pass

        if not invoice_no:
            warnings.append("Invoice number not found")
            confidence = max(0.3, confidence - 0.15)

        if not total:
            warnings.append("Total amount not found")
            confidence = max(0.3, confidence - 0.2)

        # ---- Build the row in canonical order ----
        row = [invoice_no, date_val, customer, amount, gst, total]

        fields = dict(zip(INVOICE_COLUMNS, row))

        return {
            "success": True,
            "document_type": "Invoice",
            "sheet_name": "Invoices",
            "columns": INVOICE_COLUMNS,
            "rows": [row],
            "fields": fields,
            "confidence": round(confidence, 2),
            "warnings": warnings,
        }

    except Exception as e:
        return {"success": False, "error": str(e), "fields": {}}


def _clean_str(v):
    """Trim whitespace and quotes."""
    if v is None:
        return ""
    return str(v).strip().strip('"').strip("'")


def _clean_number(v):
    """Remove ₹, commas, spaces. Keep digits, '.', and '-'."""
    if v is None:
        return ""
    s = str(v)
    # remove currency symbols and common separators
    s = re.sub(r"[₹$€£,]", "", s)
    s = s.strip()
    # keep only digits, dot, minus
    s = re.sub(r"[^\d\.\-]", "", s)
    return s


def _parse_json(text):
    """Robust JSON parser (same idea as dynamic_pdf_analyzer)."""
    import json
    if isinstance(text, dict):
        return text
    if not text:
        return None
    t = str(text).strip()
    try:
        return json.loads(t)
    except Exception:
        pass
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", t, re.DOTALL | re.IGNORECASE)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    start = t.find("{")
    end = t.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(t[start:end + 1])
        except Exception:
            pass
    return None


# Quick test — run: python -m extractors.invoice
if __name__ == "__main__":
    sample = """
    TAX INVOICE
    Invoice No: INV-2026-001
    Invoice Date: 18-09-2026
    Bill To: ABC Pvt Ltd
    123 Business Street, Mumbai

    Description        Qty    Rate      Amount
    Widget A           10     500       5,000
    Widget B           5      1,000     5,000

    Subtotal:                             10,000
    GST (18%):                            1,800
    Total Amount:                         11,800
    """

    result = extract_invoice(sample, filename="invoice-001.pdf")
    import json
    print(json.dumps(result, indent=2, default=str))