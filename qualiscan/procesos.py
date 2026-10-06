"""Metricas de proceso y de proyecto a partir del registro de incidentes y modulos."""
import csv
from datetime import datetime
from pathlib import Path

FORMATO_FECHA = "%Y-%m-%d %H:%M"


def leer_csv(ruta: Path) -> list:
    """Lee un CSV ignorando las lineas que empiezan con #."""
    with open(ruta, encoding="utf-8", newline="") as f:
        lineas = [l for l in f if l.strip() and not l.lstrip().startswith("#")]
    return list(csv.DictReader(lineas))


def horas_entre(inicio: str, fin: str) -> float:
    dt = datetime.strptime(fin, FORMATO_FECHA) - datetime.strptime(inicio, FORMATO_FECHA)
    return dt.total_seconds() / 3600


def _promedio(valores: list) -> float:
    return round(sum(valores) / len(valores), 2) if valores else 0.0


def _porcentaje(parte: int, total: int) -> float:
    return round(parte * 100 / total, 2) if total else 0.0


def metricas_proceso(incidentes: list) -> dict:
    """MTTD, MTTR y eficacia de las pruebas."""
    criticos = [i for i in incidentes if i["severidad"] == "alta"]
    en_pruebas = sum(1 for i in criticos if i["fase_deteccion"] == "pruebas")
    en_produccion = sum(1 for i in criticos if i["fase_deteccion"] == "produccion")
    return {
        "mttd_horas": _promedio([horas_entre(i["inicio"], i["detectado"]) for i in incidentes]),
        "mttr_horas": _promedio([horas_entre(i["detectado"], i["resuelto"]) for i in incidentes]),
        "criticos_en_pruebas": en_pruebas,
        "criticos_en_produccion": en_produccion,
        "eficacia_pruebas_pct": _porcentaje(en_pruebas, en_pruebas + en_produccion),
    }


def metricas_proyecto(incidentes: list, modulos: list) -> dict:
    """Eficacia de la revision y desviacion de tiempo/densidad de defectos por modulo."""
    total = len(incidentes)
    en_revision = sum(1 for i in incidentes if i["fase_deteccion"] == "revision")
    detalle = []
    for m in modulos:
        est, real, loc = float(m["horas_estimadas"]), float(m["horas_reales"]), int(m["loc"])
        defectos = sum(1 for i in incidentes if i["modulo"] == m["modulo"])
        detalle.append({
            "modulo": m["modulo"], "sprint": int(m["sprint"]),
            "puntos_historia": int(m["puntos_historia"]),
            "horas_estimadas": est, "horas_reales": real,
            "desviacion_horas": round(real - est, 2),
            "desviacion_pct": round((real - est) * 100 / est, 2) if est else 0.0,
            "loc": loc, "defectos": defectos,
            "densidad_kloc": round(defectos / (loc / 1000), 2) if loc else 0.0,
            "pct_del_total_de_defectos": _porcentaje(defectos, total)})
    est_t = sum(d["horas_estimadas"] for d in detalle)
    real_t = sum(d["horas_reales"] for d in detalle)
    loc_t = sum(d["loc"] for d in detalle)
    return {
        "defectos_total": total,
        "defectos_en_revision": en_revision,
        "eficacia_revision_pct": _porcentaje(en_revision, total),
        "horas_estimadas_total": est_t,
        "horas_reales_total": real_t,
        "desviacion_total_pct": round((real_t - est_t) * 100 / est_t, 2) if est_t else 0.0,
        "loc_total": loc_t,
        "densidad_global_kloc": round(total / (loc_t / 1000), 2) if loc_t else 0.0,
        "modulos": detalle,
    }