from __future__ import annotations

from pathlib import Path

from app.services.tema_interface_service import TemaInterfaceService


class IconeAplicativoService:
    """Seleciona um ícone legível sobre o tema atual do Windows."""

    ICONES_POR_TEMA_SISTEMA = {
        "claro": "arbohub_light.ico",
        "escuro": "arbohub_dark.ico",
    }
    ICONE_PADRAO = "arbohub.ico"

    def __init__(
        self,
        tema_service: TemaInterfaceService | None = None,
    ):
        self.tema_service = (
            tema_service
            if tema_service is not None
            else TemaInterfaceService()
        )

    def obter_nome_icone(self) -> str:
        tema_sistema = self.tema_service.obter_tema_sistema()

        return self.ICONES_POR_TEMA_SISTEMA.get(
            tema_sistema,
            self.ICONE_PADRAO,
        )

    def obter_caminho_icone(self, pasta_assets: Path) -> Path:
        caminho = pasta_assets / self.obter_nome_icone()

        if caminho.is_file():
            return caminho

        return pasta_assets / self.ICONE_PADRAO
