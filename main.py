"""Uso:
    python main.py <ruta_local_o_url_github>            (con IA)
    python main.py <ruta_local_o_url_github> --sin-ia   (solo reglas)
    python main.py --modelos                            (modelos disponibles en tu clave)
"""
import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from qualiscan.ia import cargar_env, imprimir_revision, listar_modelos, revisar_con_ia
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
    cargar_env()
    parser = argparse.ArgumentParser(description="QualiScan AI")
    parser.add_argument("destino", nargs="?", help="ruta local o URL de GitHub")
    parser.add_argument("--sin-ia", action="store_true", help="usar solo reglas")
    parser.add_argument("--modelos", action="store_true", help="listar modelos de Gemini")
    args = parser.parse_args()

    if args.modelos:
        print("\n".join(listar_modelos()))
        return
    if not args.destino:
        parser.print_help()
        return

    ruta, tmp = obtener_ruta(args.destino)
    try:
        resultado = analizar_proyecto(ruta)
        imprimir_resumen(resultado)
        revision = revisar_con_ia(resultado, ruta, usar_ia=not args.sin_ia)
        imprimir_revision(revision)
        resultado["revision_ia"] = revision
        print(f"Reporte guardado en: {guardar_json(resultado, Path('reportes'))}")
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()