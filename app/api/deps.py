"""Dependências compartilhadas dos routers da API.

Única via de conexão com o banco `fiap` (`CLAUDE.md` §6) — nenhum router
deve abrir uma engine própria.
"""
from __future__ import annotations

from functools import lru_cache

from sqlalchemy.engine import Engine

from etl.db import get_engine


@lru_cache
def get_db_engine() -> Engine:
    return get_engine()
