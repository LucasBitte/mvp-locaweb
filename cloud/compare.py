"""Dual-run somente leitura, comparação exata sem esconder divergências."""
import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import httpx
from sqlalchemy import inspect, text
from etl.db import get_engine


def configured_engine(prefix):
    keys = ('USER', 'PASSWORD', 'HOST', 'PORT', 'NAME')
    previous = {f'FIAP_DB_{key}': os.getenv(f'FIAP_DB_{key}') for key in keys}
    try:
        for key in keys:
            os.environ[f'FIAP_DB_{key}'] = os.environ[f'{prefix}_FIAP_DB_{key}']
        return get_engine()
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def fingerprint(conn, schema, table):
    quote = conn.dialect.identifier_preparer.quote
    query = f'SELECT row_to_json(t)::text FROM {quote(schema)}.{quote(table)} t'
    rows = sorted(row[0] for row in conn.execute(text(query)))
    digest = hashlib.sha256()
    for row in rows:
        raw = row.encode()
        digest.update(len(raw).to_bytes(8, 'big'))
        digest.update(raw)
    return {'rows': len(rows), 'sha256': digest.hexdigest()}


def snapshot(engine):
    result = {}
    with engine.connect().execution_options(isolation_level='REPEATABLE READ') as conn:
        with conn.begin():
            conn.execute(text('SET TRANSACTION READ ONLY'))
            conn.execute(text("SET TIME ZONE 'UTC'"))
            for schema in ('public', 'staging', 'dw', 'ml'):
                for table in inspect(conn).get_table_names(schema=schema):
                    if schema == 'public' and table != 'incidentes':
                        continue
                    result[f'{schema}.{table}'] = fingerprint(conn, schema, table)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-api', required=True)
    parser.add_argument('--target-api', required=True)
    parser.add_argument('--output', default='cloud/evidence/dual-run.json')
    args = parser.parse_args()
    engines = [configured_engine(p) for p in ('SOURCE', 'TARGET')]
    try:
        source, target = [snapshot(e) for e in engines]
        report = {'source': source, 'target': target, 'tables_equal': source == target, 'endpoints': {}}
        with httpx.Client(timeout=60) as client:
            for name in ('painel', 'detalhe', 'kpi', 'fatores', 'clusters', 'alertas'):
                bodies, latencies = [], []
                for base in (args.source_api, args.target_api):
                    start = time.perf_counter()
                    response = client.get(f'{base.rstrip("/")}/api/{name}')
                    response.raise_for_status()
                    latencies.append(round((time.perf_counter() - start) * 1000, 2))
                    bodies.append(response.json())
                report['endpoints'][name] = {'equal': bodies[0] == bodies[1], 'latency_ms': latencies}
        report['passed'] = report['tables_equal'] and all(x['equal'] for x in report['endpoints'].values())
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2), encoding='utf-8')
        raise SystemExit(0 if report['passed'] else 1)
    finally:
        for engine in engines:
            engine.dispose()


if __name__ == '__main__':
    main()
