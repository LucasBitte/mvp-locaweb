-- Camada Silver (bronze -> silver), usada por notebooks/03 antes do
-- modelo dimensional em dw.*. Não versionado por migration própria por
-- tabela: notebooks/03 recria staging.incidentes_silver a cada execução
-- (to_sql com if_exists='replace').
CREATE SCHEMA IF NOT EXISTS staging;
