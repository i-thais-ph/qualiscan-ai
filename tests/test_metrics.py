"""Pruebas de las metricas de producto (idoneidad funcional)."""
import ast
from pathlib import Path

from qualiscan.metrics import (analizar_archivo, complejidad_ciclomatica,
                               contar_lineas_codigo, detectar_hallazgos,
                               listar_archivos_python, tiene_pruebas, Funcion)


def _funcion(codigo: str) -> ast.AST:
    return ast.parse(codigo).body[0]


def test_complejidad_funcion_simple_es_1():
    assert complejidad_ciclomatica(_funcion("def f():\n    return 1")) == 1


def test_complejidad_cuenta_decisiones():
    codigo = (
        "def f(x):\n"
        "    if x > 1:\n"
        "        return 1\n"
        "    for i in range(3):\n"
        "        pass\n"
        "    while x:\n"
        "        x -= 1\n"
        "    return 0\n")
    assert complejidad_ciclomatica(_funcion(codigo)) == 4


def test_complejidad_cuenta_operadores_booleanos_y_except():
    codigo = (
        "def f(a, b, c):\n"
        "    try:\n"
        "        return a and b and c\n"
        "    except ValueError:\n"
        "        return 0\n")
    # 1 base + 2 por 'and' + 1 por except
    assert complejidad_ciclomatica(_funcion(codigo)) == 4


def test_complejidad_comprension_con_condicion():
    assert complejidad_ciclomatica(_funcion("def f(l):\n    return [x for x in l if x]")) == 3


def test_rango_de_funcion():
    assert Funcion("a.py", "f", 1, 3, 5).rango == "A"
    assert Funcion("a.py", "f", 1, 8, 5).rango == "B"
    assert Funcion("a.py", "f", 1, 15, 5).rango == "C"
    assert Funcion("a.py", "f", 1, 25, 5).rango == "D"
    assert Funcion("a.py", "f", 1, 35, 5).rango == "E"
    assert Funcion("a.py", "f", 1, 50, 5).rango == "F"


def test_contar_lineas_ignora_vacias_y_comentarios():
    texto = "# comentario\n\nx = 1\n   \ny = 2  # inline\n"
    assert contar_lineas_codigo(texto) == 2


def test_detecta_except_sin_tipo_y_eval():
    codigo = "try:\n    eval('1')\nexcept:\n    pass\n"
    reglas = {h.regla for h in detectar_hallazgos("x.py", codigo, ast.parse(codigo))}
    assert {"R01", "R02"} <= reglas


def test_detecta_argumento_mutable_y_falta_docstring():
    codigo = "def f(x=[]):\n    return x\n"
    reglas = {h.regla for h in detectar_hallazgos("x.py", codigo, ast.parse(codigo))}
    assert {"R03", "R04"} <= reglas


def test_detecta_credencial_y_todo():
    codigo = 'password = "secreto123"\n# TODO: revisar\n'
    reglas = {h.regla for h in detectar_hallazgos("x.py", codigo, ast.parse(codigo))}
    assert {"R07", "R08"} <= reglas


def test_archivo_con_error_de_sintaxis(tmp_path: Path):
    (tmp_path / "malo.py").write_text("def f(:\n", encoding="utf-8")
    res = analizar_archivo(tmp_path / "malo.py", tmp_path)
    assert res.hallazgos[0].regla == "R00"


def test_listar_archivos_ignora_venv(tmp_path: Path):
    (tmp_path / "venv").mkdir()
    (tmp_path / "venv" / "lib.py").write_text("x = 1", encoding="utf-8")
    (tmp_path / "app.py").write_text("x = 1", encoding="utf-8")
    nombres = [p.name for p in listar_archivos_python(tmp_path)]
    assert nombres == ["app.py"]


def test_tiene_pruebas(tmp_path: Path):
    assert tiene_pruebas([tmp_path / "test_algo.py"]) is True
    assert tiene_pruebas([tmp_path / "app.py"]) is False