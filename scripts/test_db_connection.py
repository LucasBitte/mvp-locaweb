"""Testa a conexão com o banco Postgres `fiap`.

O banco só existe no ambiente remoto (porta 5432 local àquele host) — para
acessá-lo de uma máquina física é preciso abrir um túnel SSH antes de rodar
este script:

    ssh -N -L 5432:localhost:5432 lucas@147.93.15.20 -p 2222

Com o túnel aberto em outro terminal, configure o `.env` local (a partir de
`.env.example`) com:

    FIAP_DB_HOST=localhost
    FIAP_DB_PORT=5432
    FIAP_DB_USER=fiap
    FIAP_DB_PASSWORD=<mesma senha do .env do ambiente remoto>
    FIAP_DB_NAME=fiap

Uso:
    python scripts/test_db_connection.py
"""

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from etl.db import get_engine


def main() -> int:
    engine = get_engine()
    url = engine.url

    print(f"Conectando em postgresql://{url.username}@{url.host}:{url.port}/{url.database} ...")

    try:
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version()")).scalar_one()
            print("Conexão OK.")
            print(f"Servidor: {version}")

            schemas = conn.execute(
                text("SELECT schema_name FROM information_schema.schemata ORDER BY schema_name")
            ).scalars().all()
            print(f"Schemas disponíveis: {', '.join(schemas)}")
    except OperationalError as exc:
        print("Falha ao conectar no banco.", file=sys.stderr)
        print(
            "Se você está em uma máquina fora do ambiente remoto, confirme que o "
            "túnel SSH está aberto:\n"
            "    ssh -N -L 5432:localhost:5432 lucas@147.93.15.20 -p 2222",
            file=sys.stderr,
        )
        print(f"Detalhe do erro: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
