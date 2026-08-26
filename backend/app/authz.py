"""Autorización y control de acceso basado en headers.

Identidad vía headers X-Operator-Id / X-Operator-Role (fase pre-JWT).
Roles: operator, reviewer, admin.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request

from .job_store import JobStore, JOB_ID_RE


class Role(str, Enum):
    OPERATOR = "operator"
    REVIEWER = "reviewer"
    ADMIN = "admin"


ROLE_HIERARCHY = {
    Role.OPERATOR: 1,
    Role.REVIEWER: 2,
    Role.ADMIN: 3,
}

VALID_ROLES = {r.value for r in Role}


def _get_operator_id(
    x_operator_id: Optional[str] = Header(None, alias="X-Operator-Id"),
) -> str:
    if not x_operator_id or not x_operator_id.strip():
        raise HTTPException(400, "Header X-Operator-Id requerido")
    return x_operator_id.strip()


def _get_operator_role(
    x_operator_role: Optional[str] = Header(None, alias="X-Operator-Role"),
) -> Role:
    if not x_operator_role or not x_operator_role.strip():
        raise HTTPException(400, "Header X-Operator-Role requerido")
    role_str = x_operator_role.strip().lower()
    if role_str not in VALID_ROLES:
        raise HTTPException(403, f"Rol inválido: {role_str}. Valores permitidos: {', '.join(sorted(VALID_ROLES))}")
    return Role(role_str)


def require_role(allowed_roles: list[Role]):
    """Dependency que valida que el rol del operador esté en allowed_roles."""
    def _check(
        operator_id: str = Depends(_get_operator_id),
        operator_role: Role = Depends(_get_operator_role),
    ) -> tuple[str, Role]:
        if operator_role not in allowed_roles:
            raise HTTPException(403, f"Rol '{operator_role.value}' no autorizado. Requerido: {[r.value for r in allowed_roles]}")
        return operator_id, operator_role
    return _check


def require_job_owner_or_reviewer(store: JobStore):
    """Dependency que valida ownership del job o rol reviewer/admin.
    
    - operator: solo puede actuar en jobs propios (operator_id coincide)
    - reviewer/admin: puede actuar en cualquier job
    """
    def _check(
        job_id: str,
        operator_id: str = Depends(_get_operator_id),
        operator_role: Role = Depends(_get_operator_role),
    ) -> tuple[str, Role]:
        if not JOB_ID_RE.match(job_id):
            raise HTTPException(400, "job_id inválido")
        
        # Primero intentar cargar job en memoria (incluye jobs rejected by quality gate)
        job = store.get(job_id)
        if job is None:
            # Fallback: cargar original persistido
            original = store.load_original(job_id)
            if original is None:
                raise HTTPException(404, "Job no encontrado")
            job = original
        
        job_operator_id = job.get("processing_metadata", {}).get("operator_id")
        job_operator_role = job.get("processing_metadata", {}).get("operator_role")
        
        # Jobs legacy/sin owner: system/admin
        if not job_operator_id:
            job_operator_id = "system"
            job_operator_role = "admin"
        
        # Admin y reviewer pueden todo
        if operator_role in (Role.ADMIN, Role.REVIEWER):
            return operator_id, operator_role
        
        # Operator solo sus propios jobs
        if operator_id != job_operator_id:
            raise HTTPException(403, "No tiene permiso para este job (solo jobs propios)")
        
        return operator_id, operator_role
    return _check


def get_operator_identity(
    operator_id: str = Depends(_get_operator_id),
    operator_role: Role = Depends(_get_operator_role),
) -> tuple[str, Role]:
    """Dependency simple que devuelve (operator_id, operator_role) validados."""
    return operator_id, operator_role


__all__ = ["Role", "require_role", "require_job_owner_or_reviewer", "get_operator_identity", "VALID_ROLES"]