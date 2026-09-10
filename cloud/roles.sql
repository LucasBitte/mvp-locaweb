-- Executar no database fiap como administrador, depois das migrations.
-- Credenciais LOGIN são definidas fora do git e armazenadas no Secrets Manager.
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'fiap_reader') THEN
    CREATE ROLE fiap_reader NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'fiap_pipeline') THEN
    CREATE ROLE fiap_pipeline NOLOGIN;
  END IF;
END $$;
GRANT CONNECT ON DATABASE fiap TO fiap_reader, fiap_pipeline;
GRANT USAGE ON SCHEMA public, staging, dw, ml TO fiap_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public, staging, dw, ml TO fiap_reader;
GRANT USAGE ON SCHEMA public TO fiap_pipeline;
GRANT SELECT ON public.incidentes TO fiap_pipeline;
GRANT USAGE, CREATE ON SCHEMA staging, dw, ml TO fiap_pipeline;
-- Os notebooks usam replace/to_sql: propriedade necessária só nesses schemas.
DO $$ DECLARE t record;
BEGIN
  FOR t IN SELECT schemaname, tablename FROM pg_tables
           WHERE schemaname IN ('staging','dw','ml') LOOP
    EXECUTE format('ALTER TABLE %I.%I OWNER TO fiap_pipeline', t.schemaname, t.tablename);
  END LOOP;
END $$;
ALTER DEFAULT PRIVILEGES FOR ROLE fiap_pipeline IN SCHEMA staging, dw, ml
  GRANT SELECT ON TABLES TO fiap_reader;
