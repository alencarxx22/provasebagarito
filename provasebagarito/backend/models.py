from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

class UserBase(BaseModel):
    nome: str
    email: str
    telefone: Optional[str] = ""
    role: str = "aluno"  # "admin" | "aluno"
    status: str = "ativo"  # "ativo" | "bloqueado"

class UserCreate(UserBase):
    senha: str
    data_expiracao: Optional[str] = None
    notas_admin: Optional[str] = ""

class UserUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[str] = None
    senha: Optional[str] = None
    telefone: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    data_expiracao: Optional[str] = None
    notas_admin: Optional[str] = None

class UserResponse(UserBase):
    id: str
    data_criacao: str
    data_expiracao: Optional[str] = None
    notas_admin: Optional[str] = ""

class UserLogin(BaseModel):
    email: str
    senha: str

class Alternativa(BaseModel):
    letra: str  # A, B, C, D, E
    texto: str

class Questao(BaseModel):
    id: str
    banca: str
    orgao: str
    ano: int
    cargo: str
    disciplina: str
    topico_edital: str = "Geral"
    numero: int
    enunciado: str
    alternativas: List[Alternativa]
    gabarito_oficial: str  # A, B, C, D, E
    anulada: bool = False
    explicacao: Optional[str] = ""
    municipio_especifico: Optional[str] = None
    fonte_arquivo: Optional[str] = None
    texto_apoio: Optional[str] = None
    texto_apoio_titulo: Optional[str] = None
    texto_apoio_aplicavel: Optional[str] = None

class RespostaSubmissao(BaseModel):
    questao_id: str
    alternativa_selecionada: str
    origem: str = "caderno"  # "caderno" | "simulado"

class RespostaFeedback(BaseModel):
    questao_id: str
    alternativa_selecionada: str
    gabarito_oficial: str
    correto: bool
    anulada: bool
    topico_edital: str
    disciplina: str
    mensagem: str

class EditalTopico(BaseModel):
    disciplina: str
    topico: str
    subtopicos: List[str] = []

class EditalEstruturado(BaseModel):
    id: str
    titulo: str
    orgao: str
    cargo: str
    ano: int
    municipio: Optional[str] = None
    disciplinas_exigidas: List[str] = []
    legislacoes_locais: List[str] = []
    topicos: List[EditalTopico] = []
    raw_text: Optional[str] = ""

class SimuladoConfig(BaseModel):
    dia_semana: str = "Domingo"  # Segunda, Terça, etc.
    horario: str = "09:00"
    quantidade_questoes: int = 30
    tempo_minutos: int = 120
    bancas_preferidas: List[str] = []

class SimuladoQuestaoItem(BaseModel):
    questao_id: str
    numero_ordem: int
    banca: str
    disciplina: str
    topico_edital: str
    enunciado: str
    texto_apoio: Optional[str] = None
    texto_apoio_titulo: Optional[str] = None
    texto_apoio_aplicavel: Optional[str] = None
    alternativas: List[Alternativa]
    resposta_aluno: Optional[str] = None
    gabarito_oficial: Optional[str] = None
    correto: Optional[bool] = None

class SimuladoCreateRequest(BaseModel):
    quantidade_questoes: int = 30
    tempo_minutos: int = 120
    apenas_ineditas: bool = True
    banca_filtro: Optional[str] = "todas"
    disciplinas_filtro: Optional[List[str]] = None

class SimuladoFinalizarRequest(BaseModel):
    simulado_id: str
    tempo_gasto_segundos: int
    respostas: Dict[str, str]  # questao_id -> letra_marcada

class SimuladoResultado(BaseModel):
    id: str
    id_aluno: str
    data_criacao: str
    data_finalizacao: str
    tempo_total_segundos: int
    tempo_gasto_segundos: int
    total_questoes: int
    total_acertos: int
    total_erros: int
    total_em_branco: int
    nota_percentual: float
    desempenho_por_disciplina: Dict[str, Dict[str, Any]]
    questoes: List[SimuladoQuestaoItem]
