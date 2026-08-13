"""Validações de destino usadas antes de autenticar nos portais."""

from __future__ import annotations

from urllib.parse import urlparse


def url_https_corresponde_dominio(
    url: str,
    dominio_oficial: str,
) -> bool:
    """Aceita somente HTTPS e correspondência exata do hostname."""

    try:
        endereco = urlparse(str(url))
    except (TypeError, ValueError):
        return False

    return (
        endereco.scheme.casefold() == "https"
        and (endereco.hostname or "").casefold()
        == str(dominio_oficial).casefold()
    )
