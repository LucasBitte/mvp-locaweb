from pathlib import Path
from cloud.pipeline import STEPS


def test_dependencias_pipeline_sem_ciclo_e_arquivos_presentes():
    visited = set()
    def visit(name, stack):
        assert name not in stack
        command, dependencies = STEPS[name]
        assert Path(command[-1] if command[-1].endswith('.ipynb') else command[1]).is_file()
        for dependency in dependencies:
            visit(dependency, stack | {name})
        visited.add(name)
    for name in STEPS:
        visit(name, set())
    assert len(visited) == 11
    assert STEPS['pressao'][1] == ['forecast_equipe']
    assert STEPS['forecast_produto'][1] == ['forecast_total']
