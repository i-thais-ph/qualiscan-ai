"""Tecnicas de estimacion: juicio de expertos, analoga, tres puntos y puntos de funcion."""
import math

# Pesos IFPUG de complejidad promedio
PESOS_PF = {"EI": 4, "EO": 5, "EQ": 4, "ILF": 10, "EIF": 7}


def juicio_expertos(cfg: dict) -> dict:
    """Promedio de las estimaciones de varios expertos por modulo."""
    por_modulo = {m: round(sum(v) / len(v), 2) for m, v in cfg["horas"].items()}
    return {"expertos": cfg["nombres"], "por_modulo": por_modulo,
            "total_horas": round(sum(por_modulo.values()), 2)}


def estimacion_analoga(cfg: dict, loc_nuevo: int) -> dict:
    """Horas del proyecto de referencia escaladas por tamano (LOC)."""
    factor = loc_nuevo / cfg["loc"]
    return {"referencia": cfg["proyecto_referencia"], "horas_ref": cfg["horas"],
            "loc_ref": cfg["loc"], "loc_nuevo": loc_nuevo, "factor": round(factor, 3),
            "total_horas": round(cfg["horas"] * factor, 2)}


def tres_puntos(cfg: dict) -> dict:
    """PERT: E = (O + 4M + P) / 6 ; desviacion = (P - O) / 6."""
    por_modulo, varianza = {}, 0.0
    for m, v in cfg.items():
        e = (v["O"] + 4 * v["M"] + v["P"]) / 6
        s = (v["P"] - v["O"]) / 6
        por_modulo[m] = {"esperado": round(e, 2), "desviacion": round(s, 2)}
        varianza += s ** 2
    return {"por_modulo": por_modulo,
            "total_horas": round(sum(x["esperado"] for x in por_modulo.values()), 2),
            "desviacion_total": round(math.sqrt(varianza), 2)}


def puntos_funcion(cfg: dict) -> dict:
    """PF sin ajustar (UFP), factor de ajuste (VAF) y horas estimadas."""
    ufp = sum(cfg[k] * peso for k, peso in PESOS_PF.items())
    vaf = 0.65 + 0.01 * sum(cfg["gsc"])
    pf = ufp * vaf
    return {"ufp": ufp, "vaf": round(vaf, 2), "pf_ajustados": round(pf, 2),
            "horas_por_pf": cfg["horas_por_pf"], "total_horas": round(pf * cfg["horas_por_pf"], 2)}