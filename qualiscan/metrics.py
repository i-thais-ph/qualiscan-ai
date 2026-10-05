"""Metricas de producto: complejidad ciclomatica, lineas de codigo y hallazgos."""
import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

CARPETAS_IGNORADAS = {".git", "venv", ".venv", "env", "node_modules",
                      "__pycache__", "site-packages", "build", "dist", ".tox"}


@dataclass
class Funcion:
    archivo: str
    nombre: str
    linea: int
    complejidad: int
    longitud: int

    @property
    def rango(self) -> str:
        c = self.complejidad
        for limite, letra in ((5, "A"), (10, "B"), (20, "C"), (30, "D"), (40, "E")):
            if c <= limite:
                return letra
        return "F"


@dataclass
class Hallazgo:
    archivo: str
    linea: int
    severidad: str   # "alta", "media", "baja"
    regla: str
    mensaje: str


@dataclass
class ResultadoArchivo:
    archivo: str
    lineas_codigo: int = 0
    funciones: list = field(default_factory=list)
    hallazgos: list = field(default_factory=list)


def complejidad_ciclomatica(nodo: ast.AST) -> int:
    """CC = 1 + numero de puntos de decision dentro de la funcion."""
    total = 1
    pila = list(ast.iter_child_nodes(nodo))
    while pila:
        n = pila.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue  # las funciones anidadas se miden por separado
        if isinstance(n, (ast.If, ast.For, ast.AsyncFor, ast.While,
                          ast.ExceptHandler, ast.IfExp, ast.Assert)):
            total += 1
        elif isinstance(n, ast.BoolOp):
            total += len(n.values) - 1
        elif isinstance(n, ast.comprehension):
            total += 1 + len(n.ifs)
        elif hasattr(ast, "match_case") and isinstance(n, ast.match_case):
            total += 1
        pila.extend(ast.iter_child_nodes(n))
    return total


def contar_lineas_codigo(texto: str) -> int:
    """Lineas que no estan vacias ni son comentarios puros."""
    return sum(1 for l in texto.splitlines()
               if l.strip() and not l.strip().startswith("#"))


PATRON_SECRETO = re.compile(
    r"""(password|passwd|secret|api_?key|token)\s*=\s*['"][^'"]{4,}['"]""", re.I)


def detectar_hallazgos(ruta: str, texto: str, arbol: ast.AST) -> list:
    """Reglas basicas de calidad (modo sin IA)."""
    hall = []
    for n in ast.walk(arbol):
        if isinstance(n, ast.ExceptHandler) and n.type is None:
            hall.append(Hallazgo(ruta, n.lineno, "media", "R01",
                                 "except sin tipo: oculta errores inesperados"))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) \
                and n.func.id in ("eval", "exec"):
            hall.append(Hallazgo(ruta, n.lineno, "alta", "R02",
                                 f"uso de {n.func.id}(): riesgo de seguridad"))
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for d in n.args.defaults + [x for x in n.args.kw_defaults if x]:
                if isinstance(d, (ast.List, ast.Dict, ast.Set)):
                    hall.append(Hallazgo(ruta, n.lineno, "media", "R03",
                                         f"'{n.name}' usa argumento mutable por defecto"))
            if not ast.get_docstring(n) and not n.name.startswith("_"):
                hall.append(Hallazgo(ruta, n.lineno, "baja", "R04",
                                     f"'{n.name}' no tiene docstring"))
            largo = (n.end_lineno or n.lineno) - n.lineno + 1
            if largo > 50:
                hall.append(Hallazgo(ruta, n.lineno, "media", "R05",
                                     f"'{n.name}' tiene {largo} lineas (maximo sugerido: 50)"))
            cc = complejidad_ciclomatica(n)
            if cc > 10:
                sev = "alta" if cc > 20 else "media"
                hall.append(Hallazgo(ruta, n.lineno, sev, "R06",
                                     f"'{n.name}' tiene complejidad {cc} (maximo sugerido: 10)"))
    for i, linea in enumerate(texto.splitlines(), 1):
        if PATRON_SECRETO.search(linea):
            hall.append(Hallazgo(ruta, i, "alta", "R07",
                                 "posible credencial escrita directamente en el codigo"))
        if re.search(r"#\s*(TODO|FIXME|HACK)", linea, re.I):
            hall.append(Hallazgo(ruta, i, "baja", "R08", "tarea pendiente en el codigo"))
    return hall


def analizar_archivo(ruta: Path, base: Path) -> ResultadoArchivo:
    rel = str(ruta.relative_to(base))
    res = ResultadoArchivo(archivo=rel)
    try:
        texto = ruta.read_text(encoding="utf-8", errors="ignore")
        arbol = ast.parse(texto)
    except (SyntaxError, ValueError):
        res.hallazgos.append(Hallazgo(rel, 1, "alta", "R00",
                                      "error de sintaxis: el archivo no se pudo analizar"))
        return res
    res.lineas_codigo = contar_lineas_codigo(texto)
    for n in ast.walk(arbol):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            res.funciones.append(Funcion(
                rel, n.name, n.lineno, complejidad_ciclomatica(n),
                (n.end_lineno or n.lineno) - n.lineno + 1))
    res.hallazgos = detectar_hallazgos(rel, texto, arbol)
    return res


def listar_archivos_python(base: Path) -> list:
    return [p for p in sorted(base.rglob("*.py"))
            if not CARPETAS_IGNORADAS.intersection(p.relative_to(base).parts)]


def tiene_pruebas(archivos: list) -> bool:
    return any(p.name.startswith("test_") or p.name.endswith("_test.py")
               or "tests" in p.parts for p in archivos)