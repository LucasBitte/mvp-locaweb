"""Executa somente a função pura de seleção de features, nunca treino."""
import ast
import json
from pathlib import Path
import numpy as np
import pandas as pd


def test_notebook_declara_duracao_como_leakage():
    notebook = json.loads(Path('notebooks/model_risk_xgboost_.ipynb').read_text(encoding='utf-8'))
    assignments = {}
    for cell in notebook['cells']:
        if cell['cell_type'] != 'code':
            continue
        try:
            tree = ast.parse(''.join(cell['source']))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == 'COLS_LEAKAGE':
                        assignments[target.id] = ast.literal_eval(node.value)
    assert 'duracao_horas' in assignments['COLS_LEAKAGE']


def test_features_reais_nao_mudam_com_rotulo_duracao_ou_futuro():
    notebook = json.loads(Path('notebooks/model_risk_xgboost_.ipynb').read_text(encoding='utf-8'))
    function = None
    for cell in notebook['cells']:
        if cell['cell_type'] == 'code' and 'def construir_features(' in ''.join(cell['source']):
            function = next(n for n in ast.parse(''.join(cell['source'])).body
                            if isinstance(n, ast.FunctionDef) and n.name == 'construir_features')
    assert function is not None
    scope = {'pd': pd, 'np': np, 'INCLUIR_POSSUI_PAI': True,
             'CATEGORICAS': ['grupo_designado', 'categoria', 'subcategoria', 'turno_abertura']}
    exec(compile(ast.Module(body=[function], type_ignores=[]), '<features-reais>', 'exec'), scope)
    frame = pd.DataFrame([dict(prioridade_num=2, possui_pai=False, hora_abertura=10,
                              dia_semana_num=1, fora_horario_comercial=False,
                              abriu_fim_de_semana=False, categoria='c', subcategoria='s',
                              turno_abertura='Manha', grupo_designado='g', dia_idx=1,
                              t=i, duracao_horas=i, target_excedeu_tempo=bool(i)) for i in range(3)])
    features = scope['construir_features']
    original = features(frame)
    mutated = frame.assign(duracao_horas=9999, target_excedeu_tempo=False)
    pd.testing.assert_frame_equal(original, features(mutated))
    pd.testing.assert_frame_equal(original.iloc[:2], features(frame.iloc[:2]))
