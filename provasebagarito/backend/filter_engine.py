from typing import List, Dict, Any, Tuple
from backend.models import Questao, EditalEstruturado

def aplicar_filtro_estrito(questoes: List[Dict[str, Any]], edital: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """
    Motor de Mapeamento com Filtro Estrito em 3 Camadas:
    1. Filtro de Matéria/Disciplina
    2. Filtro de Legislação e História Local
    3. Mapeamento de Tópicos e Raio-X
    """
    disciplinas_edital = [d.lower() for d in edital.get("disciplinas_exigidas", [])]
    municipio_aluno = (edital.get("municipio") or "").strip().lower()
    
    aprovadas = []
    descartadas = []
    raio_x = {}

    # Inicializar contadores do Raio-X por tópicos do edital
    for top in edital.get("topicos", []):
        disc = top.get("disciplina", "Geral")
        top_nome = top.get("topico", "Geral")
        if disc not in raio_x:
            raio_x[disc] = {}
        raio_x[disc][top_nome] = 0

    for q in questoes:
        disc_q = q.get("disciplina", "Conhecimentos Específicos")
        disc_q_lower = disc_q.lower()

        # Camada 1: Filtro de Matéria
        # Se a disciplina da questão não constar nas disciplinas exigidas do edital
        disciplina_permitida = False
        if not disciplinas_edital:
            disciplina_permitida = True
        else:
            for de in disciplinas_edital:
                if de in disc_q_lower or disc_q_lower in de:
                    disciplina_permitida = True
                    break
        
        if not disciplina_permitida:
            q_copia = dict(q)
            q_copia["motivo_descarte"] = f"Camada 1: Matéria ({disc_q}) não é cobrada no edital"
            q_copia["camada_descarte"] = 1
            descartadas.append(q_copia)
            continue

        # Camada 2: Filtro de Legislação / História Local
        mun_q = (q.get("municipio_especifico") or "").strip().lower()
        if mun_q:
            # Se a questão é específica de um município e o edital do aluno for de outro órgão/cidade
            if not municipio_aluno or mun_q != municipio_aluno:
                q_copia = dict(q)
                q_copia["motivo_descarte"] = f"Camada 2: Legislação ou histórico municipal restrito a {q.get('municipio_especifico')}"
                q_copia["camada_descarte"] = 2
                descartadas.append(q_copia)
                continue

        # Camada 3: Mapeamento de Tópico do Edital
        topico_atribuido = q.get("topico_edital", "Geral")
        
        # Incrementar contagem no Raio-X
        if disc_q not in raio_x:
            raio_x[disc_q] = {}
        if topico_atribuido not in raio_x[disc_q]:
            raio_x[disc_q][topico_atribuido] = 0
        raio_x[disc_q][topico_atribuido] += 1

        q_aprovada = dict(q)
        q_aprovada["filtro_status"] = "aprovada"
        q_aprovada["topico_edital_oficial"] = topico_atribuido
        aprovadas.append(q_aprovada)

    estatisticas = {
        "total_banco": len(questoes),
        "total_aprovadas": len(aprovadas),
        "total_descartadas": len(descartadas),
        "raio_x_grade": raio_x
    }

    return aprovadas, descartadas, estatisticas
