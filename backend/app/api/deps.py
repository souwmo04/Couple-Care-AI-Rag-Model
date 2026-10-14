"""FastAPI dependencies."""

from __future__ import annotations

import re

from fastapi import Header, Request

from app.core.container import Container
from app.errors import BadRequestError
from app.storage.sessions import owner_key

CLIENT_ID_RE = re.compile(r"^[A-Za-z0-9-]{16,64}$")


def get_container(request: Request) -> Container:
    return request.app.state.container


def get_owner(x_client_id: str | None = Header(default=None)) -> str:
    """Derive the owner key from the browser's random client id.

    The frontend generates a random id once per browser profile. Requests without one are
    rejected for conversation endpoints so conversations are never shared across clients.
    """
    if not x_client_id or not CLIENT_ID_RE.match(x_client_id):
        raise BadRequestError("Missing or invalid client identifier.", code="missing_client_id")
    return owner_key(x_client_id)
