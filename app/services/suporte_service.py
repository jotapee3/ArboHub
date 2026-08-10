from __future__ import annotations

import os
import webbrowser
from urllib.parse import quote, urlencode


RESPONSAVEL_SUPORTE = "João Paulo Velho"
EMAIL_SUPORTE = "cevs.joaov@gmail.com"
ROTULO_VERSAO_ARBOHUB = "ArboHub v0.6"
ASSUNTO_SUPORTE = "ArboHub — Solicitação de suporte"


class SuporteService:
    """Prepara e abre uma solicitação de suporte por e-mail."""

    def montar_link_email(
        self,
        nome_usuario: str,
        conta_usuario: str
    ) -> str:
        nome = (
            str(nome_usuario).strip()
            or "Usuário não identificado"
        )
        conta = (
            str(conta_usuario).strip()
            or "Conta não identificada"
        )

        corpo = (
            f"Olá, {RESPONSAVEL_SUPORTE}.\n\n"
            "Gostaria de solicitar suporte no ArboHub.\n\n"
            "Descreva abaixo o problema, a mudança ou a nova "
            "implementação desejada:\n\n\n"
            "---\n"
            "Informações automáticas do ArboHub\n"
            f"Versão: {ROTULO_VERSAO_ARBOHUB}\n"
            f"Usuário do Windows: {nome}\n"
            f"Conta do Windows: {conta}"
        )

        consulta = urlencode(
            {
                "subject": ASSUNTO_SUPORTE,
                "body": corpo
            },
            quote_via=quote
        )
        return f"mailto:{EMAIL_SUPORTE}?{consulta}"

    def abrir_solicitacao(
        self,
        nome_usuario: str,
        conta_usuario: str
    ) -> None:
        link = self.montar_link_email(
            nome_usuario=nome_usuario,
            conta_usuario=conta_usuario
        )

        if hasattr(os, "startfile"):
            os.startfile(link)
            return

        if not webbrowser.open(link, new=1):
            raise RuntimeError(
                "Nenhum aplicativo de e-mail respondeu à "
                "solicitação de abertura."
            )
