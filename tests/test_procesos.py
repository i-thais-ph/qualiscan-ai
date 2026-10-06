"""Pruebas de las metricas de proceso y de proyecto."""
from pathlib import Path

from qualiscan.procesos import (horas_entre, leer_csv, metricas_proceso,
                                metricas_proyecto)

INC = [
    {"id": "1", "modulo": "a", "severidad": "alta", "fase_deteccion": "pruebas",
     "inicio": "2026-01-01 10:00", "detectado": "2026-01-01 12:00", "resuelto": "2026-01-01 13:00"},
    {"id": "2", "modulo": "a", "severidad": "alta", "fase_deteccion": "produccion",
     "inicio": "2026-01-01 10:00", "detectado": "2026-01-01 14:00", "resuelto": "2026-01-01 17:00"},
    {"id": "3", "modulo": "b", "severidad": "media", "fase_deteccion": "revision",
     "inicio": "2026-01-01 10:00", "detectado": "2026-01-01 10:00", "resuelto": "2026-01-01 11:00"},
    {"id": "4", "modulo": "b", "severidad": "baja", "fase_deteccion": "revision",
     "inicio": "2026-01-01 10:00", "detectado": "2026-01-01 10:00", "resuelto": "2026-01-01 11:00"},
]
MODS = [
    {"modulo": "a", "sprint": "1", "puntos_historia": "5", "horas_estimadas": "10",
     "horas_reales": "15", "loc": "500"},
    {"modulo": "b", "sprint": "1", "puntos_historia": "3", "horas_estimadas": "10",
     "horas_reales": "10", "loc": "500"},
]


def test_horas_entre():
    assert horas_entre("2026-01-01 10:00", "2026-01-01 12:30") == 2.5


def test_mttd_y_mttr():
    p = metricas_proceso(INC)
    assert p["mttd_horas"] == 1.5   # (2 + 4 + 0 + 0) / 4
    assert p["mttr_horas"] == 1.5   # (1 + 3 + 1 + 1) / 4


def test_eficacia_de_pruebas():
    p = metricas_proceso(INC)
    assert p["criticos_en_pruebas"] == 1 and p["criticos_en_produccion"] == 1
    assert p["eficacia_pruebas_pct"] == 50.0


def test_eficacia_de_revision():
    assert metricas_proyecto(INC, MODS)["eficacia_revision_pct"] == 50.0


def test_desviacion_y_densidad_por_modulo():
    y = metricas_proyecto(INC, MODS)
    a = y["modulos"][0]
    assert a["desviacion_pct"] == 50.0
    assert a["densidad_kloc"] == 4.0          # 2 defectos / 0.5 KLOC
    assert y["desviacion_total_pct"] == 25.0   # 25 h reales vs 20 h estimadas
    assert y["densidad_global_kloc"] == 4.0    # 4 defectos / 1 KLOC


def test_sin_incidentes_no_falla():
    assert metricas_proceso([])["mttd_horas"] == 0.0
    assert metricas_proceso([])["eficacia_pruebas_pct"] == 0.0


def test_leer_csv_ignora_comentarios(tmp_path: Path):
    archivo = tmp_path / "d.csv"
    archivo.write_text("# comentario\na,b\n1,2\n", encoding="utf-8")
    assert leer_csv(archivo) == [{"a": "1", "b": "2"}]