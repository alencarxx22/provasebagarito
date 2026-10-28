import pymupdf
from backend.parsers.test_gabaritos import gabaritos

for label, filename, cargo_kw in gabaritos:
    doc = pymupdf.open(filename)
    for p in range(len(doc)):
        text = doc[p].get_text()
        if cargo_kw.upper() in text.upper():
            print(f"==================== {label} ({filename}) p.{p} ====================")
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            for l in lines[:25]:
                print("  ", l)
            break
