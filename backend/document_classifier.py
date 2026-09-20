# document_classifier.py
"""
Detects what kind of document a PDF text looks like.
Returns: {"type": "invoice" | "receipt" | "bank_statement" | "purchase_order" | "generic",
          "confidence": 0.0..1.0,
          "signals": [list of matched keywords]}
"""

import re


# Each document type has a list of (keyword, weight) pairs.
# Higher total weight = higher confidence.
SIGNATURES = {
    "invoice": [
        (r"\binvoice\s*(no|number|#)?\b", 3),
        (r"\binvoice\s*date\b", 2),
        (r"\bbill\s*to\b", 2),
        (r"\bship\s*to\b", 2),
        (r"\bgst\b", 2),
        (r"\bvat\b", 2),
        (r"\btax\s*invoice\b", 3),
        (r"\bsubtotal\b", 1),
        (r"\btotal\s*amount\b", 1),
        (r"\bgrand\s*total\b", 1),
        (r"\bdue\s*date\b", 1),
        (r"\bterms\b", 1),
    ],
    "receipt": [
        (r"\breceipt\b", 3),
        (r"\bthank\s*you\b", 1),
        (r"\bcash\b", 1),
        (r"\bcard\b", 1),
        (r"\bchange\b", 1),
        (r"\bcashier\b", 1),
    ],
    "bank_statement": [
        (r"\bbank\s*statement\b", 3),
        (r"\baccount\s*(no|number)\b", 2),
        (r"\bstatement\s*period\b", 2),
        (r"\bopening\s*balance\b", 2),
        (r"\bclosing\s*balance\b", 2),
        (r"\bdebit\b", 1),
        (r"\bcredit\b", 1),
        (r"\bifsc\b", 2),
        (r"\bmicr\b", 1),
    ],
    "purchase_order": [
        (r"\bpurchase\s*order\b", 3),
        (r"\bpo\s*(no|number|#)?\b", 2),
        (r"\bsupplier\b", 1),
        (r"\bvendor\b", 1),
        (r"\bdeliver\s*to\b", 2),
    ],
}


def classify_document(text: str, filename: str = "") -> dict:
    """
    Returns:
      {
        "type": "...",
        "confidence": 0.0..1.0,
        "signals": ["invoice no", "bill to", ...]
      }
    """
    if not text:
        return {"type": "generic", "confidence": 0.0, "signals": []}

    # Work on the first 4000 chars — headers live at the top
    sample = text[:4000].lower()
    # Also include filename (e.g. "invoice-001.pdf")
    haystack = (filename or "").lower() + "\n" + sample

    scores = {}
    matched_signals = {}

    for doc_type, patterns in SIGNATURES.items():
        score = 0
        hits = []
        for pattern, weight in patterns:
            m = re.search(pattern, haystack)
            if m:
                score += weight
                hits.append(m.group(0).strip())
        scores[doc_type] = score
        matched_signals[doc_type] = hits

    if not scores:
        return {"type": "generic", "confidence": 0.0, "signals": []}

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    # If nothing matched, fall back to generic
    if best_score == 0:
        return {"type": "generic", "confidence": 0.0, "signals": []}

    # Confidence: how dominant is the winner?
    total = sum(scores.values())
    confidence = round(best_score / total, 2) if total > 0 else 0.0

    # Hard floor: if score < 3, we're not confident
    if best_score < 3:
        return {
            "type": "generic",
            "confidence": 0.3,
            "signals": matched_signals[best_type],
        }

    return {
        "type": best_type,
        "confidence": confidence,
        "signals": matched_signals[best_type],
    }


# Quick test — run this file directly: python document_classifier.py
if __name__ == "__main__":
    sample_invoice = """
    TAX INVOICE
    Invoice No: INV-2026-001
    Invoice Date: 18-09-2026
    Bill To: ABC Pvt Ltd
    GST: 18%
    Subtotal: 10,000
    Total Amount: 11,800
    """

    sample_bank = """
    BANK STATEMENT
    Account Number: 1234567890
    Statement Period: 01-08-2026 to 31-08-2026
    Opening Balance: 5,000
    Closing Balance: 8,500
    Debit / Credit
    IFSC: HDFC0001234
    """

    sample_random = """
    This is a short note about the project.
    We will meet next Tuesday.
    """

    for name, text in [
        ("invoice.pdf", sample_invoice),
        ("bank-statement.pdf", sample_bank),
        ("note.pdf", sample_random),
    ]:
        result = classify_document(text, filename=name)
        print(f"{name:25} -> {result}")