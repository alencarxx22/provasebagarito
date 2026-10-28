import pymupdf
import re
import uuid
from typing import List, Dict, Optional, Any, Tuple
from backend.parsers.base_parser import clean_pdf_text, detect_subject_from_header_or_text, detect_local_law
from backend.parsers.gabarito_parser import extract_gabarito_from_file

def map_word_to_number(w: str) -> int:
    words = {
        "uma": 1, "duas": 2, "três": 3, "tres": 3, "quatro": 4, "cinco": 5,
        "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10
    }
    w_lower = w.lower().strip()
    if w_lower.isdigit():
        return int(w_lower)
    return words.get(w_lower, 5)

def extract_support_texts_map(full_text: str, question_blocks: List[Tuple[int, str, int]]) -> Dict[int, Dict[str, str]]:
    """
    Identifica todos os textos-base/apoio (artigos, crônicas, fábulas) no PDF da prova
    e mapeia para os números de questões aos quais pertencem.
    """
    q_to_text: Dict[int, Dict[str, str]] = {}
    if not question_blocks:
        return q_to_text

    # 1. Texto de apoio antes da primeira questão (após capa de instruções)
    first_q_num, first_q_content, first_q_start = question_blocks[0]
    pre_text = full_text[:first_q_start]

    # Gatilhos típicos de início de texto
    pre_trigger = re.search(r'(?:(?:PORTUGU[ÊE]S|L[ÍI]NGUA\s+PORTUGUESA)[^\n]*\n)?\s*(?:Leia\s+(?:atentamente\s+)?o\s+texto|O\s+texto\s+seguinte|TEXTO\s+[1-9IIVV]+|As\s+quest[õo]es[^\n]*referem-se\s+ao\s+texto|Aten[çc][ãa]o:\s*use\s+o\s+texto|À\s+moda\s+brasileira|Silenciosamente\s+barulhento|Insônia\s+infeliz)', pre_text, re.IGNORECASE)
    if pre_trigger:
        raw_support = pre_text[pre_trigger.start():].strip()
        if len(raw_support) > 150:
            # Identificar abrangência de questões
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
                    end_q = 10

            lines = [l.strip() for l in raw_support.split('\n') if l.strip()]
            titulo = "Texto de Apoio da Prova"
            for l in lines:
                if len(l) > 6 and not any(w in l.upper() for w in ["LEIA", "TEXTO", "PORTUGUÊS", "INSTRUÇÕES", "CONCURSO", "QUESTÕES", "EDITAL", "ATENÇÃO"]):
                    titulo = l
                    break

            info = {
                "titulo": titulo,
                "texto": raw_support,
                "aplicavel": f"Questões {start_q} a {end_q}"
            }
            for q_num in range(start_q, end_q + 1):
                q_to_text[q_num] = info

    # 2. Textos de apoio entre questões intermediárias (ex: Texto 2 após Q3 ou Q10)
    for i in range(len(question_blocks) - 1):
        q_curr_num, q_curr_content, q_curr_start = question_blocks[i]
        q_next_num, q_next_content, q_next_start = question_blocks[i+1]

        q_curr_end = q_curr_start + len(q_curr_content)
        if q_next_start > q_curr_end:
            inter_text = full_text[q_curr_end:q_next_start].strip()
            if len(inter_text) > 150 and any(w in inter_text.lower() for w in ["leia o texto", "texto 2", "texto 3", "use o texto a seguir", "responda as questões", "texto seguinte"]):
                range_m = re.search(r'quest[õo]es\s+(?:de\s+)?(\d{1,2})\s+(?:a|e)\s+(\d{1,2})', inter_text, re.IGNORECASE)
                if range_m:
                    start_q = int(range_m.group(1))
                    end_q = int(range_m.group(2))
                else:
                    prox_m = re.search(r'pr[óo]ximas\s+(\w+|\d+)\s+quest[õo]es', inter_text, re.IGNORECASE)
                    if prox_m:
                        start_q = q_next_num
                        end_q = q_next_num + map_word_to_number(prox_m.group(1)) - 1
                    else:
                        start_q = q_next_num
                        end_q = q_next_num + 4

                lines = [l.strip() for l in inter_text.split('\n') if l.strip()]
                titulo = f"Texto de Apoio (Questões {start_q} a {end_q})"
                for l in lines:
                    if len(l) > 6 and not any(w in l.upper() for w in ["LEIA", "TEXTO", "ATENÇÃO", "QUESTÕES", "USE O TEXTO", "SEGUINTE"]):
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

def split_into_question_blocks(full_text: str) -> List[Tuple[int, str, int]]:
    """
    Divide o texto do caderno de prova em blocos individuais de questões.
    Trata tanto formato 'QUESTÃO X' quanto números isolados em início de linha (FGV/CESGRANRIO).
    """
    # 1. Padrão explícito: QUESTÃO X / Questão X
    q_explicit = list(re.finditer(r'(?:^|\n)\s*(?:QUEST[ÃA]O\s+(\d{1,2})|Quest[ãa]o\s+(\d{1,2}))\s*[\:\–\-\.]?', full_text, re.IGNORECASE))
    
    if len(q_explicit) >= 10:
        blocks = []
        for i in range(len(q_explicit)):
            m = q_explicit[i]
            q_num = int(m.group(1) or m.group(2))
            start_pos = m.end()
            end_pos = q_explicit[i+1].start() if i+1 < len(q_explicit) else len(full_text)
            content = full_text[start_pos:end_pos].strip()
            blocks.append((q_num, content, m.start()))
        return blocks

    # 2. Padrão com número no início de linha: '1 (NMCB...' ou '1\n' ou '1 - '
    q_lines = list(re.finditer(r'(?:^|\n)\s*(\d{1,2})\s*(?:\([^\)]+\)|\-|\–|\.|\s)?\s*(?:\n|\r\n)(?=[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇ])', full_text))
    
    filtered = []
    expected = 1
    for m in q_lines:
        num = int(m.group(1))
        if num == expected:
            filtered.append(m)
            expected += 1
            
    if len(filtered) >= 10:
        blocks = []
        for i in range(len(filtered)):
            m = filtered[i]
            q_num = int(m.group(1))
            start_pos = m.end()
            end_pos = filtered[i+1].start() if i+1 < len(filtered) else len(full_text)
            content = full_text[start_pos:end_pos].strip()
            blocks.append((q_num, content, m.start()))
        return blocks

    # 3. Fallback: 'X - ' ou 'X. '
    q_fallback = list(re.finditer(r'(?:^|\n)\s*(\d{1,2})\s*[\.\-\)]\s+(?=[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇ])', full_text))
    filtered_fb = []
    expected = 1
    for m in q_fallback:
        num = int(m.group(1))
        if num == expected:
            filtered_fb.append(m)
            expected += 1
            
    blocks = []
    for i in range(len(filtered_fb)):
        m = filtered_fb[i]
        q_num = int(m.group(1))
        start_pos = m.end()
        end_pos = filtered_fb[i+1].start() if i+1 < len(filtered_fb) else len(full_text)
        content = full_text[start_pos:end_pos].strip()
        blocks.append((q_num, content, m.start()))
    return blocks

def parse_statement_and_alternatives(raw_content: str) -> Tuple[str, List[Dict[str, str]]]:
    """Extrai o enunciado e as alternativas (A a E) de um bloco de questão."""
    lines = raw_content.split("\n")
    enunciado_lines = []
    alternativas = []
    current_letra = None
    current_lines = []

    alt_regex = re.compile(r'^\s*(?:\(([A-Ea-e])\)|([A-Ea-e])\s*[\)\.\–\-])\s*(.*)$')
    
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
            
        m = alt_regex.match(line_clean)
        if m:
            if current_letra:
                alternativas.append({
                    "letra": current_letra,
                    "texto": " ".join(current_lines).strip()
                })
            current_letra = (m.group(1) or m.group(2)).upper()
            first_text = m.group(3).strip()
            current_lines = [first_text] if first_text else []
        else:
            if current_letra:
                if re.search(r'\s+(?:\([B-Eb-e]\)|[B-Eb-e]\s*[\)\.\–\-])\s+', line_clean):
                    parts = re.split(r'\s+(?=(?:\([B-Eb-e]\)|[B-Eb-e]\s*[\)\.\–\-]))', line_clean)
                    for idx, p in enumerate(parts):
                        sub_m = alt_regex.match(p.strip())
                        if sub_m:
                            if current_letra:
                                alternativas.append({
                                    "letra": current_letra,
                                    "texto": " ".join(current_lines).strip()
                                })
                            current_letra = (sub_m.group(1) or sub_m.group(2)).upper()
                            current_lines = [sub_m.group(3).strip()]
                        else:
                            current_lines.append(p.strip())
                else:
                    current_lines.append(line_clean)
            else:
                enunciado_lines.append(line_clean)

    if current_letra:
        alternativas.append({
            "letra": current_letra,
            "texto": " ".join(current_lines).strip()
        })

    enunciado = " ".join(enunciado_lines).strip()
    return enunciado, alternativas

def parse_full_exam(prova_pdf_path: str, gabarito_pdf_path: str, banca: str, orgao: str, ano: int, cargo: str, cargo_kw: str = "") -> List[Dict[str, Any]]:
    """Lê a prova e o gabarito, cruzando as questões com os gabaritos e vinculando os textos de apoio."""
    doc = pymupdf.open(prova_pdf_path)
    full_text = ""
    for page in doc:
        full_text += clean_pdf_text(page.get_text()) + "\n"

    # Extrair gabarito oficial
    gabaritos = extract_gabarito_from_file(gabarito_pdf_path, banca, cargo_kw)

    blocks = split_into_question_blocks(full_text)
    
    # Extrair mapa de textos de apoio
    support_texts_map = extract_support_texts_map(full_text, blocks)

    questoes = []
    current_disciplina = "Língua Portuguesa" if "PORTUGU" in full_text[:4000].upper() else "Conhecimentos Específicos"

    for q_num, raw_content, char_idx in blocks:
        # Detectar se há novo cabeçalho de disciplina na janela anterior (janela ampla de 1200 chars)
        context_window = full_text[max(0, char_idx - 1200):char_idx]
        current_disciplina = detect_subject_from_header_or_text(context_window, current_disciplina)

        enunciado, alternativas = parse_statement_and_alternatives(raw_content)
        
        if len(enunciado) < 15 or len(alternativas) < 3:
            continue

        gab_letra = gabaritos.get(q_num, "A")
        anulada = (gab_letra in ["*", "X", "ANULADA"])
        if anulada:
            gab_letra = "ANULADA"

        municipio_esp = detect_local_law(enunciado)

        # Vincular texto de apoio se existir para esta questão
        support_info = support_texts_map.get(q_num)
        texto_apoio = support_info["texto"] if support_info else None
        texto_apoio_titulo = support_info["titulo"] if support_info else None
        texto_apoio_aplicavel = support_info["aplicavel"] if support_info else None

        # Se a questão referencia explicitamente "texto" ou possui texto de apoio, é Língua Portuguesa
        enun_lower = enunciado.lower()
        if "sobre o texto" in enun_lower or "segundo o texto" in enun_lower or "conforme o texto" in enun_lower or "no texto" in enun_lower or (support_info and q_num <= 15):
            current_disciplina = "Língua Portuguesa"

        # Atribuir tópico padrão
        topico_default = f"Fundamentos de {current_disciplina}"
        if "Português" in current_disciplina:
            if "crase" in enun_lower:
                topico_default = "Crase"
            elif "concord" in enun_lower:
                topico_default = "Concordância Verbal e Nominal"
            elif "regênc" in enun_lower or "regenc" in enun_lower:
                topico_default = "Regência Verbal e Nominal"
            elif "pontua" in enun_lower or "vírgula" in enun_lower:
                topico_default = "Pontuação"
            elif "acentu" in enun_lower:
                topico_default = "Acentuação Gráfica"
            else:
                topico_default = "Interpretação e Compreensão de Texto"
        elif "Informática" in current_disciplina:
            if "excel" in enun_lower or "planilha" in enun_lower:
                topico_default = "Microsoft Excel / Planilhas Eletrônicas"
            elif "word" in enun_lower:
                topico_default = "Processador de Textos / Word"
            elif "segurança" in enun_lower or "vírus" in enun_lower:
                topico_default = "Segurança da Informação"
            elif "internet" in enun_lower or "navegador" in enun_lower:
                topico_default = "Redes e Navegação na Internet"
            else:
                topico_default = "Noções de Sistemas Operacionais e Hardware"
        elif "Raciocínio" in current_disciplina or "Matemática" in current_disciplina:
            if "porcentagem" in enun_lower or "%" in enunciado:
                topico_default = "Porcentagem e Regra de Três"
            elif "probabilidade" in enun_lower:
                topico_default = "Probabilidade e Análise Combinatória"
            elif "proposição" in enun_lower or "tabela verdade" in enun_lower:
                topico_default = "Lógica Proposicional e Conectivos"
            else:
                topico_default = "Raciocínio Lógico e Sequências"
        elif "Administrativo" in current_disciplina or "Específicos" in current_disciplina:
            if "licita" in enun_lower or "14.133" in enunciado or "8.666" in enunciado:
                topico_default = "Licitações e Contratos Administrativos"
            elif "ato" in enun_lower and "administrativo" in enun_lower:
                topico_default = "Atos Administrativos"
            elif "servidor" in enun_lower or "cargo" in enun_lower:
                topico_default = "Regime Jurídico dos Servidores Públicos"
            elif "arquivo" in enun_lower or "document" in enun_lower:
                topico_default = "Arquivologia e Gestão de Documentos"
            elif "atendimento" in enun_lower or "público" in enun_lower:
                topico_default = "Atendimento ao Cidadão e Relações Humanas"
            elif "comunicação oficial" in enun_lower or "redação oficial" in enun_lower or "ofício" in enun_lower:
                topico_default = "Redação Oficial e Correspondência"
            else:
                topico_default = "Princípios da Administração Pública"

        questao_id = f"Q-{banca.upper()}-{ano}-{q_num}-{str(uuid.uuid4())[:6]}"
        
        questoes.append({
            "id": questao_id,
            "banca": banca,
            "orgao": orgao,
            "ano": ano,
            "cargo": cargo,
            "disciplina": current_disciplina,
            "topico_edital": topico_default,
            "numero": q_num,
            "enunciado": enunciado,
            "alternativas": alternativas,
            "gabarito_oficial": gab_letra,
            "anulada": anulada,
            "explicacao": f"Gabarito oficial divulgado pela banca {banca}.",
            "municipio_especifico": municipio_esp,
            "fonte_arquivo": prova_pdf_path,
            "texto_apoio": texto_apoio,
            "texto_apoio_titulo": texto_apoio_titulo,
            "texto_apoio_aplicavel": texto_apoio_aplicavel
        })

    return questoes
