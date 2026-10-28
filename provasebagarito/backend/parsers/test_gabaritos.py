import pymupdf
import re

gabaritos = [
    ('IBGP 1', 'gabarito_oficial ibgp1.pdf', '301'),
    ('IBGP 2', 'gabarito_definitivo ibgp2.pdf', 'ADMINISTRAT'),
    ('IBGP 3', 'gabarito_definitivo ibgp3.pdf', 'ADMINISTRAT'),
    ('IBGP 4', 'gabaritos ibgp4.pdf', 'ADMINISTRAT'),
    ('IBGP 5', 'gabaritos ibgp5.pdf', 'ADMINISTRAT'),
    ('CESGRANRIO 1', 'gabarito cesgranrio1.pdf', 'ADMINISTRA'),
    ('CESGRANRIO 2', 'gabaritos cesgranrio2.pdf', 'ADMINISTRA'),
    ('FGV 1', 'gabarito fgv1.pdf', 'ASSISTENTE ADMINISTRATIVO'),
    ('FGV 2', 'gabarito fgv2.pdf', 'ASSISTENTE ADMINISTRATIVO'),
    ('FUNDATEC 1', 'gabarito fundatec1.pdf', '865'),
    ('COPESE 1', 'gabarito_preliminar copese1.pdf', 'ASSISTENTE ADMINISTRATIVO'),
    ('FAFIPA 1', 'gabarito fafipa1.pdf', '8682')
]

for label, filename, cargo_kw in gabaritos:
    doc = pymupdf.open(filename)
    found_page = -1
    for p in range(len(doc)):
        if cargo_kw.upper() in doc[p].get_text().upper():
            found_page = p
            break
    print(f'{label} ({filename}): keyword "{cargo_kw}" -> found on page {found_page} of {len(doc)}')
