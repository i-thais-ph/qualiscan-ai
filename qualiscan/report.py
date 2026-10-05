"""Calculo de indicadores y generacion del reporte (consola y JSON)."""
import json
from datetime import datetime
from pathlib import Path

from .metrics import (analizar_archivo, listar_archivos_python, tiene_pruebas)


def analizar_proyecto(base: Path) -> dict:
    archivos = listar_archivos_python(base)
    resultados = [analizar_archivo(p, base) for p in archivos]
    funciones = [f for r in resultados for f in r.funciones]
    hallazgos = [h for r in resultados for h in r.hallazgos]
    loc = sum(r.lineas_codigo for r in resultados)
    # Defectos = hallazgos de severidad alta o media
    defectos = [h for h in hallazgos if h.severidad in ("alta", "media")]
    cc_prom = (sum(f.complejidad for f in funciones) / len(funciones)) if funciones else 0
    return {
        "proyecto": base.name,
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "archivos": len(archivos),
        "lineas_codigo": loc,
        "funciones": len(funciones),
        "complejidad_promedio": round(cc_prom, 2),
        "complejidad_maxima": max((f.complejidad for f in funciones), default=0),
        "funciones_complejas": sum(1 for f in funciones if f.complejidad > 10),
        "tiene_pruebas": tiene_pruebas(archivos),
        "hallazgos_total": len(hallazgos),
        "defectos": len(defectos),
        "densidad_defectos_kloc": round(len(defectos) / (loc / 1000), 2) if loc else 0,
        "detalle_funciones": [f.__dict__ | {"rango": f.rango} for f in funciones],
        "detalle_hallazgos": [h.__dict__ for h in hallazgos],
    }


def imprimir_resumen(r: dict) -> None:
    print("\n" + "=" * 60)
    print(f" QUALISCAN AI - Reporte de {r['proyecto']}")
    print("=" * 60)
    print(f" Archivos Python analizados : {r['archivos']}")
    print(f" Lineas de codigo (LOC)     : {r['lineas_codigo']}")
    print(f" Funciones                  : {r['funciones']}")
    print(f" Complejidad promedio       : {r['complejidad_promedio']}")
    print(f" Complejidad maxima         : {r['complejidad_maxima']}")
    print(f" Funciones con CC > 10      : {r['funciones_complejas']}")
    print(f" Pruebas detectadas         : {'Si' if r['tiene_pruebas'] else 'No'}")
    print(f" Defectos (severidad alta/media): {r['defectos']}")
    print(f" Densidad de defectos       : {r['densidad_defectos_kloc']} por KLOC")
    print("-" * 60)
    peores = sorted(r["detalle_funciones"], key=lambda f: -f["complejidad"])[:5]
    print(" Top 5 funciones mas complejas:")
    for f in peores:
        print(f"   [{f['rango']}] CC={f['complejidad']:<3} {f['archivo']}:{f['linea']} {f['nombre']}()")
    print("=" * 60 + "\n")


def guardar_json(r: dict, carpeta: Path) -> Path:
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / f"reporte_{r['proyecto']}.json"
    destino.write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    return destino