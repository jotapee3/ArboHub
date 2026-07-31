from __future__ import annotations

from time import monotonic
from typing import Callable

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    sync_playwright
)


class NavegadorSinan:

    URL_LOGIN = (
        "https://sinan.saude.gov.br/"
        "sinan/login/login.jsf"
    )

    def __init__(
        self,
        permitir_downloads: bool = False
    ):
        self.permitir_downloads = bool(
            permitir_downloads
        )

        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.contexto: BrowserContext | None = None
        self.pagina: Page | None = None

    def abrir(self) -> Page:
        """
        Abre o Chromium em modo visível e acessa o SINAN.

        Nenhum estado de autenticação, screenshot, vídeo ou
        rastreamento é salvo.

        Downloads permanecem bloqueados por padrão. Eles só são
        habilitados quando o fluxo de exportação instancia:

        NavegadorSinan(permitir_downloads=True)
        """

        if self.pagina is not None:
            return self.pagina

        self.playwright = sync_playwright().start()

        self.browser = self.playwright.chromium.launch(
            headless=False
        )

        self.contexto = self.browser.new_context(
            accept_downloads=self.permitir_downloads,
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

        return self.pagina

    def aguardar_login_manual(
        self,
        tempo_limite_segundos: int = 600,
        cancelado: Callable[[], bool] | None = None
    ) -> bool:
        """
        Aguarda o usuário realizar o login manualmente.

        O método verifica somente a URL e a existência do menu
        principal. Não lê usuário, senha ou registros de pacientes.

        O callback opcional ``cancelado`` permite que a interface
        interrompa a espera pelo login de forma responsiva.
        """

        if self.pagina is None:
            raise RuntimeError(
                "O navegador ainda não foi aberto."
            )

        limite = (
            monotonic()
            + tempo_limite_segundos
        )

        while monotonic() < limite:
            if (
                cancelado is not None
                and cancelado()
            ):
                raise RuntimeError(
                    "A espera pelo login foi cancelada."
                )

            if self.pagina.is_closed():
                raise RuntimeError(
                    "A janela do navegador foi fechada."
                )

            if self.login_foi_concluido():
                return True

            self.pagina.wait_for_timeout(250)

        raise TimeoutError(
            "O tempo para realizar o login foi encerrado."
        )

    def login_foi_concluido(self) -> bool:
        if self.pagina is None:
            return False

        url_atual = self.pagina.url.lower()

        if "/secured/" in url_atual:
            return True

        if (
            "/login/" not in url_atual
            and "home.jsf" in url_atual
        ):
            return True

        try:
            menu_consulta = self.pagina.get_by_text(
                "Consulta",
                exact=True
            )

            return menu_consulta.count() > 0

        except Exception:
            return False

    def fechar(self):
        """
        Fecha o contexto temporário, o navegador e o Playwright.
        """

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

        self.pagina = None
        self.contexto = None
        self.browser = None
        self.playwright = None