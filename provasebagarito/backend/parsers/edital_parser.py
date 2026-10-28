import pymupdf
import re
import uuid
from typing import Dict, List, Optional, Any
from backend.parsers.base_parser import clean_pdf_text, DISCIPLINA_KEYWORDS, detect_local_law

DEFAULT_EDITAL_TOPICOS = [
    {
        "disciplina": "Língua Portuguesa",
        "topico": "Compreensão e Interpretação de Texto",
        "subtopicos": ["Tipologia textual", "Coesão e coerência", "Significação de palavras"]
    },
    {
        "disciplina": "Língua Portuguesa",
        "topico": "Ortografia e Acentuação Gráfica",
        "subtopicos": ["Novo acordo ortográfico", "Regras gerais de acentuação"]
    },
    {
        "disciplina": "Língua Portuguesa",
        "topico": "Morfossintaxe",
        "subtopicos": ["Classes de palavras", "Estrutura e formação de palavras", "Termos da oração"]
    },
    {
        "disciplina": "Língua Portuguesa",
        "topico": "Crase e Regência",
        "subtopicos": ["Regência verbal e nominal", "Casos obrigatórios e proibitivos de crase"]
    },
    {
        "disciplina": "Língua Portuguesa",
        "topico": "Concordância Verbal e Nominal",
        "subtopicos": ["Regra geral do sujeito", "Casos especiais de concordância"]
    },
    {
        "disciplina": "Língua Portuguesa",
        "topico": "Pontuação",
        "subtopicos": ["Emprego da vírgula", "Dois pontos e ponto e vírgula"]
    },
    {
        "disciplina": "Raciocínio Lógico e Matemática",
        "topico": "Lógica Proposicional e Conectivos",
        "subtopicos": ["Tabelas-verdade", "Negação e equivalência lógica", "Argumentação"]
    },
    {
        "disciplina": "Raciocínio Lógico e Matemática",
        "topico": "Matemática Básica e Financeira",
        "subtopicos": ["Regra de três simples e composta", "Porcentagem", "Juros simples"]
    },
    {
        "disciplina": "Noções de Informática",
        "topico": "Sistemas Operacionais e Arquivos",
        "subtopicos": ["Windows 10/11", "Manipulação de arquivos e pastas", "Atalhos"]
    },
    {
        "disciplina": "Noções de Informática",
        "topico": "Suíte de Escritório (Office)",
        "subtopicos": ["Microsoft Word e Excel", "Fórmulas básicas", "Edição e formatação"]
    },
    {
        "disciplina": "Noções de Informática",
        "topico": "Segurança da Informação e Redes",
        "subtopicos": ["Navegadores", "Correio eletrônico", "Malwares e antivírus", "Backup"]
    },
    {
        "disciplina": "Direito Administrativo",
        "topico": "Princípios da Administração Pública",
        "subtopicos": ["Legalidade, Impessoalidade, Moralidade, Publicidade, Eficiência (LIMPE)"]
    },
    {
        "disciplina": "Direito Administrativo",
        "topico": "Atos Administrativos",
        "subtopicos": ["Requisitos, atributos, classificação, anulação e revogação"]
    },
    {
        "disciplina": "Direito Administrativo",
        "topico": "Licitações e Contratos (Lei 14.133/2021)",
        "subtopicos": ["Modalidades de licitação", "Critérios de julgamento", "Dispensa e inexigibilidade"]
    },
    {
        "disciplina": "Conhecimentos Específicos",
        "topico": "Redação Oficial e Correspondência",
        "subtopicos": ["Manual da Presidência da República", "Ofício, memorando, ata, relatório"]
    },
    {
        "disciplina": "Conhecimentos Específicos",
        "topico": "Arquivologia e Gestão de Documentos",
        "subtopicos": ["Teoria das três idades", "Classificação, conservação e métodos de arquivamento"]
    },
    {
        "disciplina": "Conhecimentos Específicos",
        "topico": "Atendimento ao Público e Relações Humanas",
        "subtopicos": ["Qualidade no atendimento ao cidadão", "Comunicação interpessoal", "Ética profissional"]
    }
]

def parse_edital_pdf_or_text(pdf_path: Optional[str] = None, text_content: Optional[str] = None, cargo_alvo: str = "Assistente Administrativo", orgao: str = "Concurso Geral", ano: int = 2026) -> Dict[str, Any]:
    full_text = ""
    if pdf_path:
        doc = pymupdf.open(pdf_path)
        for page in doc:
            full_text += clean_pdf_text(page.get_text()) + "\n"
    elif text_content:
        full_text = text_content
    else:
        full_text = ""

    municipio = detect_local_law(full_text)
    
    # Disciplinas detectadas
    disciplinas_detectadas = []
    upper_text = full_text.upper()
    for disc, kws in DISCIPLINA_KEYWORDS.items():
        for kw in kws:
            if kw in upper_text:
                if disc not in disciplinas_detectadas:
                    disciplinas_detectadas.append(disc)
                break

    # Se não detectou disciplinas pelo texto bruto, atribui o currículo padrão de concurso administrativo
    if not disciplinas_detectadas:
        disciplinas_detectadas = [
            "Língua Portuguesa",
            "Raciocínio Lógico e Matemática",
            "Noções de Informática",
            "Direito Administrativo",
            "Conhecimentos Específicos"
        ]

    # Filtrar tópicos que pertencem às disciplinas exigidas pelo edital
    topicos_ativos = [t for t in DEFAULT_EDITAL_TOPICOS if t["disciplina"] in disciplinas_detectadas]

    # Tópicos adicionais extraídos das linhas do edital
    linhas = [l.strip() for l in full_text.split("\n") if len(l.strip()) > 5]
    for l in linhas:
        if any(w in l.lower() for w in ["lei nº", "lei federal", "estatuto", "código de ética"]):
            # Adicionar como tópico de legislação
            topicos_ativos.append({
                "disciplina": "Legislação",
                "topico": l[:80],
                "subtopicos": []
            })

    edital_data = {
        "id": f"EDITAL-{str(uuid.uuid4())[:8]}",
        "titulo": f"Edital {orgao} - {cargo_alvo}",
        "orgao": orgao,
        "cargo": cargo_alvo,
        "ano": ano,
        "municipio": municipio,
        "disciplinas_exigidas": disciplinas_detectadas,
        "legislacoes_locais": [municipio] if municipio else [],
        "topicos": topicos_ativos,
        "raw_text": full_text[:2000] if full_text else ""
    }
    return edital_data
