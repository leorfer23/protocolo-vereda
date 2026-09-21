"""Reporte de una corrida: consola (mismo lenguaje ✓/✗ de validar.py, con –
para lo omitido) y JSON para CI o para una segunda lectura. Un nivel no
corrido nunca se mezcla con los que sí, ni cuenta como fallado."""
import sys

SIMBOLO = {"ok": "✓", "fallo": "✗", "omitido": "–"}


def imprimir_texto(nombre_nivel, casos, archivo=sys.stdout):
    por_categoria = {}
    for c in casos:
        por_categoria.setdefault(c.categoria, []).append(c)
    for categoria, items in por_categoria.items():
        print(f"\n== nivel {nombre_nivel} · {categoria} ==", file=archivo)
        for c in items:
            linea = f"{SIMBOLO[c.resultado]} {c.operation_id}: {c.descripcion}"
            if c.motivo:
                linea += f" — {c.motivo}"
            print(linea, file=archivo)
    ok = sum(1 for c in casos if c.resultado == "ok")
    fallo = sum(1 for c in casos if c.resultado == "fallo")
    omitido = sum(1 for c in casos if c.resultado == "omitido")
    print(f"\nnivel {nombre_nivel}: {ok} ok, {fallo} fallaron, {omitido} omitidos (de {len(casos)})", file=archivo)
    return fallo


def a_dict(nombre_nivel, casos):
    return {
        "corrido": True,
        "ok": sum(1 for c in casos if c.resultado == "ok"),
        "fallo": sum(1 for c in casos if c.resultado == "fallo"),
        "omitido": sum(1 for c in casos if c.resultado == "omitido"),
        "casos": [
            {
                "categoria": c.categoria,
                "operation_id": c.operation_id,
                "descripcion": c.descripcion,
                "resultado": c.resultado,
                "motivo": c.motivo,
                "evidencia": c.evidencia,
            }
            for c in casos
        ],
    }
