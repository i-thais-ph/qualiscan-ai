"""Calcula metricas de proceso, de proyecto y estimaciones a partir de la carpeta datos/.

Uso:  python metricas.py
"""
import json
from pathlib import Path

from qualiscan.estimacion import (estimacion_analoga, juicio_expertos,
                                  puntos_funcion, tres_puntos)
from qualiscan.procesos import leer_csv, metricas_proceso, metricas_proyecto


def calcular(carpeta: Path) -> dict:
    incidentes = leer_csv(carpeta / "incidentes.csv")
    modulos = leer_csv(carpeta / "modulos.csv")
    est = json.loads((carpeta / "estimacion.json").read_text(encoding="utf-8"))
    proyecto = metricas_proyecto(incidentes, modulos)
    estimaciones = {
        "juicio_expertos": juicio_expertos(est["expertos"]),
        "analoga": estimacion_analoga(est["analoga"], proyecto["loc_total"]),
        "tres_puntos": tres_puntos(est["tres_puntos"]),
        "puntos_funcion": puntos_funcion(est["puntos_funcion"]),
    }
    return {"proceso": metricas_proceso(incidentes), "proyecto": proyecto,
            "estimaciones": estimaciones}


def imprimir(r: dict) -> None:
    p, y, e = r["proceso"], r["proyecto"], r["estimaciones"]
    print("\n" + "=" * 64)
    print(" METRICAS DE PROCESO")
    print("=" * 64)
    print(f" MTTD (tiempo medio de deteccion) : {p['mttd_horas']} h")
    print(f" MTTR (tiempo medio de reparacion): {p['mttr_horas']} h")
    print(f" Criticos detectados en pruebas   : {p['criticos_en_pruebas']}")
    print(f" Criticos que llegaron a produccion: {p['criticos_en_produccion']}")
    print(f" Eficacia de las pruebas          : {p['eficacia_pruebas_pct']} %")
    print("\n" + "=" * 64)
    print(" METRICAS DE PROYECTO")
    print("=" * 64)
    print(f" Eficacia de la revision: {y['eficacia_revision_pct']} % "
          f"({y['defectos_en_revision']} de {y['defectos_total']} defectos)")
    print(f" Densidad global        : {y['densidad_global_kloc']} defectos/KLOC")
    print(f" Desviacion total       : {y['desviacion_total_pct']} % "
          f"({y['horas_estimadas_total']} h estimadas vs {y['horas_reales_total']} h reales)")
    print("\n Modulo    Sprint  Est(h)  Real(h)  Desv%   LOC  Def  Def/KLOC  %Def")
    for m in y["modulos"]:
        print(f" {m['modulo']:<9} {m['sprint']:^6} {m['horas_estimadas']:>6} {m['horas_reales']:>8} "
              f"{m['desviacion_pct']:>6} {m['loc']:>5} {m['defectos']:>4} {m['densidad_kloc']:>8} "
              f"{m['pct_del_total_de_defectos']:>6}")
    print("\n" + "=" * 64)
    print(" TECNICAS DE ESTIMACION (horas totales)")
    print("=" * 64)
    print(f" 1. Juicio de expertos : {e['juicio_expertos']['total_horas']}")
    print(f" 2. Estimacion analoga : {e['analoga']['total_horas']}")
    print(f" 3. Tres puntos (PERT) : {e['tres_puntos']['total_horas']} "
          f"(desv. +/- {e['tres_puntos']['desviacion_total']})")
    print(f" 4. Puntos de funcion  : {e['puntos_funcion']['total_horas']} "
          f"({e['puntos_funcion']['pf_ajustados']} PF)")
    print(f" Tiempo real           : {y['horas_reales_total']}")
    print("=" * 64 + "\n")


if __name__ == "__main__":
    resultado = calcular(Path("datos"))
    imprimir(resultado)
    Path("reportes").mkdir(exist_ok=True)
    destino = Path("reportes") / "metricas_proceso_proyecto.json"
    destino.write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Reporte guardado en: {destino}")