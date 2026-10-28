import os
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Any

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.config import BASE_DIR, FRONTEND_DIR, DATA_DIR
from backend.database import (
    init_db, get_all_users, get_user_by_id, get_user_by_email,
    create_user, update_user, toggle_user_status, delete_user,
    get_all_questions, get_question_by_id, record_resposta,
    get_respostas_by_user, get_caderno_erros, get_active_edital,
    save_edital, get_simulados_by_user, check_password
)
from backend.auth import (
    create_access_token, get_current_user_from_token,
    require_active_user, require_admin
)
from backend.models import (
    UserLogin, UserCreate, UserUpdate, RespostaSubmissao,
    SimuladoCreateRequest, SimuladoFinalizarRequest
)
from backend.filter_engine import aplicar_filtro_estrito
from backend.parsers.edital_parser import parse_edital_pdf_or_text
from backend.simulados import (
    gerar_simulado_geral, finalizar_e_corrigir_simulado
)

# Inicializa banco de dados
init_db()

app = FastAPI(
    title="EdTech Concursos SaaS",
    description="Plataforma de Caderno de Questões Inteligente, Filtro Estrito de Edital e Ciclo de Simulados",
    version="2.0.0"
)

# CORS para desenvolvimento
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# 1. ROTAS DE AUTENTICAÇÃO
# -------------------------------------------------------------

@app.post("/api/auth/login")
def login(creds: UserLogin):
    user = get_user_by_email(creds.email)
    if not user or not check_password(creds.senha, user.get("senha_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos."
        )
    
    token = create_access_token(
        user_id=user["id"],
        role=user.get("role", "aluno"),
        status=user.get("status", "ativo")
    )
    
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "nome": user.get("nome"),
            "email": user.get("email"),
            "telefone": user.get("telefone", ""),
            "role": user.get("role", "aluno"),
            "status": user.get("status", "ativo"),
            "data_criacao": user.get("data_criacao")
        }
    }

@app.get("/api/auth/me")
def get_current_user_info(user: Dict[str, Any] = Depends(get_current_user_from_token)):
    return {
        "id": user["id"],
        "nome": user.get("nome"),
        "email": user.get("email"),
        "telefone": user.get("telefone", ""),
        "role": user.get("role", "aluno"),
        "status": user.get("status", "ativo"),
        "data_criacao": user.get("data_criacao")
    }

# -------------------------------------------------------------
# 2. ROTAS ADMINISTRATIVAS (Corte de Acesso e Gestão de Alunos)
# -------------------------------------------------------------

@app.get("/api/admin/users")
def list_users(admin: Dict[str, Any] = Depends(require_admin)):
    users = get_all_users()
    # Retorna sem os hashes de senha
    sanitized = []
    for u in users:
        item = dict(u)
        item.pop("senha_hash", None)
        sanitized.append(item)
    return sanitized

@app.post("/api/admin/users")
def admin_create_user(payload: UserCreate, admin: Dict[str, Any] = Depends(require_admin)):
    try:
        new_u = create_user(
            nome=payload.nome,
            email=payload.email,
            senha=payload.senha,
            telefone=payload.telefone or "",
            role=payload.role or "aluno",
            status=payload.status or "ativo",
            data_expiracao=payload.data_expiracao,
            notas=payload.notas_admin or ""
        )
        item = dict(new_u)
        item.pop("senha_hash", None)
        return item
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/admin/users/{user_id}")
def admin_update_user(user_id: str, payload: UserUpdate, admin: Dict[str, Any] = Depends(require_admin)):
    updates = payload.dict(exclude_unset=True)
    updated = update_user(user_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    item = dict(updated)
    item.pop("senha_hash", None)
    return item

@app.post("/api/admin/users/{user_id}/toggle-status")
def admin_toggle_status(user_id: str, admin: Dict[str, Any] = Depends(require_admin)):
    """Permite ao administrador cortar ou reativar o acesso de um aluno imediatamente."""
    updated = toggle_user_status(user_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return {
        "id": updated["id"],
        "email": updated["email"],
        "novo_status": updated["status"],
        "mensagem": f"Acesso do usuário {updated['email']} alterado para: {updated['status'].upper()}"
    }

@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(user_id: str, admin: Dict[str, Any] = Depends(require_admin)):
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="Não é permitido excluir o usuário administrador ativo.")
    success = delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return {"mensagem": "Usuário excluído com sucesso."}

# -------------------------------------------------------------
# 3. ROTAS DO CADERNO DE QUESTÕES & FILTRO ESTRITO
# -------------------------------------------------------------

@app.get("/api/questoes")
def get_questoes(
    banca: Optional[str] = None,
    disciplina: Optional[str] = None,
    topico: Optional[str] = None,
    status_resposta: Optional[str] = "todas",  # todas, pendentes, resolvidas
    termo: Optional[str] = None,
    user: Dict[str, Any] = Depends(require_active_user)
):
    all_q = get_all_questions()
    edital = get_active_edital(user["id"])
    
    # 1. Aplicar filtro estrito do edital ativo
    if edital:
        aprovadas, _, _ = aplicar_filtro_estrito(all_q, edital)
    else:
        aprovadas = all_q

    # 2. Obter histórico de respostas do usuário
    user_respostas = get_respostas_by_user(user["id"])

    # 3. Aplicar filtros adicionais de busca
    resultados = []
    for q in aprovadas:
        qid = q["id"]
        resp_aluno = user_respostas.get(qid)
        
        # Filtro de banca
        if banca and banca.lower() != "todas" and q.get("banca", "").lower() != banca.lower():
            continue
            
        # Filtro de disciplina
        if disciplina and disciplina.lower() != "todas" and disciplina.lower() not in q.get("disciplina", "").lower():
            continue

        # Filtro de tópico
        if topico and topico.lower() != "todos" and topico.lower() not in q.get("topico_edital", "").lower():
            continue

        # Filtro de status de resposta
        if status_resposta == "resolvidas" and not resp_aluno:
            continue
        elif status_resposta == "pendentes" and resp_aluno:
            continue

        # Busca por termo
        if termo:
            t_lower = termo.lower()
            enun = q.get("enunciado", "").lower()
            top = q.get("topico_edital", "").lower()
            if t_lower not in enun and t_lower not in top:
                continue

        item = dict(q)
        if resp_aluno:
            item["respondida"] = True
            item["resposta_aluno"] = resp_aluno.get("alternativa_selecionada")
            item["acertou"] = resp_aluno.get("correto")
        else:
            item["respondida"] = False
            item["resposta_aluno"] = None
            item["acertou"] = None
            
        resultados.append(item)

    return {
        "total": len(resultados),
        "questoes": resultados
    }

@app.post("/api/questoes/{questao_id}/responder")
def responder_questao(
    questao_id: str,
    payload: RespostaSubmissao,
    user: Dict[str, Any] = Depends(require_active_user)
):
    q = get_question_by_id(questao_id)
    if not q:
        raise HTTPException(status_code=404, detail="Questão não encontrada.")

    gabarito_oficial = q.get("gabarito_oficial", "A").upper()
    anulada = q.get("anulada", False)
    marcada = payload.alternativa_selecionada.upper().strip()

    correto = (anulada or marcada == gabarito_oficial)
    
    # Grava no banco e alimenta o Caderno de Erros se for incorreta
    record_resposta(
        user_id=user["id"],
        questao_id=questao_id,
        alternativa_selecionada=marcada,
        correto=correto,
        gabarito_oficial=gabarito_oficial,
        origem=payload.origem
    )

    if anulada:
        msg = "Questão ANULADA pela banca organizadora. Pontuação atribuída a todos os candidatos."
    elif correto:
        msg = f"Parabéns! Resposta correta: Alternativa {gabarito_oficial}."
    else:
        msg = f"Incorreta. Você marcou '{marcada}'. O gabarito oficial da banca é a alternativa '{gabarito_oficial}'."

    return {
        "questao_id": questao_id,
        "alternativa_selecionada": marcada,
        "gabarito_oficial": gabarito_oficial,
        "correto": correto,
        "anulada": anulada,
        "topico_edital": q.get("topico_edital", "Geral"),
        "disciplina": q.get("disciplina", "Geral"),
        "mensagem": msg
    }

# -------------------------------------------------------------
# 4. CADERNO DE ERROS
# -------------------------------------------------------------

@app.get("/api/caderno-erros")
def listar_caderno_erros(user: Dict[str, Any] = Depends(require_active_user)):
    erros = get_caderno_erros(user["id"])
    return {
        "total_erros": len(erros),
        "questoes": erros
    }

# -------------------------------------------------------------
# 5. RAIO-X & FORA DO EDITAL
# -------------------------------------------------------------

@app.get("/api/edital/analise")
def analise_edital(user: Dict[str, Any] = Depends(require_active_user)):
    all_q = get_all_questions()
    edital = get_active_edital(user["id"])
    if not edital:
        raise HTTPException(status_code=404, detail="Nenhum edital cadastrado no sistema.")
        
    aprovadas, descartadas, stats = aplicar_filtro_estrito(all_q, edital)
    return {
        "edital": {
            "titulo": edital.get("titulo"),
            "cargo": edital.get("cargo"),
            "orgao": edital.get("orgao"),
            "ano": edital.get("ano"),
            "municipio": edital.get("municipio"),
            "disciplinas_exigidas": edital.get("disciplinas_exigidas", []),
        },
        "estatisticas": stats,
        "fora_do_edital": descartadas
    }

@app.get("/api/edital/atual")
def obter_edital_atual(user: Dict[str, Any] = Depends(require_active_user)):
    edital = get_active_edital(user["id"])
    if not edital:
        return {"edital": None}
    return {"edital": edital}

@app.post("/api/edital/upload")
async def upload_novo_edital(
    file: Optional[UploadFile] = File(None),
    cargo_alvo: str = Form("Assistente Administrativo"),
    orgao: str = Form("Concurso Público"),
    ano: int = Form(2026),
    user: Dict[str, Any] = Depends(require_active_user)
):
    temp_path = None
    if file:
        temp_dir = DATA_DIR / "uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / file.filename
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
    edital = parse_edital_pdf_or_text(
        pdf_path=str(temp_path) if temp_path else None,
        cargo_alvo=cargo_alvo,
        orgao=orgao,
        ano=ano
    )
    save_edital(edital)
    
    # Recalcula filtro com a base de questões
    all_q = get_all_questions()
    aprovadas, descartadas, stats = aplicar_filtro_estrito(all_q, edital)
    
    return {
        "mensagem": "Edital processado e mapeado com sucesso!",
        "edital": edital,
        "estatisticas": stats
    }

# -------------------------------------------------------------
# 6. CICLO DE SIMULADOS
# -------------------------------------------------------------

@app.post("/api/simulados/gerar")
def gerar_novo_simulado(
    payload: SimuladoCreateRequest,
    user: Dict[str, Any] = Depends(require_active_user)
):
    simulado = gerar_simulado_geral(
        user_id=user["id"],
        quantidade_questoes=payload.quantidade_questoes,
        tempo_minutos=payload.tempo_minutos,
        apenas_ineditas=payload.apenas_ineditas,
        banca_filtro=payload.banca_filtro or "todas",
        disciplinas_filtro=payload.disciplinas_filtro
    )
    return simulado

@app.post("/api/simulados/finalizar")
def finalizar_simulado(
    payload: SimuladoFinalizarRequest,
    user: Dict[str, Any] = Depends(require_active_user)
):
    try:
        resultado = finalizar_e_corrigir_simulado(
            simulado_id=payload.simulado_id,
            user_id=user["id"],
            tempo_gasto_segundos=payload.tempo_gasto_segundos,
            respostas_aluno=payload.respostas
        )
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/simulados/historico")
def historico_simulados(user: Dict[str, Any] = Depends(require_active_user)):
    simulados = get_simulados_by_user(user["id"])
    return {
        "total": len(simulados),
        "simulados": simulados[::-1]  # Mais recentes primeiro
    }

# -------------------------------------------------------------
# 7. ESTATÍSTICAS DO ALUNO (DASHBOARD)
# -------------------------------------------------------------

@app.get("/api/stats")
def obter_estatisticas(user: Dict[str, Any] = Depends(require_active_user)):
    all_q = get_all_questions()
    edital = get_active_edital(user["id"])
    aprovadas = all_q
    if edital:
        aprovadas, _, _ = aplicar_filtro_estrito(all_q, edital)

    user_respostas = get_respostas_by_user(user["id"])
    
    total_respondidas = len(user_respostas)
    total_acertos = sum(1 for r in user_respostas.values() if r.get("correto"))
    total_erros = total_respondidas - total_acertos
    
    taxa_acerto = round((total_acertos / total_respondidas) * 100, 1) if total_respondidas > 0 else 0.0

    simulados = get_simulados_by_user(user["id"])
    media_simulados = 0.0
    if simulados:
        media_simulados = round(sum(s.get("nota_percentual", 0) for s in simulados) / len(simulados), 1)

    return {
        "total_questoes_banco": len(all_q),
        "total_questoes_edital": len(aprovadas),
        "total_respondidas": total_respondidas,
        "total_acertos": total_acertos,
        "total_erros": total_erros,
        "taxa_acerto": taxa_acerto,
        "total_restantes": max(0, len(aprovadas) - total_respondidas),
        "total_simulados_feitos": len(simulados),
        "media_simulados": media_simulados
    }

@app.get("/api/desempenho")
def obter_desempenho_completo(user: Dict[str, Any] = Depends(require_active_user)):
    all_q = get_all_questions()
    q_map = {q["id"]: q for q in all_q}
    
    edital = get_active_edital(user["id"])
    aprovadas = all_q
    if edital:
        aprovadas, _, _ = aplicar_filtro_estrito(all_q, edital)

    user_respostas = get_respostas_by_user(user["id"])
    
    total_respondidas = len(user_respostas)
    total_acertos = sum(1 for r in user_respostas.values() if r.get("correto"))
    total_erros = total_respondidas - total_acertos
    taxa_acerto = round((total_acertos / total_respondidas) * 100, 1) if total_respondidas > 0 else 0.0

    # Agrupamento por disciplina
    disciplinas_stats = {}
    for q in aprovadas:
        d = q.get("disciplina", "Conhecimentos Específicos")
        if d not in disciplinas_stats:
            disciplinas_stats[d] = {
                "total_edital": 0,
                "feitas": 0,
                "acertos": 0,
                "erros": 0,
                "taxa_acerto": 0.0
            }
        disciplinas_stats[d]["total_edital"] += 1

    # Contabilizar respostas por disciplina
    for qid, resp in user_respostas.items():
        q_obj = q_map.get(qid)
        if q_obj:
            d = q_obj.get("disciplina", "Conhecimentos Específicos")
            if d not in disciplinas_stats:
                disciplinas_stats[d] = {
                    "total_edital": 0,
                    "feitas": 0,
                    "acertos": 0,
                    "erros": 0,
                    "taxa_acerto": 0.0
                }
            disciplinas_stats[d]["feitas"] += 1
            if resp.get("correto"):
                disciplinas_stats[d]["acertos"] += 1
            else:
                disciplinas_stats[d]["erros"] += 1

    for d, s in disciplinas_stats.items():
        if s["feitas"] > 0:
            s["taxa_acerto"] = round((s["acertos"] / s["feitas"]) * 100, 1)

    simulados = get_simulados_by_user(user["id"])
    media_simulados = round(sum(s.get("nota_percentual", 0) for s in simulados) / len(simulados), 1) if simulados else 0.0

    # Histórico de atividades recentes
    atividades_recentes = []
    # Ordenar respostas do usuário por timestamp decrescente
    respostas_ordenadas = sorted(user_respostas.values(), key=lambda x: x.get("timestamp", ""), reverse=True)
    for r in respostas_ordenadas[:20]:
        q_obj = q_map.get(r.get("questao_id"))
        if q_obj:
            atividades_recentes.append({
                "questao_id": q_obj["id"],
                "numero": q_obj.get("numero"),
                "banca": q_obj.get("banca"),
                "ano": q_obj.get("ano"),
                "disciplina": q_obj.get("disciplina"),
                "topico_edital": q_obj.get("topico_edital"),
                "alternativa_selecionada": r.get("alternativa_selecionada"),
                "gabarito_oficial": r.get("gabarito_oficial"),
                "correto": r.get("correto"),
                "origem": r.get("origem", "caderno"),
                "timestamp": r.get("timestamp")
            })

    return {
        "resumo": {
            "total_questoes_banco": len(all_q),
            "total_questoes_edital": len(aprovadas),
            "total_feitas": total_respondidas,
            "total_acertos": total_acertos,
            "total_erros": total_erros,
            "taxa_acerto": taxa_acerto,
            "total_restantes": max(0, len(aprovadas) - total_respondidas),
            "total_simulados_feitos": len(simulados),
            "media_simulados": media_simulados
        },
        "desempenho_por_disciplina": disciplinas_stats,
        "atividades_recentes": atividades_recentes
    }

# -------------------------------------------------------------
# 8. FRONTEND SPA ESTÁTICO
# -------------------------------------------------------------

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
