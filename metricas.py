"""Calcula metricas de proceso, de proyecto y estimaciones a partir de la carpeta datos/.

Uso:  python metricas.py            (resumen)
      python metricas.py --detalle   (ademas, todos los numeros para las tablas del reporte)
"""
import json
import math
import sys
from pathlib import Path

from qualiscan.estimacion import (estimacion_analoga, juicio_expertos,
                                  puntos_funcion, tres_puntos)
from qualiscan.procesos import horas_entre, leer_csv, metricas_proceso, metricas_proyecto


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


def estado(valor: float, meta: float, modo: str) -> str:
    """Cumple / Parcial / No cumple contra una meta ('max' = menor es mejor)."""
    ok = valor <= meta if modo == "max" else valor >= meta
    if ok:
        return "Cumple"
    if modo == "min" and valor == 0:
        return "No cumple"
    razon = valor / meta if modo == "max" else meta / valor
    return "Parcial" if razon <= 1.3 else "No cumple"


def detalle_para_reporte(carpeta: Path, r: dict) -> str:
    """Texto con TODOS los numeros que van en las tablas del reporte."""
    inc = leer_csv(carpeta / "incidentes.csv")
    cfg = json.loads((carpeta / "estimacion.json").read_text(encoding="utf-8"))
    p, y, e = r["proceso"], r["proyecto"], r["estimaciones"]
    L = []
    L.append("TABLA 22 - Incidentes (ID | modulo | severidad | fase | T.deteccion h | T.reparacion h)")
    for i in inc:
        L.append(f"  {i['id']} | {i['modulo']} | {i['severidad']} | {i['fase_deteccion']} | "
                 f"{horas_entre(i['inicio'], i['detectado']):.2f} | {horas_entre(i['detectado'], i['resuelto']):.2f}")
    L.append("\nTABLA 23 - Metricas de proceso")
    L.append(f"  MTTD = {p['mttd_horas']} h | MTTR = {p['mttr_horas']} h | criticos en pruebas = "
             f"{p['criticos_en_pruebas']} | criticos en produccion = {p['criticos_en_produccion']} | "
             f"eficacia de pruebas = {p['eficacia_pruebas_pct']}%")
    L.append("\nTABLA 24 - Defectos por fase")
    total = len(inc)
    for fase in ("revision", "pruebas", "produccion"):
        n = sum(1 for i in inc if i["fase_deteccion"] == fase)
        L.append(f"  {fase}: {n} ({n * 100 / total:.1f}%)")
    L.append(f"  total: {total} | eficacia de la revision = {y['eficacia_revision_pct']}%")
    L.append("\nTABLA 25 - Por modulo (modulo | sprint | est | real | desv% | LOC | defectos | def/KLOC | %defectos)")
    for m in y["modulos"]:
        L.append(f"  {m['modulo']} | {m['sprint']} | {m['horas_estimadas']} | {m['horas_reales']} | "
                 f"{m['desviacion_pct']} | {m['loc']} | {m['defectos']} | {m['densidad_kloc']} | "
                 f"{m['pct_del_total_de_defectos']}")
    L.append("\nTABLA 26 - Por sprint (sprint | puntos | est | real | desv% | defectos | def/KLOC)")
    sp = {}
    for m in y["modulos"]:
        s = sp.setdefault(m["sprint"], [0, 0, 0, 0, 0])
        s[0] += m["puntos_historia"]; s[1] += m["horas_estimadas"]; s[2] += m["horas_reales"]
        s[3] += m["loc"]; s[4] += m["defectos"]
    for k, s in sp.items():
        L.append(f"  {k} | {s[0]} | {s[1]} | {s[2]} | {(s[2] - s[1]) * 100 / s[1]:.2f} | {s[4]} | "
                 f"{s[4] / (s[3] / 1000):.2f}")
    L.append(f"  Parrafo: estimadas {y['horas_estimadas_total']} h, reales {y['horas_reales_total']} h, "
             f"desviacion {y['desviacion_total_pct']}%, densidad global {y['densidad_global_kloc']}/KLOC "
             f"({y['defectos_total']} defectos en {y['loc_total']} lineas)")
    L.append("\nTABLA 27 - Juicio de expertos " + str(cfg["expertos"]["nombres"]))
    for m, h in cfg["expertos"]["horas"].items():
        L.append(f"  {m}: {h} -> promedio {e['juicio_expertos']['por_modulo'][m]}")
    L.append(f"  TOTAL = {e['juicio_expertos']['total_horas']} h")
    a = e["analoga"]
    L.append("\nTABLA 28 - Estimacion analoga")
    L.append(f"  referencia: {a['referencia']} | horas ref = {a['horas_ref']} | LOC ref = {a['loc_ref']} | "
             f"LOC nuevo = {a['loc_nuevo']} | factor = {a['factor']} | ESTIMACION = {a['total_horas']} h")
    L.append("\nTABLA 29 - Tres puntos (modulo | O | M | P | esperado | desviacion)")
    for m, v in e["tres_puntos"]["por_modulo"].items():
        t = cfg["tres_puntos"][m]
        L.append(f"  {m} | {t['O']} | {t['M']} | {t['P']} | {v['esperado']} | {v['desviacion']}")
    L.append(f"  TOTAL = {e['tres_puntos']['total_horas']} h | desviacion total = {e['tres_puntos']['desviacion_total']}")
    f = e["puntos_funcion"]; c = cfg["puntos_funcion"]
    L.append("\nTABLAS 30 y 31 - Puntos de funcion")
    L.append(f"  EI={c['EI']} EO={c['EO']} EQ={c['EQ']} ILF={c['ILF']} EIF={c['EIF']} | UFP = {f['ufp']} | "
             f"suma GSC = {sum(c['gsc'])} | VAF = {f['vaf']} | PF ajustados = {f['pf_ajustados']} | "
             f"horas/PF = {f['horas_por_pf']} | ESFUERZO = {f['total_horas']} h")
    real = y["horas_reales_total"]
    L.append("\nTABLA 32 - Comparacion contra el tiempo real (tecnica | horas | diferencia | error%)")
    for nombre, v in (("Juicio de expertos", e["juicio_expertos"]["total_horas"]), ("Estimacion analoga", a["total_horas"]),
                      ("Tres puntos", e["tres_puntos"]["total_horas"]), ("Puntos de funcion", f["total_horas"])):
        L.append(f"  {nombre} | {v} | {v - real:+.2f} | {abs(v - real) * 100 / real:.1f}%")
    L.append(f"  Tiempo real = {real} h")
    L.append("\nTABLA 34 - Estados contra las metas (los demas indicadores no cambian)")
    for nombre, v, meta, modo in (("MTTD", p["mttd_horas"], 4, "max"), ("MTTR", p["mttr_horas"], 8, "max"),
                                  ("Eficacia de pruebas", p["eficacia_pruebas_pct"], 80, "min"),
                                  ("Eficacia de revision", y["eficacia_revision_pct"], 50, "min"),
                                  ("Desviacion de tiempo", y["desviacion_total_pct"], 20, "max"),
                                  ("Densidad registrada", y["densidad_global_kloc"], 30, "max")):
        L.append(f"  {nombre}: {v} (meta {'<=' if modo == 'max' else '>='} {meta}) -> {estado(v, meta, modo)}")
    return "\n".join(L)


if __name__ == "__main__":
    resultado = calcular(Path("datos"))
    imprimir(resultado)
    Path("reportes").mkdir(exist_ok=True)
    destino = Path("reportes") / "metricas_proceso_proyecto.json"
    destino.write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Reporte guardado en: {destino}")
    if "--detalle" in sys.argv:
        texto = detalle_para_reporte(Path("datos"), resultado)
        (Path("reportes") / "detalle_para_reporte.txt").write_text(texto, encoding="utf-8")
        print("\n" + "=" * 64 + "\n DETALLE PARA LAS TABLAS DEL REPORTE\n" + "=" * 64)
        print(texto)
        print("\n(Tambien guardado en reportes/detalle_para_reporte.txt)")