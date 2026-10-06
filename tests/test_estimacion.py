"""Pruebas de las cuatro tecnicas de estimacion."""
from qualiscan.estimacion import (estimacion_analoga, juicio_expertos,
                                  puntos_funcion, tres_puntos)


def test_juicio_de_expertos_promedia():
    r = juicio_expertos({"nombres": ["a", "b"], "horas": {"m1": [4, 6], "m2": [2, 4]}})
    assert r["por_modulo"] == {"m1": 5.0, "m2": 3.0}
    assert r["total_horas"] == 8.0


def test_estimacion_analoga_escala_por_tamano():
    cfg = {"proyecto_referencia": "x", "horas": 20, "loc": 200}
    assert estimacion_analoga(cfg, 400)["total_horas"] == 40.0


def test_tres_puntos_pert():
    r = tres_puntos({"m": {"O": 2, "M": 4, "P": 12}})
    assert r["por_modulo"]["m"]["esperado"] == 5.0   # (2 + 16 + 12) / 6
    assert r["por_modulo"]["m"]["desviacion"] == 1.67
    assert r["total_horas"] == 5.0


def test_puntos_de_funcion():
    cfg = {"EI": 2, "EO": 3, "EQ": 1, "ILF": 1, "EIF": 2,
           "gsc": [1] * 14, "horas_por_pf": 1}
    r = puntos_funcion(cfg)
    assert r["ufp"] == 51                 # 8 + 15 + 4 + 10 + 14
    assert r["vaf"] == 0.79               # 0.65 + 0.14
    assert r["pf_ajustados"] == 40.29
    assert r["total_horas"] == 40.29