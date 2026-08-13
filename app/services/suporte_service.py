from __future__ import annotations

import os
import webbrowser
from urllib.parse import quote, urlencode

from app.core.versao import ROTULO_VERSAO_ARBOHUB

ASSUNTO_SUPORTE = "ArboHub — Solicitação de suporte"


class SuporteService:
    """Prepara e abre uma solicitação de suporte por e-mail."""

    def montar_link_email(
        self,
        destinatario: str,
        nome_destinatario: str = "",
    ) -> str:
        email = str(destinatario).strip().casefold()

        if not self._email_valido(email):
            raise ValueError(
                "Configure um e-mail institucional válido para a "
                "supervisão antes de preparar a solicitação."
            )

        nome = str(nome_destinatario).strip()
        saudacao = f"Olá, {nome}." if nome else "Olá."

        corpo = (
            f"{saudacao}\n\n"
            "Gostaria de solicitar suporte no ArboHub.\n\n"
            "Descreva abaixo o problema, a mudança ou a nova "
            "implementação desejada:\n\n\n"
            "---\n"
            "Informações automáticas do ArboHub\n"
            f"Versão: {ROTULO_VERSAO_ARBOHUB}\n\n"
            "Antes de enviar, remova dados de pacientes, senhas, "
            "números de solicitação, caminhos internos e capturas "
            "dos portais."
        )

        consulta = urlencode(
            {
                "subject": ASSUNTO_SUPORTE,
                "body": corpo
            },
            quote_via=quote
        )
        return f"mailto:{email}?{consulta}"

    def abrir_solicitacao(
        self,
        destinatario: str,
        nome_destinatario: str = "",
    ) -> None:
        link = self.montar_link_email(
            destinatario=destinatario,
            nome_destinatario=nome_destinatario,
        )

        if hasattr(os, "startfile"):
            os.startfile(link)
            return

        if not webbrowser.open(link, new=1):
            raise RuntimeError(
                "Nenhum aplicativo de e-mail respondeu à "
                "solicitação de abertura."
            )

    @staticmethod
    def _email_valido(email: str) -> bool:
        if " " in email or email.count("@") != 1:
            return False

        usuario, dominio = email.rsplit("@", 1)
        return bool(
            usuario
            and dominio
            and "." in dominio
            and not dominio.startswith(".")
            and not dominio.endswith(".")
        )
