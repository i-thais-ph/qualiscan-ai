"""Pruebas del calculo de indicadores y del reporte (fiabilidad)."""
import json
from pathlib import Path

from qualiscan.report import analizar_proyecto, guardar_json, imprimir_resumen


def _proyecto(tmp_path: Path) -> Path:
    (tmp_path / "app.py").write_text(
        "def a(x):\n    if x:\n        return 1\n    return 0\n\n\n"
        "def b():\n    try:\n        pass\n    except:\n        pass\n",
        encoding="utf-8")
    return tmp_path


def test_analizar_proyecto_calcula_indicadores(tmp_path: Path):
    r = analizar_proyecto(_proyecto(tmp_path))
    assert r["archivos"] == 1
    assert r["funciones"] == 2
    assert r["complejidad_maxima"] == 2
    assert r["tiene_pruebas"] is False
    assert r["defectos"] == 1  # el except sin tipo (severidad media)


def test_densidad_de_defectos_formula(tmp_path: Path):
    r = analizar_proyecto(_proyecto(tmp_path))
    esperado = round(r["defectos"] / (r["lineas_codigo"] / 1000), 2)
    assert r["densidad_defectos_kloc"] == esperado


def test_proyecto_vacio_no_falla(tmp_path: Path):
    r = analizar_proyecto(tmp_path)
    assert r["lineas_codigo"] == 0
    assert r["densidad_defectos_kloc"] == 0
    assert r["complejidad_promedio"] == 0


def test_guardar_json(tmp_path: Path):
    r = analizar_proyecto(_proyecto(tmp_path))
    destino = guardar_json(r, tmp_path / "salida")
    assert json.loads(destino.read_text(encoding="utf-8"))["proyecto"] == r["proyecto"]


def test_imprimir_resumen_muestra_titulo(tmp_path: Path, capsys):
    imprimir_resumen(analizar_proyecto(_proyecto(tmp_path)))
    assert "QUALISCAN AI" in capsys.readouterr().out