import json
import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from backend.config import (
    USERS_FILE, QUESTIONS_FILE, EDITAIS_FILE, SIMULADOS_FILE, RESPOSTAS_FILE,
    DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASS, DEFAULT_ADMIN_NAME, DEFAULT_ADMIN_PHONE
)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def check_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def _load_json(file_path: Path, default_factory=list):
    if not file_path.exists():
        data = default_factory()
        _save_json(file_path, data)
        return data
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default_factory()

def _save_json(file_path: Path, data):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_file = file_path.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    temp_file.replace(file_path)

def init_db():
    # 1. Initialize Users
    users = _load_json(USERS_FILE, list)
    admin_exists = any(u.get("email") == DEFAULT_ADMIN_EMAIL for u in users)
    if not admin_exists:
        admin_user = {
            "id": "admin-master-id",
            "nome": DEFAULT_ADMIN_NAME,
            "email": DEFAULT_ADMIN_EMAIL,
            "senha_hash": hash_password(DEFAULT_ADMIN_PASS),
            "telefone": DEFAULT_ADMIN_PHONE,
            "role": "admin",
            "status": "ativo",
            "data_criacao": datetime.now().isoformat(),
            "data_expiracao": None,
            "notas_admin": "Administrador Principal do Sistema"
        }
        users.append(admin_user)

    demo_student = any(u.get("email") == "aluno@concurso.com" for u in users)
    if not demo_student:
        users.append({
            "id": "aluno-demo-id",
            "nome": "Lucas Concurseiro",
            "email": "aluno@concurso.com",
            "senha_hash": hash_password("Aluno123@"),
            "telefone": "(31) 98765-4321",
            "role": "aluno",
            "status": "ativo",
            "data_criacao": datetime.now().isoformat(),
            "data_expiracao": None,
            "notas_admin": "Aluno Demonstração"
        })
    _save_json(USERS_FILE, users)

    # 2. Initialize other files
    _load_json(QUESTIONS_FILE, list)
    _load_json(EDITAIS_FILE, list)
    _load_json(SIMULADOS_FILE, list)
    _load_json(RESPOSTAS_FILE, list)

# ----------------- USERS -----------------

def get_all_users() -> List[Dict[str, Any]]:
    return _load_json(USERS_FILE, list)

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    users = get_all_users()
    for u in users:
        if u.get("id") == user_id:
            return u
    return None

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    users = get_all_users()
    email_clean = email.strip().lower()
    for u in users:
        if u.get("email", "").strip().lower() == email_clean:
            return u
    return None

def create_user(nome: str, email: str, senha: str, telefone: str = "", role: str = "aluno", status: str = "ativo", data_expiracao: str = None, notas: str = "") -> Dict[str, Any]:
    users = get_all_users()
    if get_user_by_email(email):
        raise ValueError(f"O email '{email}' já está cadastrado.")
    
    new_user = {
        "id": str(uuid.uuid4()),
        "nome": nome.strip(),
        "email": email.strip().lower(),
        "senha_hash": hash_password(senha),
        "telefone": telefone.strip(),
        "role": role,
        "status": status,
        "data_criacao": datetime.now().isoformat(),
        "data_expiracao": data_expiracao,
        "notas_admin": notas
    }
    users.append(new_user)
    _save_json(USERS_FILE, users)
    return new_user

def update_user(user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    users = get_all_users()
    for i, u in enumerate(users):
        if u.get("id") == user_id:
            if "senha" in updates and updates["senha"]:
                updates["senha_hash"] = hash_password(updates.pop("senha"))
            if "email" in updates:
                updates["email"] = updates["email"].strip().lower()
            users[i].update({k: v for k, v in updates.items() if v is not None})
            _save_json(USERS_FILE, users)
            return users[i]
    return None

def toggle_user_status(user_id: str) -> Optional[Dict[str, Any]]:
    users = get_all_users()
    for i, u in enumerate(users):
        if u.get("id") == user_id:
            current_status = u.get("status", "ativo")
            new_status = "bloqueado" if current_status == "ativo" else "ativo"
            users[i]["status"] = new_status
            _save_json(USERS_FILE, users)
            return users[i]
    return None

def delete_user(user_id: str) -> bool:
    users = get_all_users()
    filtered = [u for u in users if u.get("id") != user_id]
    if len(filtered) != len(users):
        _save_json(USERS_FILE, filtered)
        return True
    return False

# ----------------- QUESTÕES -----------------

def get_all_questions() -> List[Dict[str, Any]]:
    return _load_json(QUESTIONS_FILE, list)

def get_question_by_id(qid: str) -> Optional[Dict[str, Any]]:
    questions = get_all_questions()
    for q in questions:
        if q.get("id") == qid:
            return q
    return None

def save_all_questions(questions: List[Dict[str, Any]]):
    _save_json(QUESTIONS_FILE, questions)

# ----------------- RESPOSTAS / CADERNO DE ERROS -----------------

def get_all_respostas() -> List[Dict[str, Any]]:
    return _load_json(RESPOSTAS_FILE, list)

def record_resposta(user_id: str, questao_id: str, alternativa_selecionada: str, correto: bool, gabarito_oficial: str, origem: str = "caderno"):
    respostas = get_all_respostas()
    # Atualizar resposta existente ou adicionar nova
    entry = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "questao_id": questao_id,
        "alternativa_selecionada": alternativa_selecionada,
        "gabarito_oficial": gabarito_oficial,
        "correto": correto,
        "origem": origem,
        "timestamp": datetime.now().isoformat()
    }
    # Manter a última resposta do aluno para a questão
    # Remover versões antigas dessa questão para este usuário
    novas = [r for r in respostas if not (r.get("user_id") == user_id and r.get("questao_id") == questao_id)]
    novas.append(entry)
    _save_json(RESPOSTAS_FILE, novas)
    return entry

def get_respostas_by_user(user_id: str) -> Dict[str, Dict[str, Any]]:
    respostas = get_all_respostas()
    user_respostas = {}
    for r in respostas:
        if r.get("user_id") == user_id:
            user_respostas[r.get("questao_id")] = r
    return user_respostas

def get_caderno_erros(user_id: str) -> List[Dict[str, Any]]:
    user_respostas = get_respostas_by_user(user_id)
    questions = {q["id"]: q for q in get_all_questions()}
    
    erros = []
    for qid, resp in user_respostas.items():
        if not resp.get("correto") and qid in questions:
            q = dict(questions[qid])
            q["ultima_resposta_aluno"] = resp.get("alternativa_selecionada")
            q["data_resposta"] = resp.get("timestamp")
            erros.append(q)
    return erros

# ----------------- EDITAIS -----------------

def get_all_editais() -> List[Dict[str, Any]]:
    return _load_json(EDITAIS_FILE, list)

def save_edital(edital: Dict[str, Any]):
    editais = get_all_editais()
    # remove duplicate id
    editais = [e for e in editais if e.get("id") != edital.get("id")]
    editais.append(edital)
    _save_json(EDITAIS_FILE, editais)

def get_active_edital(user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    editais = get_all_editais()
    if not editais:
        return None
    # Retorna o último edital cadastrado
    return editais[-1]

# ----------------- SIMULADOS -----------------

def get_all_simulados() -> List[Dict[str, Any]]:
    return _load_json(SIMULADOS_FILE, list)

def save_simulado_attempt(attempt: Dict[str, Any]):
    simulados = get_all_simulados()
    simulados.append(attempt)
    _save_json(SIMULADOS_FILE, simulados)

def get_simulados_by_user(user_id: str) -> List[Dict[str, Any]]:
    simulados = get_all_simulados()
    return [s for s in simulados if s.get("id_aluno") == user_id]
