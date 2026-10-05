"""Pruebas del modulo de IA y de su respaldo (fiabilidad / tolerancia a fallos)."""
import os
from pathlib import Path
from unittest import mock

from qualiscan import ia
from qualiscan.report import analizar_proyecto


def _resultado(tmp_path: Path) -> dict:
    (tmp_path / "app.py").write_text(
        "def a(x):\n    if x:\n        return 1\n    return 0\n", encoding="utf-8")
    return analizar_proyecto(tmp_path)


def test_sin_ia_usa_reglas(tmp_path: Path):
    rev = ia.revisar_con_ia(_resultado(tmp_path), tmp_path, usar_ia=False)
    assert rev["modo"] == "reglas"


def test_sin_clave_usa_reglas(tmp_path: Path):
    with mock.patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
        rev = ia.revisar_con_ia(_resultado(tmp_path), tmp_path)
    assert rev["modo"] == "reglas"
    assert "GEMINI_API_KEY" in rev["motivo"]


def test_respuesta_valida_de_ia(tmp_path: Path):
    falso = ('```json\n[{"archivo":"app.py","funcion":"a","severidad":"baja",'
             '"problema":"p","sugerencia":"s"}]\n```')
    with mock.patch.object(ia, "consultar_gemini", return_value=(falso, "modelo-x")):
        rev = ia.revisar_con_ia(_resultado(tmp_path), tmp_path)
    assert rev["modo"] == "ia"
    assert rev["modelo"] == "modelo-x"
    assert rev["sugerencias"][0]["funcion"] == "a"


def test_respuesta_invalida_activa_respaldo(tmp_path: Path):
    with mock.patch.object(ia, "consultar_gemini", return_value=("esto no es json", "m")):
        rev = ia.revisar_con_ia(_resultado(tmp_path), tmp_path)
    assert rev["modo"] == "reglas"


def test_falla_de_red_activa_respaldo(tmp_path: Path):
    with mock.patch.object(ia, "consultar_gemini", side_effect=RuntimeError("sin internet")):
        rev = ia.revisar_con_ia(_resultado(tmp_path), tmp_path)
    assert rev["modo"] == "reglas"
    assert "sin internet" in rev["motivo"]


def test_cargar_env(tmp_path: Path):
    archivo = tmp_path / ".env"
    archivo.write_text('QS_PRUEBA="valor123"\n# comentario\n', encoding="utf-8")
    os.environ.pop("QS_PRUEBA", None)
    ia.cargar_env(str(archivo))
    assert os.environ["QS_PRUEBA"] == "valor123"
    os.environ.pop("QS_PRUEBA", None)


def test_imprimir_revision(tmp_path: Path, capsys):
    rev = ia.revisar_con_ia(_resultado(tmp_path), tmp_path, usar_ia=False)
    ia.imprimir_revision(rev)
    assert "REVISION DE CODIGO" in capsys.readouterr().out