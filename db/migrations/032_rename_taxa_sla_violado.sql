-- Migration 032: Renomear taxa_sla_violado_pct → taxa_excedeu_tempo_esperado_pct
-- Objetivo: eliminar ambiguidade semântica (excedência de tempo vs. OLA oficial)
-- Contexto: Achado #2 do plano de auditoria (Parte B, linha 103)

-- Renomear a coluna em ml.fct_perfil_cluster
ALTER TABLE ml.fct_perfil_cluster
    RENAME COLUMN taxa_sla_violado_pct TO taxa_excedeu_tempo_esperado_pct;

-- Comentário explicativo
COMMENT ON COLUMN ml.fct_perfil_cluster.taxa_excedeu_tempo_esperado_pct IS
    'Taxa de incidentes que excederam o tempo esperado (SLA threshold) por prioridade. '
    'Não é a mesma coisa que "quebra de OLA" oficial (kpi_status_int). '
    'Renomeada em migration 032 para eliminar ambiguidade semântica.';
