"""Uso:
    python main.py <ruta_local>
    python main.py https://github.com/usuario/repo
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from qualiscan.report import analizar_proyecto, guardar_json, imprimir_resumen


def obtener_ruta(destino: str):
    """Devuelve (ruta_local, carpeta_temporal_o_None)."""
    if destino.startswith(("http://", "https://", "git@")):
        tmp = Path(tempfile.mkdtemp(prefix="qualiscan_"))
        nombre = destino.rstrip("/").removesuffix(".git").split("/")[-1]
        carpeta = tmp / nombre
        print(f"Clonando {destino} ...")
        subprocess.run(["git", "clone", "--depth", "1", destino, str(carpeta)], check=True)
        return carpeta, tmp
    return Path(destino).resolve(), None


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    ruta, tmp = obtener_ruta(sys.argv[1])
    try:
        resultado = analizar_proyecto(ruta)
        imprimir_resumen(resultado)
        print(f"Reporte guardado en: {guardar_json(resultado, Path('reportes'))}")
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()