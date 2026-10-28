import os
from pathlib import Path
from backend.config import BASE_DIR
from backend.parsers.prova_parser import parse_full_exam
from backend.database import save_all_questions, get_all_questions, init_db

PROVAS_CONFIG = [
    {
        "prova": "agente administrativo ibgp1.pdf",
        "gabarito": "gabarito_oficial ibgp1.pdf",
        "banca": "IBGP",
        "orgao": "Prefeitura de Mário Campos/MG",
        "ano": 2020,
        "cargo": "Agente Administrativo III",
        "cargo_kw": "301"
    },
    {
        "prova": "agente_de_servicos_administrativos ibgp2.pdf",
        "gabarito": "gabarito_definitivo ibgp2.pdf",
        "banca": "IBGP",
        "orgao": "Prefeitura Municipal",
        "ano": 2021,
        "cargo": "Agente de Serviços Administrativos",
        "cargo_kw": "ADMINISTRAT"
    },
    {
        "prova": "analista_administrativo ibgp3.pdf",
        "gabarito": "gabarito_definitivo ibgp3.pdf",
        "banca": "IBGP",
        "orgao": "Conselho Regional",
        "ano": 2021,
        "cargo": "Analista Administrativo",
        "cargo_kw": "ADMINISTRAT"
    },
    {
        "prova": "analista_administrativo ibgp4.pdf",
        "gabarito": "gabaritos ibgp4.pdf",
        "banca": "IBGP",
        "orgao": "Prefeitura Municipal",
        "ano": 2022,
        "cargo": "Analista Administrativo",
        "cargo_kw": "ADMINISTRAT"
    },
    {
        "prova": "assistente_administrativo ibgp5.pdf",
        "gabarito": "gabaritos ibgp5.pdf",
        "banca": "IBGP",
        "orgao": "Câmara Municipal",
        "ano": 2023,
        "cargo": "Assistente Administrativo",
        "cargo_kw": "ADMINISTRAT"
    },
    {
        "prova": "administracao cesgranrio1.pdf",
        "gabarito": "gabarito cesgranrio1.pdf",
        "banca": "CESGRANRIO",
        "orgao": "TRANSPETRO",
        "ano": 2023,
        "cargo": "Administração",
        "cargo_kw": "ADMINISTRAÇÃO"
    },
    {
        "prova": "prova_5_administracao cesgranrio2.pdf",
        "gabarito": "gabaritos cesgranrio2.pdf",
        "banca": "CESGRANRIO",
        "orgao": "CHESF",
        "ano": 2012,
        "cargo": "Administração",
        "cargo_kw": "ADMINISTRA"
    },
    {
        "prova": "assistente_administrativo fgv1.pdf",
        "gabarito": "gabarito fgv1.pdf",
        "banca": "FGV",
        "orgao": "EBSERH",
        "ano": 2024,
        "cargo": "Assistente Administrativo",
        "cargo_kw": "ASSISTENTE ADMINISTRATIVO"
    },
    {
        "prova": "assistente_administrativo fgv2.pdf",
        "gabarito": "gabarito fgv2.pdf",
        "banca": "FGV",
        "orgao": "AMAZUL",
        "ano": 2025,
        "cargo": "Assistente Administrativo",
        "cargo_kw": "ASSISTENTE ADMINISTRATIVO"
    },
    {
        "prova": "administrativo fundatec1.pdf",
        "gabarito": "gabarito fundatec1.pdf",
        "banca": "FUNDATEC",
        "orgao": "Prefeitura de Porto Alegre/RS",
        "ano": 2026,
        "cargo": "Assistente Administrativo",
        "cargo_kw": "865"
    },
    {
        "prova": "administrativo-prova banca copese1.pdf",
        "gabarito": "gabarito_preliminar copese1.pdf",
        "banca": "COPESE",
        "orgao": "Prefeitura de Palmas/TO",
        "ano": 2024,
        "cargo": "Assistente Administrativo",
        "cargo_kw": "ASSISTENTE ADMINISTRATIVO"
    },
    {
        "prova": "assistente_administrativo fafipa1.pdf",
        "gabarito": "gabarito fafipa1.pdf",
        "banca": "FAFIPA",
        "orgao": "Câmara de Jaguariaíva/PR",
        "ano": 2026,
        "cargo": "Assistente Administrativo",
        "cargo_kw": "8682"
    }
]

def run_ingestion():
    init_db()
    todas_questoes = []
    print("Iniciando ingestão de provas e gabaritos...")
    
    for item in PROVAS_CONFIG:
        prova_path = BASE_DIR / item["prova"]
        gab_path = BASE_DIR / item["gabarito"]
        
        if not prova_path.exists() or not gab_path.exists():
            print(f"[-] Arquivo não encontrado: {item['prova']} ou {item['gabarito']}")
            continue
            
        print(f"[+] Processando {item['banca']} - {item['cargo']} ({item['ano']})...")
        try:
            questoes = parse_full_exam(
                prova_pdf_path=str(prova_path),
                gabarito_pdf_path=str(gab_path),
                banca=item["banca"],
                orgao=item["orgao"],
                ano=item["ano"],
                cargo=item["cargo"],
                cargo_kw=item["cargo_kw"]
            )
            print(f"    -> {len(questoes)} questões extraídas com sucesso!")
            todas_questoes.extend(questoes)
        except Exception as e:
            print(f"    [!] Erro ao processar {item['prova']}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\nTotal geral de questões extraídas e catalogadas: {len(todas_questoes)}")
    save_all_questions(todas_questoes)
    return todas_questoes

if __name__ == "__main__":
    run_ingestion()
