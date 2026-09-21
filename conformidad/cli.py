"""python3 -m conformidad <url> -- ver docs/suite-conformidad.md.

Por ahora solo existe el nivel A (anónimo, de solo lectura). --nivel queda
reservado para cuando se sumen B y C; pedirlos hoy falla explícito en vez de
correr a medias."""
import argparse
import json
import sys

from . import nivel_a, reporte


def main(argv=None):
    p = argparse.ArgumentParser(prog="python3 -m conformidad", description="Suite de conformidad de Vereda.")
    p.add_argument("url", help="Origen del nodo, ej. https://vereda.ar (sin /v1)")
    p.add_argument("--nivel", default="a", help="por ahora, solo 'a'")
    p.add_argument("--lat", type=float, default=nivel_a.LAT_DEFECTO, help=f"default {nivel_a.LAT_DEFECTO} (Buenos Aires)")
    p.add_argument("--lng", type=float, default=nivel_a.LNG_DEFECTO, help=f"default {nivel_a.LNG_DEFECTO} (Buenos Aires)")
    p.add_argument("--timeout", type=float, default=8.0, help="segundos por request (default 8)")
    p.add_argument("--formato", choices=["texto", "json"], default="texto")
    p.add_argument("--salida", help="archivo de salida; por defecto, stdout")
    p.add_argument(
        "--incluir-negativos",
        action="store_true",
        help=(
            "además, manda los cuerpos de ejemplos/casos/*.json sin sesión a las "
            "operaciones de escritura que coincidan, esperando 401. Es la única "
            "parte del nivel A que hace POST; apagado por default para no golpear "
            "un nodo de producción sin que quien corre la suite lo pida explícito."
        ),
    )
    args = p.parse_args(argv)

    if args.nivel.lower() != "a":
        print(f"todavía no existe el nivel {args.nivel!r}; solo 'a' (ver docs/suite-conformidad.md)", file=sys.stderr)
        return 2

    casos = nivel_a.correr(
        args.url,
        lat=args.lat,
        lng=args.lng,
        timeout=args.timeout,
        incluir_negativos=args.incluir_negativos,
    )

    salida = open(args.salida, "w", encoding="utf-8") if args.salida else sys.stdout
    try:
        if args.formato == "json":
            payload = {"a": reporte.a_dict("A", casos)}
            json.dump(payload, salida, ensure_ascii=False, indent=2)
            salida.write("\n")
            fallos = payload["a"]["fallo"]
        else:
            fallos = reporte.imprimir_texto("A", casos, archivo=salida)
    finally:
        if args.salida:
            salida.close()

    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
