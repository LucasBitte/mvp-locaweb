-- Atualiza nome_perfil/descricao_curta dos 4 clusters (ml.dim_cluster,
-- migration 018) para uma leitura mais executiva, focada nas métricas que
-- de fato diferenciam cada perfil. Números conferidos contra
-- ml.fct_perfil_cluster/API ao vivo antes de aplicar (mesma
-- data_execucao 2026-08-22 11:56:19 já em produção, sem retreino):
-- A: pct_volume=32,07% · B: duracao_media_horas=198,30h, pct_volume=32,88%
-- C: duracao_media_horas=20,81h · D: taxa_excedeu_tempo_esperado_pct=98,05%
-- "excedeu tempo esperado" (não "violação") no texto de D, consistente com
-- o achado de auditoria documentado em app/api/routers/clusters.py (esse
-- indicador não é o SLA oficial, que é ~0,95% no banco todo).
-- tags/cor_hex/modelo_versao_referencia não mudam.
UPDATE ml.dim_cluster SET
    nome_perfil = 'Volume Moderado (Rotina)',
    descricao_curta = 'Duração intermediária • Alto volume (32%) • Risco moderado'
WHERE cluster_id = 'A';

UPDATE ml.dim_cluster SET
    nome_perfil = 'Gargalo Crônico Lento',
    descricao_curta = 'Alta duração extrema (198h) • Alto volume (33%) • Trava a esteira'
WHERE cluster_id = 'B';

UPDATE ml.dim_cluster SET
    nome_perfil = 'Rotina Rápida',
    descricao_curta = 'Curta duração (20h) • Resolução ágil • Baixo risco'
WHERE cluster_id = 'C';

UPDATE ml.dim_cluster SET
    nome_perfil = 'Alto Risco Crítico',
    descricao_curta = 'Pior taxa que excedeu tempo esperado (98%) • Maior risco operacional • Foco imediato'
WHERE cluster_id = 'D';
