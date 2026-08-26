from __future__ import annotations


class SessaoSinanExpirada(RuntimeError):
    """Indica que o portal perdeu a autenticação da sessão atual."""
