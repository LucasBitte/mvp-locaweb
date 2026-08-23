-- Corrige nome_perfil/descricao_curta dos clusters A e C (ml.dim_cluster,
-- migrations 018/029) — auditoria de consistência dado×texto encontrou
-- contradições reais:
-- A: "Volume Moderado (Rotina)" contradizia a própria descrição do card
-- ("Alto volume") e o dado real — pct_volume=32,07% é o 2º maior dos 4
-- clusters (quase empatado com B, 32,88%), não "moderado"; 30,78h de
-- duração é o 2º MENOR valor, não "intermediária"; 94,82% de excedência de
-- tempo esperado não é "risco moderado" em nenhum padrão absoluto.
-- C: "Resolução ágil"/"Baixo risco" — taxa_resolucao_pct (95,49%) é
-- estatisticamente idêntica à dos outros 3 clusters (94,4%-95,7%, ~0,3pp de
-- variação, não é diferencial real desse cluster); 94,31% de excedência é
-- o menor dos 4, mas ainda alto em absoluto.
-- Números reconferidos contra /api/clusters ao vivo antes de aplicar
-- (mesma data_execucao 2026-08-22 11:56:19 já em produção, sem retreino).
-- B e D não mudam (já corrigidos na migration 029, sem divergência
-- encontrada nesta auditoria). tags/cor_hex/modelo_versao_referencia não
-- mudam.
UPDATE ml.dim_cluster SET
    nome_perfil = 'Alto Volume, Risco Elevado',
    descricao_curta = 'Duração relativamente curta (31h) • Maior fatia do volume (32%) • Excedência de tempo ainda alta (95%)'
WHERE cluster_id = 'A';

UPDATE ml.dim_cluster SET
    nome_perfil = 'Rotina Mais Rápida',
    descricao_curta = 'Menor duração do grupo (21h) • Taxa de resolução equivalente aos demais clusters • Excedência de tempo ainda elevada (94%)'
WHERE cluster_id = 'C';
