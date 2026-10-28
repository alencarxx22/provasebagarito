import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"
DATA_DIR = BASE_DIR / "dados_processados"
DATA_DIR.mkdir(parents=True, exist_ok=True)

USERS_FILE = DATA_DIR / "usuarios.json"
QUESTIONS_FILE = DATA_DIR / "questoes_banco.json"
EDITAIS_FILE = DATA_DIR / "editais.json"
SIMULADOS_FILE = DATA_DIR / "simulados.json"
RESPOSTAS_FILE = DATA_DIR / "respostas_alunos.json"

# Master Admin Credentials
DEFAULT_ADMIN_EMAIL = "ap202do14bis@gmail.com"
DEFAULT_ADMIN_PASS = "Banana02@"
DEFAULT_ADMIN_NAME = "Administrador Master"
DEFAULT_ADMIN_PHONE = "+55 (11) 99999-9999"

JWT_SECRET = "edtech-concursos-saas-super-secret-key-2026"
JWT_ALGORITHM = "HS256"
