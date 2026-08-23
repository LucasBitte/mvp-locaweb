#!/usr/bin/env python3
"""
Cria e popula ml_dev.alertas_ativos — tabela que /api/alertas consulta.

A tabela ml.alertas_ativos referenciada pelo router de Fase 3.2 nunca existiu
no banco (achado descoberto na Fase 4.2, ao ligar as telas 03/04/05 contra a
API real). Em vez de criar direto em produção (`ml`), populamos em `ml_dev`
(mesmo padrão já usado para ml_dev.fct_avaliacao_modelo na Fase 2.1) até uma
decisão formal de promover isso para `ml` na Fase 5.

Regras aplicadas (documentadas como REGRA, nunca como saída de modelo):
  1. cluster_maior_impacto: cluster com maior pct_volume × taxa_excedeu_tempo_esperado_pct
     (mesma fórmula da Tela 04 — nunca usar só a taxa isolada: todos os 4 clusters têm
     94-98% de excedência, então um limiar sobre a taxa crua dispara pra todos e não
     sinaliza nada; o "impacto por volume e excedência" é o que de fato diferencia)
  2. equipe_pressao_atencao: equipe com nivel_pressao='atencao' na previsão D+1

Uso:
  python3 scripts/create_and_populate_alertas_dev.py
"""
from pathlib import Path
from uuid import uuid4

import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch


def find_project_root(start: Path = None) -> Path:
    start = start or Path.cwd()
    if (start / ".git").exists() or (start / "etl" / "db.py").exists():
        return start
    if start.parent == start:
        raise RuntimeError("mvp-locaweb root not found")
    return find_project_root(start.parent)


def load_env():
    env_vars = {}
    env_file = find_project_root() / ".env"
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env_vars[k] = v
    return env_vars


DDL = """
CREATE SCHEMA IF NOT EXISTS ml_dev;

CREATE TABLE IF NOT EXISTS ml_dev.alertas_ativos (
    id TEXT PRIMARY KEY,
    severidade TEXT NOT NULL,
    condicao TEXT NOT NULL,
    cluster_id TEXT,
    equipe_id TEXT,
    origem TEXT NOT NULL DEFAULT 'regra',
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def main():
    env = load_env()
    conn = psycopg2.connect(
        host=env.get("FIAP_DB_HOST", "localhost"),
        port=int(env.get("FIAP_DB_PORT", 5432)),
        database=env.get("FIAP_DB_NAME", "fiap"),
        user=env.get("FIAP_DB_USER", "fiap"),
        password=env.get("FIAP_DB_PASSWORD", ""),
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(DDL)
    cur.execute("TRUNCATE ml_dev.alertas_ativos")

    rows = []

    # Regra 1: cluster_maior_impacto — pct_volume × taxa_excedeu_tempo_esperado_pct,
    # só o cluster de maior impacto (não "todo cluster acima de X%", que dispara sempre
    # já que a taxa crua é 94-98% em todos os 4 clusters neste dataset).
    cur.execute("""
        SELECT c.cluster_id, c.nome_perfil, p.taxa_excedeu_tempo_esperado_pct, p.pct_volume
        FROM ml.dim_cluster c
        JOIN ml.fct_perfil_cluster p ON c.cluster_id = p.cluster_id
    """)
    perfis = cur.fetchall()
    if perfis:
        top = max(perfis, key=lambda r: float(r["pct_volume"]) * float(r["taxa_excedeu_tempo_esperado_pct"]))
        taxa = float(top["taxa_excedeu_tempo_esperado_pct"])
        volume = float(top["pct_volume"])
        rows.append((
            str(uuid4()),
            "alta",
            f"Cluster {top['nome_perfil']} é o de maior impacto (volume×excedência): "
            f"{volume:.1f}% do volume com {taxa:.1f}% de excedência de tempo esperado",
            top["cluster_id"],
            None,
            "regra",
        ))

    # Regra 2: equipe_pressao_atencao (previsão D+1 mais recente)
    cur.execute("""
        SELECT dg.grupo_designado, fg.nivel_pressao, fg.pressao_relativa_pct
        FROM ml.fct_pressao_equipe fg
        JOIN dw.dim_grupo dg ON dg.dim_grupo_sk = fg.dim_grupo_sk
        WHERE fg.nivel_pressao = 'atencao'
        AND fg.ds = (SELECT MIN(ds) FROM ml.fct_pressao_equipe WHERE ds >= CURRENT_DATE)
    """)
    for r in cur.fetchall():
        rows.append((
            str(uuid4()),
            "média",
            f"Equipe {r['grupo_designado']} em pressão acima do histórico (nível: atenção, {float(r['pressao_relativa_pct']):.1f}%)",
            None,
            r["grupo_designado"],
            "regra",
        ))

    execute_batch(cur, """
        INSERT INTO ml_dev.alertas_ativos (id, severidade, condicao, cluster_id, equipe_id, origem)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, rows)

    conn.commit()
    print(f"{len(rows)} alertas inseridos em ml_dev.alertas_ativos")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
