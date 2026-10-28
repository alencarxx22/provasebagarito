import time
import base64
import hmac
import hashlib
import json
from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, Depends, status
from backend.config import JWT_SECRET
from backend.database import get_user_by_id, get_user_by_email, check_password

def create_access_token(user_id: str, role: str, status: str, expires_in_seconds: int = 86400 * 7) -> str:
    """Gera um token assinado simples e seguro sem dependências pesadas externas."""
    payload = {
        "uid": user_id,
        "rol": role,
        "sta": status,
        "exp": int(time.time()) + expires_in_seconds
    }
    raw = json.dumps(payload, separators=(',', ':')).encode("utf-8")
    b64_payload = base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")
    signature = hmac.new(JWT_SECRET.encode("utf-8"), b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{b64_payload}.{signature}"

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        b64_payload, signature = parts
        expected_sig = hmac.new(JWT_SECRET.encode("utf-8"), b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None
        # Add padding if needed
        padding = "=" * ((4 - len(b64_payload) % 4) % 4)
        payload_bytes = base64.urlsafe_b64decode(b64_payload + padding)
        payload = json.loads(payload_bytes.decode("utf-8"))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None

def get_current_user_from_token(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação não fornecido."
        )
    
    parts = authorization.split(" ")
    token = parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else authorization
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão inválida ou expirada. Faça login novamente."
        )
    
    user = get_user_by_id(payload.get("uid"))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado."
        )
    return user

def require_active_user(user: Dict[str, Any] = Depends(get_current_user_from_token)) -> Dict[str, Any]:
    """
    Regra estrita: Se a licença estiver com status diferente de 'ativo'
    (ex: 'bloqueado', 'cortado', 'suspenso'), impede acesso a qualquer área restrita!
    """
    if user.get("role") != "admin" and user.get("status") != "ativo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "LICENCA_BLOQUEADA",
                "message": "Seu acesso à plataforma está suspenso ou bloqueado. Entre em contato para regularizar sua licença."
            }
        )
    return user

def require_admin(user: Dict[str, Any] = Depends(get_current_user_from_token)) -> Dict[str, Any]:
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: Requer privilégios de administrador."
        )
    return user
