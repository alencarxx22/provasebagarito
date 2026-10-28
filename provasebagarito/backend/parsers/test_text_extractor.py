import pymupdf
import re
from backend.parsers.base_parser import clean_pdf_text

def extract_support_texts(full_text: str):
    """
    Identifica todos os textos de apoio (leitura/interpretação) no caderno de prova
    e mapeia para quais questões eles são aplicáveis.
    """
    support_blocks = []
    
    # Padrões comuns de indicação de texto base
    # 1. "Leia o texto ... para responder as questões de X a Y"
    # 2. "use o texto a seguir para responder às próximas X questões"
    # 3. "O texto seguinte servirá de base para responder às questões de X a Y"
    # 4. "Leia o texto a seguir e responda as QUESTÕES X e Y"
    padroes_gatilho = [
        r'(?:Leia\s+(?:atentamente\s+)?o\s+texto|O\s+texto\s+seguinte\s+servir[áa]|Aten[çc][ãa]o:\s*use\s+o\s+texto|As\s+quest[õo]es\s+(?:da\s+prova\s+)?referem-se\s+ao\s+texto)[^\n]*?(?:quest[õo]es\s+(?:de\s+)?(\d{1,2})\s+(?:a|e)\s+(\d{1,2})|pr[óo]ximas\s+(\w+|\d+)\s+quest[õo]es|ao\s+texto\s+a\s+seguir)'
    ]

    # Encontrar blocos entre gatilhos de texto e a primeira questão
    lines = full_text.split('\n')
    
    # Procurar menções explícitas de "TEXTO"
    texto_headers = list(re.finditer(r'(?:^|\n)\s*(Leia\s+o\s+texto[^\n]*|Aten[çc][ãa]o:\s*use\s+o\s+texto[^\n]*|O\s+texto\s+seguinte[^\n]*|TEXTO\s+[1-9IIVV]+[^\n]*|As\s+quest[õo]es[^\n]*referem-se\s+ao\s+texto[^\n]*)', full_text, re.IGNORECASE))
    
    print(f"Total de cabeçalhos de texto encontrados: {len(texto_headers)}")
    for m in texto_headers:
        print("  Gatilho:", repr(m.group(1).strip()[:100]))

extract_support_texts("")
