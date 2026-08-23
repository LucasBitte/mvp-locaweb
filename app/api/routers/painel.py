"""
Router: GET /api/painel
Cockpit executivo — 4 KPIs + visão das 3 lentes

Fonte: ml.fct_previsao_diaria_total, ml.fct_pressao_equipe, dw.fct_incidentes, dw.ref_meta_sla_anual
"""
from datetime import datetime, date, timedelta
from typing import Optional
import os

import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import APIRouter, Query

from app.api.models import PainelResponse, PrevisaoPonto, PressaoEquipe, MetadadosResposta

router = APIRouter(prefix="/api", tags=["painel"])


def get_db_connection():
    """Conecta ao banco fiap"""
    env_vars = {}
    env_file_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
    if os.path.exists(env_file_path):
        with open(env_file_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env_vars[k] = v

    return psycopg2.connect(
        host=env_vars.get("FIAP_DB_HOST", "localhost"),
        port=int(env_vars.get("FIAP_DB_PORT", 5432)),
        database=env_vars.get("FIAP_DB_NAME", "fiap"),
        user=env_vars.get("FIAP_DB_USER", "fiap"),
        password=env_vars.get("FIAP_DB_PASSWORD", ""),
    )


@router.get("/painel", response_model=PainelResponse)
def get_painel(data_base: Optional[str] = Query(None, description="YYYY-MM-DD (default: hoje)")):
    """
    Cockpit executivo com 4 KPIs e visão geral.

    Retorna:
    - total_chamados: incidentes de hoje
    - kpi_status_agregado: % de OLA cumprido (P2+P3)
    - previsao_d1: volume previsto para amanhã (com intervalo de confiança)
    - pressao_equipes: lista de equipes e pressão relativa
    """

    if data_base:
        try:
            data_execucao = datetime.strptime(data_base, "%Y-%m-%d")
        except ValueError:
            data_execucao = datetime.now()
    else:
        data_execucao = datetime.now()

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 1. Total de chamados hoje
        cur.execute("""
            SELECT COUNT(*) as total
            FROM dw.fct_incidentes
            WHERE DATE(aberto) = DATE(%s)
            AND prioridade_num IN (2, 3)
        """, (data_execucao,))
        total_chamados = cur.fetchone()["total"] or 0

        # 2. KPI status agregado (P2+P3)
        cur.execute("""
            SELECT
                ROUND(100.0 * SUM(CASE WHEN kpi_status_int > 0 THEN 1 ELSE 0 END)
                    / NULLIF(COUNT(*), 0)::numeric, 2) as pct_cumprido
            FROM dw.fct_incidentes
            WHERE prioridade_num IN (2, 3)
            AND kpi_status_int IS NOT NULL
        """)
        row = cur.fetchone()
        kpi_status_agregado = float(row["pct_cumprido"] or 0)

        # 3. Previsão D+1 (Prophet total)
        amanha = (data_execucao + timedelta(days=1)).date()
        cur.execute("""
            SELECT ds, yhat, yhat_lower, yhat_upper, y
            FROM ml.fct_previsao_diaria_total
            WHERE ds = %s
            ORDER BY ds DESC
            LIMIT 1
        """, (amanha,))
        pred_row = cur.fetchone()

        if pred_row:
            previsao_d1 = PrevisaoPonto(
                ds=pred_row["ds"],
                y=float(pred_row["y"] or 0),
                yhat=float(pred_row["yhat"] or 0),
                yhat_lower=float(pred_row["yhat_lower"]) if pred_row["yhat_lower"] else None,
                yhat_upper=float(pred_row["yhat_upper"]) if pred_row["yhat_upper"] else None,
            )
        else:
            # Fallback se não houver previsão
            previsao_d1 = PrevisaoPonto(
                ds=amanha,
                y=0,
                yhat=0,
                yhat_lower=None,
                yhat_upper=None,
            )

        # 4. Pressão média D+1..D+7
        cur.execute("""
            SELECT AVG(pressao_relativa_pct) as pressao_media
            FROM ml.fct_pressao_equipe
            WHERE ds >= %s AND ds <= %s
        """, (amanha, amanha + timedelta(days=6)))
        pressao_row = cur.fetchone()
        pressao_d1_a_d7_media = float(pressao_row["pressao_media"] or 0)

        # 5. Pressão por equipe (D+1)
        cur.execute("""
            SELECT
                fg.grupo_id,
                fg.pressao_relativa_pct,
                fg.metodo_origem
            FROM ml.fct_pressao_equipe fg
            WHERE fg.ds = %s
            ORDER BY fg.pressao_relativa_pct DESC
        """, (amanha,))

        pressao_equipes = []
        for row in cur.fetchall():
            pressao_equipes.append(PressaoEquipe(
                grupo_id=row["grupo_id"],
                pressao_relativa_pct=float(row["pressao_relativa_pct"] or 0),
                metodo_origem=row.get("metodo_origem", "split_proporcional"),
            ))

        # 6. Volume total do ano (referência)
        cur.execute("SELECT COUNT(*) as total FROM dw.fct_incidentes WHERE EXTRACT(YEAR FROM aberto) = 2025")
        vol_year = cur.fetchone()["total"] or 41441  # fallback

        # 7. Categoria top (volume previsto)
        cur.execute("""
            SELECT categoria, MAX(yhat) as max_prev
            FROM ml.fct_previsao_categoria
            WHERE ds = %s
            GROUP BY categoria
            ORDER BY max_prev DESC
            LIMIT 1
        """, (amanha,))
        cat_row = cur.fetchone()
        forecast_top_categoria = cat_row["categoria"] if cat_row else "Infraestrutura"

        # 8. Risco principal (cluster)
        cur.execute("""
            SELECT cluster_id FROM ml.fct_perfil_cluster
            ORDER BY taxa_sla_violado_pct DESC
            LIMIT 1
        """)
        risco_row = cur.fetchone()
        risco_principal = risco_row["cluster_id"] if risco_row else "D"

        # Montar resposta
        return PainelResponse(
            total_chamados=total_chamados,
            kpi_status_agregado=kpi_status_agregado,
            previsao_d1=previsao_d1,
            pressao_d1_a_d7_media=pressao_d1_a_d7_media,
            pressao_equipes=pressao_equipes,
            volume_total_ano_referencia=int(vol_year),
            forecast_top_categoria=forecast_top_categoria,
            risco_principal=risco_principal,
            metadados=MetadadosResposta(data_execucao=datetime.now()),
        )

    finally:
        conn.close()
