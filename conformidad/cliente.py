"""Cliente HTTP defensivo.

Una suite que se rompe con una respuesta inesperada de un nodo ajeno no sirve
para juzgarlo. Nada de lo que un nodo devuelva (o no devuelva) puede tirar una
excepción sin atrapar hasta el llamador: DNS que no resuelve, timeout, texto
que no es JSON, conexión rechazada, redirect infinito. Todo eso se convierte
en una `Respuesta` con `ok=False` y un motivo en español.
"""
from dataclasses import dataclass, field
from typing import Any, Optional

import requests

TIMEOUT_S = 8


@dataclass
class Respuesta:
    ok: bool
    estado: Optional[int] = None
    cabeceras: dict = field(default_factory=dict)
    cuerpo: Any = None
    cuerpo_es_json: bool = False
    motivo: str = ""


def _con_cuerpo(r: requests.Response) -> Respuesta:
    cuerpo, es_json = None, False
    if r.text:
        try:
            cuerpo = r.json()
            es_json = True
        except ValueError:
            cuerpo = r.text
    return Respuesta(ok=True, estado=r.status_code, cabeceras=dict(r.headers), cuerpo=cuerpo, cuerpo_es_json=es_json)


def _pedido(metodo, url, **kw):
    try:
        r = requests.request(metodo, url, timeout=kw.pop("timeout", TIMEOUT_S), **kw)
    except requests.exceptions.Timeout:
        return Respuesta(ok=False, motivo=f"tiempo de espera agotado contra {url}")
    except requests.exceptions.ConnectionError as e:
        return Respuesta(ok=False, motivo=f"no se pudo conectar a {url} ({_causa(e)})")
    except requests.exceptions.TooManyRedirects:
        return Respuesta(ok=False, motivo=f"demasiados redirects en {url}")
    except requests.exceptions.RequestException as e:
        return Respuesta(ok=False, motivo=f"error de red contra {url} ({_causa(e)})")
    return _con_cuerpo(r)


def _causa(e: Exception) -> str:
    # requests envuelve urllib3 que envuelve socket/ssl: el texto trae DNS,
    # conexión rechazada o certificado en algún lado, pero es largo. Se
    # recorta -- alcanza para saber qué pasó sin siete líneas de reintentos.
    texto = str(e) or type(e).__name__
    return texto[:200]


def get(url, headers=None, timeout=TIMEOUT_S) -> Respuesta:
    return _pedido("GET", url, headers=headers or {}, timeout=timeout)


def post(url, headers=None, json_body=None, timeout=TIMEOUT_S) -> Respuesta:
    return _pedido("POST", url, headers=headers or {}, json=json_body, timeout=timeout)


def solicitud(metodo, url, headers=None, json_body=None, timeout=TIMEOUT_S) -> Respuesta:
    return _pedido(metodo.upper(), url, headers=headers or {}, json=json_body, timeout=timeout)
