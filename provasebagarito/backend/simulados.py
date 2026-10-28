import random
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.database import (
    get_all_questions, get_respostas_by_user, record_resposta,
    save_simulado_attempt, get_simulados_by_user, get_active_edital
)
from backend.filter_engine import aplicar_filtro_estrito

ACTIVE_SIMULADOS_CACHE: Dict[str, Dict[str, Any]] = {}

def gerar_simulado_geral(
    user_id: str,
    quantidade_questoes: int = 30,
    tempo_minutos: int = 120,
    apenas_ineditas: bool = True,
    banca_filtro: str = "todas",
    disciplinas_filtro: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Gera um simulado personalizado cronometrado com questões estritamente alinhadas
    ao edital do aluno, priorizando questões inéditas (ainda não resolvidas).
    """
    todas_questoes = get_all_questions()
    edital = get_active_edital(user_id) or {
        "disciplinas_exigidas": ["Língua Portuguesa", "Raciocínio Lógico e Matemática", "Noções de Informática", "Direito Administrativo", "Conhecimentos Específicos"],
        "municipio": None,
        "topicos": []
    }
    
    # 1. Aplicar filtro estrito do edital
    aprovadas, _, _ = aplicar_filtro_estrito(todas_questoes, edital)
    
    # 2. Filtrar por banca se especificada
    if banca_filtro and banca_filtro.lower() != "todas":
        aprovadas = [q for q in aprovadas if q.get("banca", "").lower() == banca_filtro.lower()]
        
    # 3. Filtrar por disciplinas se especificado
    if disciplinas_filtro:
        disc_filtro_lower = [d.lower() for d in disciplinas_filtro]
        aprovadas = [q for q in aprovadas if any(df in q.get("disciplina", "").lower() for df in disc_filtro_lower)]

    # 4. Separar questões inéditas para este aluno
    respostas_usuario = get_respostas_by_user(user_id)
    questoes_resolvidas_ids = set(respostas_usuario.keys())

    ineditas = [q for q in aprovadas if q["id"] not in questoes_resolvidas_ids]
    ja_vistas = [q for q in aprovadas if q["id"] in questoes_resolvidas_ids]

    # Embaralhar para evitar viés de ordem
    random.shuffle(ineditas)
    random.shuffle(ja_vistas)

    pool_selecionado = []
    if apenas_ineditas:
        pool_selecionado = ineditas[:quantidade_questoes]
        # Se não houver inéditas suficientes, completa com já vistas
        if len(pool_selecionado) < quantidade_questoes:
            restante = quantidade_questoes - len(pool_selecionado)
            pool_selecionado.extend(ja_vistas[:restante])
    else:
        # Mistura equilibrada
        combinadas = ineditas + ja_vistas
        random.shuffle(combinadas)
        pool_selecionado = combinadas[:quantidade_questoes]

    if not pool_selecionado:
        # Fallback de segurança se a base filtrada estiver vazia
        pool_selecionado = todas_questoes[:quantidade_questoes]

    simulado_id = f"SIM-{str(uuid.uuid4())[:8]}"
    
    # Montar itens do simulado (sem revelar gabarito antes de responder)
    itens_para_aluno = []
    itens_completos = []

    for idx, q in enumerate(pool_selecionado, start=1):
        item_aluno = {
            "numero_ordem": idx,
            "questao_id": q["id"],
            "banca": q.get("banca", ""),
            "disciplina": q.get("disciplina", ""),
            "topico_edital": q.get("topico_edital", ""),
            "enunciado": q.get("enunciado", ""),
            "texto_apoio": q.get("texto_apoio"),
            "texto_apoio_titulo": q.get("texto_apoio_titulo"),
            "texto_apoio_aplicavel": q.get("texto_apoio_aplicavel"),
            "alternativas": q.get("alternativas", []),
            "anulada": q.get("anulada", False)
        }
        item_completo = dict(item_aluno)
        item_completo["gabarito_oficial"] = q.get("gabarito_oficial", "A")
        
        itens_para_aluno.append(item_aluno)
        itens_completos.append(item_completo)

    simulado_data = {
        "id": simulado_id,
        "id_aluno": user_id,
        "titulo": f"Simulado Geral - {len(itens_para_aluno)} Questões ({datetime.now().strftime('%d/%m/%Y')})",
        "data_inicio": datetime.now().isoformat(),
        "tempo_total_segundos": tempo_minutos * 60,
        "quantidade_questoes": len(itens_para_aluno),
        "status": "em_andamento",
        "questoes_segredo": itens_completos
    }
    
    # Salvar em cache de simulados ativos
    ACTIVE_SIMULADOS_CACHE[simulado_id] = simulado_data

    return {
        "simulado_id": simulado_id,
        "titulo": simulado_data["titulo"],
        "data_inicio": simulado_data["data_inicio"],
        "tempo_total_segundos": simulado_data["tempo_total_segundos"],
        "quantidade_questoes": len(itens_para_aluno),
        "total_ineditas": len([q for q in pool_selecionado if q["id"] not in questoes_resolvidas_ids]),
        "questoes": itens_para_aluno
    }

def finalizar_e_corrigir_simulado(
    simulado_id: str,
    user_id: str,
    tempo_gasto_segundos: int,
    respostas_aluno: Dict[str, str]
) -> Dict[str, Any]:
    """
    Finaliza o simulado, calcula a nota geral, o tempo gasto, o desempenho por matéria
    e alimenta o Caderno de Erros automaticamente com as questões erradas.
    """
    simulado_ativo = ACTIVE_SIMULADOS_CACHE.get(simulado_id)
    if not simulado_ativo:
        raise ValueError("Simulado não encontrado ou já finalizado.")

    questoes_originais = simulado_ativo.get("questoes_segredo", [])
    
    total_acertos = 0
    total_erros = 0
    total_em_branco = 0
    
    disciplinas_stats: Dict[str, Dict[str, Any]] = {}
    questoes_resultado = []

    for item in questoes_originais:
        qid = item["questao_id"]
        gabarito = item.get("gabarito_oficial", "A")
        disc = item.get("disciplina", "Geral")
        anulada = item.get("anulada", False)
        
        if disc not in disciplinas_stats:
            disciplinas_stats[disc] = {"total": 0, "acertos": 0, "erros": 0, "em_branco": 0}
        disciplinas_stats[disc]["total"] += 1

        resposta = respostas_aluno.get(qid, "").upper().strip()
        
        correto = False
        if anulada:
            correto = True
            total_acertos += 1
            disciplinas_stats[disc]["acertos"] += 1
        elif not resposta:
            total_em_branco += 1
            disciplinas_stats[disc]["em_branco"] += 1
        elif resposta == gabarito:
            correto = True
            total_acertos += 1
            disciplinas_stats[disc]["acertos"] += 1
        else:
            correto = False
            total_erros += 1
            disciplinas_stats[disc]["erros"] += 1
            
        # Registrar resposta do aluno no banco central
        record_resposta(
            user_id=user_id,
            questao_id=qid,
            alternativa_selecionada=resposta or "EM_BRANCO",
            correto=correto,
            gabarito_oficial=gabarito,
            origem="simulado"
        )

        res_item = dict(item)
        res_item["resposta_aluno"] = resposta
        res_item["correto"] = correto
        questoes_resultado.append(res_item)

    total_q = len(questoes_originais)
    nota_percentual = round((total_acertos / total_q) * 100, 1) if total_q > 0 else 0.0

    # Calcular percentual por disciplina
    for disc, s in disciplinas_stats.items():
        s["percentual"] = round((s["acertos"] / s["total"]) * 100, 1) if s["total"] > 0 else 0.0

    resultado_final = {
        "id": simulado_id,
        "id_aluno": user_id,
        "titulo": simulado_ativo.get("titulo", "Simulado Geral"),
        "data_inicio": simulado_ativo.get("data_inicio"),
        "data_finalizacao": datetime.now().isoformat(),
        "tempo_total_segundos": simulado_ativo.get("tempo_total_segundos", 7200),
        "tempo_gasto_segundos": tempo_gasto_segundos,
        "total_questoes": total_q,
        "total_acertos": total_acertos,
        "total_erros": total_erros,
        "total_em_branco": total_em_branco,
        "nota_percentual": nota_percentual,
        "desempenho_por_disciplina": disciplinas_stats,
        "questoes": questoes_resultado
    }

    # Persistir no histórico
    save_simulado_attempt(resultado_final)
    
    # Remover do cache de ativos
    ACTIVE_SIMULADOS_CACHE.pop(simulado_id, None)

    return resultado_final
