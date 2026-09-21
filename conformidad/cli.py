"""python3 -m conformidad <url> -- ver docs/suite-conformidad.md.

Nivel B (autenticado) todavía no existe; pedirlo hoy falla explícito en vez
de correr a medias."""
import argparse
import json
import sys

from . import nivel_a, nivel_c, reporte

NIVELES_DISPONIBLES = {"a", "c"}


def main(argv=None):
    p = argparse.ArgumentParser(prog="python3 -m conformidad", description="Suite de conformidad de Vereda.")
    p.add_argument("url", help="Origen del nodo, ej. https://vereda.ar (sin /v1)")
    p.add_argument("--nivel", default="a", help="'a' (anónimo), 'c' (federación) o 'a,c'. 'b' todavía no existe.")
    p.add_argument("--lat", type=float, default=nivel_a.LAT_DEFECTO, help=f"nivel A -- default {nivel_a.LAT_DEFECTO} (Buenos Aires)")
    p.add_argument("--lng", type=float, default=nivel_a.LNG_DEFECTO, help=f"nivel A -- default {nivel_a.LNG_DEFECTO} (Buenos Aires)")
    p.add_argument("--timeout", type=float, default=8.0, help="segundos por request (default 8)")
    p.add_argument("--formato", choices=["texto", "json"], default="texto")
    p.add_argument("--salida", help="archivo de salida; por defecto, stdout")
    p.add_argument(
        "--incluir-negativos",
        action="store_true",
        help=(
            "nivel A -- además, manda los cuerpos de ejemplos/casos/*.json sin sesión a las "
            "operaciones de escritura que coincidan, esperando 401. Apagado por default para "
            "no golpear un nodo de producción sin que quien corre la suite lo pida explícito."
        ),
    )
    args = p.parse_args(argv)

    niveles = [n.strip().lower() for n in args.nivel.split(",") if n.strip()]
    desconocidos = [n for n in niveles if n not in NIVELES_DISPONIBLES]
    if desconocidos:
        print(f"todavía no existe el nivel {desconocidos[0]!r}; disponibles: {sorted(NIVELES_DISPONIBLES)} (ver docs/suite-conformidad.md)", file=sys.stderr)
        return 2

    resultados = {}
    if "a" in niveles:
        resultados["a"] = nivel_a.correr(args.url, lat=args.lat, lng=args.lng, timeout=args.timeout, incluir_negativos=args.incluir_negativos)
    if "c" in niveles:
        resultados["c"] = nivel_c.correr(args.url, timeout=args.timeout)

    salida = open(args.salida, "w", encoding="utf-8") if args.salida else sys.stdout
    try:
        if args.formato == "json":
            payload = {nivel: reporte.a_dict(nivel.upper(), casos) for nivel, casos in resultados.items()}
            json.dump(payload, salida, ensure_ascii=False, indent=2)
            salida.write("\n")
            fallos = sum(p["fallo"] for p in payload.values())
        else:
            fallos = sum(reporte.imprimir_texto(nivel.upper(), casos, archivo=salida) for nivel, casos in resultados.items())
    finally:
        if args.salida:
            salida.close()

    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
