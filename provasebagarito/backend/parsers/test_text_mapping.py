import pymupdf
import re
from typing import Dict, Any, List, Optional
from backend.parsers.base_parser import clean_pdf_text

def map_word_to_number(w: str) -> int:
    words = {
        "uma": 1, "duas": 2, "três": 3, "tres": 3, "quatro": 4, "cinco": 5,
        "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10
    }
    w_lower = w.lower().strip()
    if w_lower.isdigit():
        return int(w_lower)
    return words.get(w_lower, 5)

def extract_all_support_texts_from_exam(full_text: str, question_positions: List[Dict[str, Any]]) -> Dict[int, Dict[str, str]]:
    """
    Localiza todos os textos de apoio e associa aos números de questão correspondentes.
    Retorna: { questao_num: { "titulo": "...", "texto": "...", "aplicavel": "..." } }
    """
    q_to_text: Dict[int, Dict[str, str]] = {}
    
    # 1. Procurar texto antes da primeira questão (após página de capa)
    if question_positions:
        first_q_pos = question_positions[0]["start_pos"]
        pre_text = full_text[:first_q_pos]
        
        # Ignorar instruções de capa
        trigger_m = re.search(r'(?:PORTUGU[ÊE]S|L[ÍI]NGUA\s+PORTUGUESA|Leia\s+(?:atentamente\s+)?o\s+texto|O\s+texto\s+seguinte|TEXTO\s+[1-9IIVV]+|As\s+quest[õo]es[^\n]*referem-se\s+ao\s+texto|À\s+moda\s+brasileira|Silenciosamente\s+barulhento)', pre_text, re.IGNORECASE)
        if trigger_m:
            raw_support = pre_text[trigger_m.start():].strip()
            # Se for texto longo (> 150 caracteres)
            if len(raw_support) > 150:
                # Detectar alcance de questões
                range_m = re.search(r'quest[õo]es\s+(?:de\s+)?(\d{1,2})\s+(?:a|e)\s+(\d{1,2})', raw_support, re.IGNORECASE)
                if range_m:
                    start_q = int(range_m.group(1))
                    end_q = int(range_m.group(2))
                else:
                    prox_m = re.search(r'pr[óo]ximas\s+(\w+|\d+)\s+quest[õo]es', raw_support, re.IGNORECASE)
                    if prox_m:
                        start_q = 1
                        end_q = map_word_to_number(prox_m.group(1))
                    else:
                        start_q = 1
                        end_q = 10 # Padrão para português
                        
                # Extrair título aproximado
                lines = [l.strip() for l in raw_support.split('\n') if l.strip()]
                titulo = "Texto de Apoio da Prova"
                for l in lines[:6]:
                    if len(l) > 6 and not any(w in l.upper() for w in ["LEIA", "TEXTO", "PORTUGUÊS", "INSTRUÇÕES", "CONCURSO", "QUESTÕES"]):
                        titulo = l
                        break
                        
                info = {
                    "titulo": titulo,
                    "texto": raw_support,
                    "aplicavel": f"Questões {start_q} a {end_q}"
                }
                for q_num in range(start_q, end_q + 1):
                    q_to_text[q_num] = info

    # 2. Procurar textos intermediários entre questões (ex: entre Q3 e Q4)
    for i in range(len(question_positions) - 1):
        q_curr = question_positions[i]["num"]
        q_next = question_positions[i+1]["num"]
        
        inter_start = question_positions[i]["end_pos"]
        inter_end = question_positions[i+1]["start_pos"]
        
        if inter_end > inter_start:
            inter_text = full_text[inter_start:inter_end].strip()
            
            # Verificar se há texto de apoio no meio
            if len(inter_text) > 150 and any(w in inter_text.lower() for w in ["leia o texto", "texto 2", "texto 3", "use o texto a seguir", "responda as questões"]):
                range_m = re.search(r'quest[õo]es\s+(?:de\s+)?(\d{1,2})\s+(?:a|e)\s+(\d{1,2})', inter_text, re.IGNORECASE)
                if range_m:
                    start_q = int(range_m.group(1))
                    end_q = int(range_m.group(2))
                else:
                    prox_m = re.search(r'pr[óo]ximas\s+(\w+|\d+)\s+quest[õo]es', inter_text, re.IGNORECASE)
                    if prox_m:
                        start_q = q_next
                        end_q = q_next + map_word_to_number(prox_m.group(1)) - 1
                    else:
                        start_q = q_next
                        end_q = min(len(question_positions), q_next + 5)
                        
                lines = [l.strip() for l in inter_text.split('\n') if l.strip()]
                titulo = f"Texto de Apoio (Questões {start_q} a {end_q})"
                for l in lines[:6]:
                    if len(l) > 6 and not any(w in l.upper() for w in ["LEIA", "TEXTO", "ATENÇÃO", "QUESTÕES", "USE O TEXTO"]):
                        titulo = l
                        break

                info = {
                    "titulo": titulo,
                    "texto": inter_text,
                    "aplicavel": f"Questões {start_q} a {end_q}"
                }
                for q_num in range(start_q, end_q + 1):
                    q_to_text[q_num] = info

    return q_to_text

print("Função extract_all_support_texts_from_exam criada com sucesso!")
