import re
from typing import List, Tuple, Optional

DISCIPLINA_KEYWORDS = {
    "Língua Portuguesa": ["PORTUGUÊS", "LÍNGUA PORTUGUESA", "LINGUA PORTUGUESA", "PORTUGUES"],
    "Raciocínio Lógico e Matemática": ["RACIOCÍNIO LÓGICO", "RACIOCINIO LOGICO", "MATEMÁTICA", "MATEMATICA", "RACIOCÍNIO QUANTITATIVO"],
    "Noções de Informática": ["INFORMÁTICA", "INFORMATICA", "NOÇÕES DE INFORMÁTICA", "TECNOLOGIA DA INFORMAÇÃO"],
    "Direito Administrativo": ["DIREITO ADMINISTRATIVO", "ADMINISTRAÇÃO PÚBLICA", "ADMINISTRACAO PUBLICA"],
    "Direito Constitucional": ["DIREITO CONSTITUCIONAL", "CONSTITUIÇÃO FEDERAL"],
    "Legislação Municipal / Local": ["LEGISLAÇÃO MUNICIPAL", "LEI ORGÂNICA", "ESTATUTO DOS SERVIDORES", "HISTÓRIA DO MUNICÍPIO"],
    "Conhecimentos Específicos": ["CONHECIMENTOS ESPECÍFICOS", "CONHECIMENTOS ESPECIFICOS", "ADMINISTRAÇÃO GERAL", "GESTÃO PÚBLICA", "ARQUIVOLOGIA", "ATENDIMENTO"]
}

def clean_pdf_text(text: str) -> str:
    """Remove marcas d'água PCI, links de rodapé e artefatos de digitalização."""
    # Remove marcas d'água pcimarkpci
    text = re.sub(r'pcimarkpci[^\n]*', '', text)
    text = re.sub(r'www\.pciconcursos\.com\.br[^\n]*', '', text, flags=re.IGNORECASE)
    # Remove cabeçalhos repetitivos de páginas
    text = re.sub(r'Página\s+\d+\s+de\s+\d+', '', text, flags=re.IGNORECASE)
    return text

def detect_subject_from_header_or_text(text: str, current_subject: str = "Conhecimentos Específicos") -> str:
    upper = text.upper()
    for disciplina, keywords in DISCIPLINA_KEYWORDS.items():
        for kw in keywords:
            # Check if keyword appears in an isolated header line or section title
            pattern = rf'(?:^|\n)\s*{re.escape(kw)}\s*(?:\n|$)'
            if re.search(pattern, upper):
                return disciplina
    return current_subject

def detect_local_law(text: str) -> Optional[str]:
    """Identifica se a questão trata de legislação ou história restrita a um município."""
    padroes = [
        r'lei\s+org[âa]nica\s+do\s+munic[íi]pio\s+de\s+([a-zA-Záàâãéèêíïóôõöúçñ\s]+)',
        r'munic[íi]pio\s+de\s+([a-zA-Záàâãéèêíïóôõöúçñ\s]+)',
        r'prefeitura\s+municipal\s+de\s+([a-zA-Záàâãéèêíïóôõöúçñ\s]+)',
        r'c[âa]mara\s+municipal\s+de\s+([a-zA-Záàâãéèêíïóôõöúçñ\s]+)'
    ]
    for p in padroes:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            nome = m.group(1).strip()
            # Se for curto e não for nome genérico
            if 3 < len(nome) < 30 and "brasil" not in nome.lower() and "estado" not in nome.lower():
                return nome.title()
    return None
