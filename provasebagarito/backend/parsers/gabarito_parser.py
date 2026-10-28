import pymupdf
import re
from typing import Dict, Optional, Tuple

def parse_fafipa_gabarito(text: str, cargo_kw: str = "8682") -> Dict[int, str]:
    """Ex: 01: E, 02: A"""
    answers = {}
    lines = text.split("\n")
    in_cargo = False
    for line in lines:
        line_clean = line.strip()
        if cargo_kw.upper() in line_clean.upper():
            in_cargo = True
            continue
        elif in_cargo and re.match(r'^\d{4}\s*[\-–]', line_clean):
            # Proximo cargo
            break
        
        if in_cargo:
            m = re.match(r'^0?(\d{1,2})\s*:\s*([A-Ea-e\*X])', line_clean)
            if m:
                answers[int(m.group(1))] = m.group(2).upper()
    return answers

def parse_cesgranrio_gabarito(doc: pymupdf.Document, cargo_kw: str = "Administração") -> Dict[int, str]:
    """Ex: 1 - E, 2 - B... ou Conhecimentos Básicos + Conhecimentos Específicos"""
    answers = {}
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"
    
    # Basicos + Especificos
    # Padrão: "1 - E" ou "1- \n B"
    matches = re.findall(r'(\d{1,2})\s*[\-–]\s*([A-Ea-e\*X])', full_text)
    for q_str, ans in matches:
        q_num = int(q_str)
        if q_num not in answers:
            answers[q_num] = ans.upper()
    return answers

def parse_fundatec_gabarito(text: str, cargo_kw: str = "865") -> Dict[int, str]:
    """Ex: linha de números seguida de linhas de letras."""
    answers = {}
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    num_idx = -1
    for i, line in enumerate(lines):
        if "01 02 03 04" in line or "1 2 3 4 5" in line or (re.search(r'\b01\b.*\b02\b.*\b03\b', line)):
            num_idx = i
            break
    
    if num_idx != -1 and num_idx + 1 < len(lines):
        # A próxima linha ou linhas contêm as letras
        letters = []
        for j in range(num_idx + 1, min(len(lines), num_idx + 80)):
            if len(lines[j]) == 1 and lines[j] in "ABCDE*X":
                letters.append(lines[j])
            elif all(c in "ABCDE*X \t" for c in lines[j]):
                letters.extend([c for c in lines[j].split() if c in "ABCDE*X"])
        
        for q, letter in enumerate(letters, start=1):
            answers[q] = letter.upper()
    return answers

def parse_fgv_copese_block_gabarito(page_text: str, cargo_kw: str = "ASSISTENTE ADMINISTRATIVO") -> Dict[int, str]:
    """Para FGV e COPESE, onde há um bloco de números 1..N seguido por bloco de letras."""
    answers = {}
    lines = [l.strip() for l in page_text.split("\n") if l.strip()]
    
    # Encontrar início do cargo
    start_idx = 0
    if cargo_kw:
        for idx, l in enumerate(lines):
            if cargo_kw.upper() in l.upper():
                start_idx = idx
                break
                
    relevant_lines = lines[start_idx:]
    
    # Coletar sequência de números e depois sequência de letras
    numbers = []
    letters = []
    collecting_numbers = True
    
    for l in relevant_lines:
        if l.isdigit() and 1 <= int(l) <= 100:
            if collecting_numbers:
                numbers.append(int(l))
            else:
                # começou nova coluna ou bloco
                pass
        elif len(l) == 1 and l.upper() in "ABCDE*X":
            collecting_numbers = False
            letters.append(l.upper())
        elif len(l) == 2 and l[0].upper() in "ABCDE*X" and l[1] == "*":
            collecting_numbers = False
            letters.append("*")
            
    if numbers and letters and len(letters) >= len(numbers) * 0.7:
        for q, letter in zip(numbers, letters):
            answers[q] = letter
            
    return answers

def parse_ibgp_columnar_gabarito(page_text: str, cargo_kw: str = "301") -> Dict[int, str]:
    """Para IBGP, onde aparecem pares intercalados: Número, Letra, Número, Letra..."""
    answers = {}
    lines = [l.strip() for l in page_text.split("\n") if l.strip()]
    
    i = 0
    while i < len(lines) - 1:
        l1 = lines[i]
        l2 = lines[i+1]
        if l1.isdigit() and 1 <= int(l1) <= 100:
            if len(l2) == 1 and l2.upper() in "ABCDE*X":
                answers[int(l1)] = l2.upper()
                i += 2
                continue
            elif l2 == "*":
                answers[int(l1)] = "*"
                i += 2
                continue
        i += 1
    return answers

def extract_gabarito_from_file(gabarito_path: str, banca: str, cargo_kw: str = "") -> Dict[int, str]:
    doc = pymupdf.open(gabarito_path)
    banca_upper = banca.upper()
    
    # 1. Tentar encontrar página específica pelo cargo_kw
    target_pages = []
    if cargo_kw:
        for p_no in range(len(doc)):
            if cargo_kw.upper() in doc[p_no].get_text().upper():
                target_pages.append(p_no)
    if not target_pages:
        target_pages = list(range(len(doc)))

    for p_no in target_pages:
        text = doc[p_no].get_text()
        
        # FAFIPA
        if "FAFIPA" in banca_upper or "01:" in text:
            ans = parse_fafipa_gabarito(text, cargo_kw)
            if len(ans) >= 10:
                return ans
                
        # FUNDATEC
        if "FUNDATEC" in banca_upper or "CP 865" in text or "EDITAL Nº" in text:
            ans = parse_fundatec_gabarito(text, cargo_kw)
            if len(ans) >= 10:
                return ans

        # FGV
        if "FGV" in banca_upper:
            ans = parse_fgv_copese_block_gabarito(text, cargo_kw)
            if len(ans) >= 10:
                return ans
                
        # COPESE
        if "COPESE" in banca_upper:
            ans = parse_fgv_copese_block_gabarito(text, cargo_kw)
            if len(ans) >= 10:
                return ans
                
        # IBGP
        if "IBGP" in banca_upper:
            ans = parse_ibgp_columnar_gabarito(text, cargo_kw)
            if len(ans) >= 10:
                return ans

        # CESGRANRIO
        if "CESGRANRIO" in banca_upper or "TRANSPETRO" in text or "CHESF" in text:
            ans = parse_cesgranrio_gabarito(doc, cargo_kw)
            if len(ans) >= 10:
                return ans

    # Fallback genérico: tentar todos os métodos
    for p_no in range(len(doc)):
        text = doc[p_no].get_text()
        for fn in [parse_ibgp_columnar_gabarito, parse_fgv_copese_block_gabarito, parse_fafipa_gabarito, parse_fundatec_gabarito]:
            res = fn(text, cargo_kw)
            if len(res) >= 15:
                return res

    return {}
