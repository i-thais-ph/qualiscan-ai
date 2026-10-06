"""Revision de codigo con IA (Gemini) con respaldo automatico sin IA.

Solo usa la libreria estandar de Python (urllib), sin instalar nada extra.
La clave se lee del archivo .env (GEMINI_API_KEY). Nunca se escribe en el codigo.
"""
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

URL_BASE = "https://generativelanguage.googleapis.com/v1beta"
# Si el primero falla (modelo no disponible o limite), prueba el siguiente.
MODELOS_POR_DEFECTO = ["gemini-flash-latest", "gemini-flash-lite-latest", "gemini-2.5-flash"]
MAX_FUNCIONES = 3        # funciones mas complejas que se envian a la IA
MAX_CARACTERES = 6000    # limite de codigo por funcion enviada


def cargar_env(ruta: str = ".env") -> None:
    """Lee el archivo .env y carga sus variables (formato CLAVE=valor)."""
    archivo = Path(ruta)
    if not archivo.exists():
        return
    for linea in archivo.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#") and "=" in linea:
            clave, valor = linea.split("=", 1)
            os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


def _llamar_modelo(modelo: str, prompt: str, clave: str) -> str:
    cuerpo = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{URL_BASE}/models/{modelo}:generateContent", data=cuerpo,
        headers={"Content-Type": "application/json", "x-goog-api-key": clave})
    with urllib.request.urlopen(req, timeout=40) as resp:
        datos = json.loads(resp.read().decode("utf-8"))
    return datos["candidates"][0]["content"]["parts"][0]["text"]


def consultar_gemini(prompt: str) -> tuple:
    """Devuelve (texto, modelo_usado). Lanza RuntimeError si ningun modelo responde."""
    clave = os.environ.get("GEMINI_API_KEY", "")
    if not clave:
        raise RuntimeError("no hay GEMINI_API_KEY en el archivo .env")
    modelos = [m for m in [os.environ.get("GEMINI_MODEL")] + MODELOS_POR_DEFECTO if m]
    errores = []
    for modelo in modelos:
        try:
            return _llamar_modelo(modelo, prompt, clave), modelo
        except urllib.error.HTTPError as e:
            errores.append(f"{modelo}: HTTP {e.code}")
        except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError) as e:
            errores.append(f"{modelo}: {type(e).__name__}")
    raise RuntimeError("; ".join(errores))


def listar_modelos() -> list:
    """Util para diagnostico: modelos que acepta tu clave."""
    clave = os.environ.get("GEMINI_API_KEY", "")
    req = urllib.request.Request(f"{URL_BASE}/models?pageSize=100",
                                 headers={"x-goog-api-key": clave})
    with urllib.request.urlopen(req, timeout=30) as resp:
        datos = json.loads(resp.read().decode("utf-8"))
    return [m["name"].split("/")[-1] for m in datos.get("models", [])
            if "generateContent" in m.get("supportedGenerationMethods", [])]


def _fragmento(base: Path, f: dict) -> str:
    lineas = (base / f["archivo"]).read_text(encoding="utf-8", errors="ignore").splitlines()
    texto = "\n".join(lineas[f["linea"] - 1: f["linea"] - 1 + f["longitud"]])
    if len(texto) > MAX_CARACTERES:
        texto = texto[:MAX_CARACTERES] + "\n# ... [FRAGMENTO TRUNCADO]"
    return texto


def _construir_prompt(base: Path, funciones: list) -> str:
    bloques = []
    for f in funciones:
        bloques.append(f"### Archivo: {f['archivo']} | Funcion: {f['nombre']} | "
                       f"Complejidad ciclomatica: {f['complejidad']}\n{_fragmento(base, f)}")
    return (
        "Eres un revisor de codigo Python senior. Revisa las siguientes funciones y "
        "detecta defectos reales, riesgos de fiabilidad y problemas de mantenibilidad. "
        "IMPORTANTE: solo ves fragmentos aislados; no incluyen los imports ni el resto "
        "del archivo y pueden estar truncados. No reportes errores de sintaxis, nombres "
        "no definidos ni imports faltantes por esa causa, y reporta solo problemas de los "
        "que tengas certeza (si dudas, no lo incluyas). "
        "Responde SOLO con un arreglo JSON (sin texto adicional) donde cada elemento "
        'tenga las claves: "archivo", "funcion", "severidad" (alta|media|baja), '
        '"problema" y "sugerencia". Escribe en espanol, maximo 2 oraciones por campo.\n\n'
        + "\n\n".join(bloques))


def _limpiar_json(texto: str) -> list:
    texto = texto.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    datos = json.loads(texto)
    return datos if isinstance(datos, list) else [datos]


def _revision_por_reglas(resultado: dict, motivo: str) -> dict:
    """Respaldo: sugerencias a partir de las reglas, sin IA ni internet."""
    orden = {"alta": 0, "media": 1, "baja": 2}
    hall = sorted(resultado["detalle_hallazgos"], key=lambda h: orden[h["severidad"]])[:8]
    return {
        "modo": "reglas", "motivo": motivo, "modelo": None, "segundos": 0,
        "sugerencias": [{"archivo": h["archivo"], "funcion": f"linea {h['linea']}",
                         "severidad": h["severidad"], "problema": h["mensaje"],
                         "sugerencia": "Corregir segun la regla " + h["regla"]} for h in hall]}


def revisar_con_ia(resultado: dict, base: Path, usar_ia: bool = True) -> dict:
    """Intenta usar Gemini; si algo falla, usa el modo de reglas."""
    if not usar_ia:
        return _revision_por_reglas(resultado, "IA desactivada (--sin-ia)")
    funciones = sorted(resultado["detalle_funciones"], key=lambda f: -f["complejidad"])
    funciones = funciones[:MAX_FUNCIONES]
    if not funciones:
        return _revision_por_reglas(resultado, "no hay funciones que revisar")
    inicio = time.time()
    try:
        texto, modelo = consultar_gemini(_construir_prompt(base, funciones))
        sugerencias = _limpiar_json(texto)
    except (RuntimeError, ValueError) as e:
        return _revision_por_reglas(resultado, f"IA no disponible ({e})")
    return {"modo": "ia", "motivo": "", "modelo": modelo,
            "segundos": round(time.time() - inicio, 2), "sugerencias": sugerencias}


def imprimir_revision(rev: dict) -> None:
    etiqueta = f"IA ({rev['modelo']}, {rev['segundos']} s)" if rev["modo"] == "ia" \
        else f"REGLAS (sin IA) - {rev['motivo']}"
    print(f"\n REVISION DE CODIGO: {etiqueta}")
    print("-" * 60)
    for s in rev["sugerencias"]:
        print(f" [{str(s.get('severidad', '')).upper():5}] {s.get('archivo')} :: {s.get('funcion')}")
        print(f"   Problema  : {s.get('problema')}")
        print(f"   Sugerencia: {s.get('sugerencia')}")
    print("=" * 60 + "\n")