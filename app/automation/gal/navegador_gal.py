from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic
from typing import Callable, Iterator
from urllib.parse import urlparse

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Frame,
    Page,
    Playwright,
    sync_playwright
)


class NavegadorGal:
    """Abre o GAL sem persistir sessao, credenciais ou rastreamento."""

    URL_LOGIN = "https://gal.riograndedosul.sus.gov.br/login/"
    DOMINIO_OFICIAL = "gal.riograndedosul.sus.gov.br"

    MARCADORES_AREA_AUTENTICADA = (
        "Biologia Medica",
        "Biologia Médica",
        "Relatorios",
        "Relatórios"
    )

    def __init__(self, permitir_downloads: bool = True):
        self.permitir_downloads = bool(permitir_downloads)

        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.contexto: BrowserContext | None = None
        self.pagina: Page | None = None
        self._pasta_downloads_temporaria: TemporaryDirectory | None = None

    @property
    def pasta_downloads(self) -> Path | None:
        """Pasta privada em que o Chromium grava downloads do GAL."""

        if self._pasta_downloads_temporaria is None:
            return None

        return Path(self._pasta_downloads_temporaria.name)

    def abrir(self) -> Page:
        """
        Abre o Chromium visivel no endereco oficial do GAL.

        O portal utiliza um certificado que pode gerar o aviso de
        conexao nao particular. O contexto ignora somente esse erro
        de certificado; o dominio oficial continua sendo verificado.
        Login e CAPTCHA permanecem obrigatoriamente manuais.
        """

        if self.pagina is not None and not self.pagina.is_closed():
            return self.pagina

        try:
            if self.permitir_downloads:
                self._pasta_downloads_temporaria = TemporaryDirectory(
                    prefix="arbohub_gal_navegador_"
                )

            self.playwright = sync_playwright().start()
            parametros_navegador: dict[str, object] = {
                "headless": False
            }

            if self.pasta_downloads is not None:
                parametros_navegador["downloads_path"] = str(
                    self.pasta_downloads
                )

            self.browser = self.playwright.chromium.launch(
                **parametros_navegador
            )
            self.contexto = self.browser.new_context(
                accept_downloads=self.permitir_downloads,
                ignore_https_errors=True,
                viewport={
                    "width": 1366,
                    "height": 850
                }
            )
            self.pagina = self.contexto.new_page()
            self.pagina.goto(
                self.URL_LOGIN,
                wait_until="domcontentloaded",
                timeout=60_000
            )
        except Exception:
            self.fechar()
            raise

        if not self._pagina_em_dominio_oficial(self.pagina):
            raise RuntimeError(
                "O navegador nao abriu o dominio oficial do GAL."
            )

        return self.pagina

    def paginas_ativas(self) -> tuple[Page, ...]:
        if self.contexto is None:
            return ()

        return tuple(
            pagina
            for pagina in self.contexto.pages
            if not pagina.is_closed()
        )

    def quadros_ativos(self) -> Iterator[tuple[Page, Page | Frame]]:
        """Percorre paginas e frames do portal antigo do GAL."""

        for pagina in reversed(self.paginas_ativas()):
            yield pagina, pagina

            for quadro in reversed(pagina.frames):
                if quadro is pagina.main_frame:
                    continue

                yield pagina, quadro

    def login_foi_concluido(self) -> bool:
        """Detecta somente a area autenticada, sem ler registros."""

        for pagina, quadro in self.quadros_ativos():
            if not self._pagina_em_dominio_oficial(pagina):
                continue

            for marcador in self.MARCADORES_AREA_AUTENTICADA:
                try:
                    if quadro.get_by_text(
                        marcador,
                        exact=True
                    ).count() > 0:
                        return True
                except Exception:
                    continue

        for pagina in self.paginas_ativas():
            if not self._pagina_em_dominio_oficial(pagina):
                continue

            caminho = urlparse(pagina.url).path.casefold()

            if caminho and "login" not in caminho:
                return True

        return False

    def aguardar_login_manual(
        self,
        tempo_limite_segundos: int = 900,
        cancelado: Callable[[], bool] | None = None
    ) -> bool:
        """Aguarda o usuario concluir login e CAPTCHA no GAL."""

        limite = monotonic() + tempo_limite_segundos

        while monotonic() < limite:
            if cancelado is not None and cancelado():
                raise RuntimeError(
                    "A espera pelo login do GAL foi cancelada."
                )

            if not self.paginas_ativas():
                raise RuntimeError(
                    "A janela do GAL foi fechada antes do login."
                )

            if self.login_foi_concluido():
                return True

            pagina = self.paginas_ativas()[-1]
            pagina.wait_for_timeout(500)

        raise TimeoutError(
            "O tempo para realizar login e CAPTCHA no GAL terminou."
        )

    def fechar(self):
        if self.contexto is not None:
            try:
                self.contexto.close()
            except Exception:
                pass

        if self.browser is not None:
            try:
                self.browser.close()
            except Exception:
                pass

        if self.playwright is not None:
            try:
                self.playwright.stop()
            except Exception:
                pass

        if self._pasta_downloads_temporaria is not None:
            try:
                self._pasta_downloads_temporaria.cleanup()
            except Exception:
                pass

        self.pagina = None
        self.contexto = None
        self.browser = None
        self.playwright = None
        self._pasta_downloads_temporaria = None

    def _pagina_em_dominio_oficial(self, pagina: Page) -> bool:
        try:
            dominio = urlparse(pagina.url).hostname
        except Exception:
            return False

        return dominio == self.DOMINIO_OFICIAL
