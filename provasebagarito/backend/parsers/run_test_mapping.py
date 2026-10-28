import pymupdf
from backend.parsers.base_parser import clean_pdf_text
from backend.parsers.prova_parser import split_into_question_blocks
from backend.parsers.test_text_mapping import extract_all_support_texts_from_exam

def test_support(pdf_path):
    doc = pymupdf.open(pdf_path)
    full = ""
    for p in doc:
        full += clean_pdf_text(p.get_text()) + "\n"
        
    blocks = split_into_question_blocks(full)
    q_positions = [{"num": b[0], "start_pos": b[2], "end_pos": b[2] + len(b[1])} for b in blocks]
    
    res = extract_all_support_texts_from_exam(full, q_positions)
    print(f"=== {pdf_path}: {len(res)} questões vinculadas a texto de apoio! ===")
    for q_num in sorted(res.keys()):
        item = res[q_num]
        print(f"  Q#{q_num} -> Titulo: {item['titulo']} ({item['aplicavel']}) | Tamanho: {len(item['texto'])} chars")

test_support("assistente_administrativo ibgp5.pdf")
test_support("assistente_administrativo fgv1.pdf")
