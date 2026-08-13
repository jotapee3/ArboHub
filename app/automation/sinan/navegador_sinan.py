from __future__ import annotations

import re
from time import monotonic
from typing import Callable, Iterable

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Locator,
    Page,
    Playwright,
    sync_playwright
)

from app.core.seguranca_urls import (
    url_https_corresponde_dominio,
)
from app.services.configuracoes_service import (
    ConfiguracoesService
)
from app.services.credenciais_service import (
    CredenciaisService,
    CredencialSinan
)


class NavegadorSinan:

    URL_LOGIN = (
        "https://sinan.saude.gov.br/"
        "sinan/login/login.jsf"
    )
    DOMINIO_OFICIAL = "sinan.saude.gov.br"
    TEMPO_LOGIN_AUTOMATICO_SEGUNDOS = 20

    def __init__(
        self,
        permitir_downloads: bool = False,
        usar_login_automatico: bool = False
    ):
        self.permitir_downloads = bool(
            permitir_downloads
        )
        self.usar_login_automatico = bool(
            usar_login_automatico
        )

        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.contexto: BrowserContext | None = None
        self.pagina: Page | None = None

        self.login_automatico_ativado = False
        self.login_automatico_tentado = False
        self.login_automatico_concluido = False
        self.login_automatico_falhou = False
        self.mensagem_login_automatico = ""

    def abrir(self) -> Page:
        """
        Abre o Chromium em modo visível e acessa o SINAN.

        Nenhum estado de autenticação, screenshot, vídeo ou
        rastreamento é salvo.

        Quando o login automático estiver ativado, a credencial é
        lida do Gerenciador de Credenciais do Windows somente durante
        esta tentativa. Em caso de falha, a página permanece aberta
        para login manual.

        Downloads permanecem bloqueados por padrão. Eles só são
        habilitados quando o fluxo de exportação instancia:

        NavegadorSinan(
            permitir_downloads=True,
            usar_login_automatico=True
        )
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

        if not self._pagina_oficial_do_sinan():
            self.fechar()
            raise RuntimeError(
                "O navegador não abriu o endereço HTTPS oficial "
                "do SINAN. A autenticação foi interrompida."
            )

        if self.usar_login_automatico:
            self._tentar_login_automatico_configurado()

        return self.pagina

    def aguardar_login_manual(
        self,
        tempo_limite_segundos: int = 600,
        cancelado: Callable[[], bool] | None = None
    ) -> bool:
        """
        Aguarda a autenticação quando ela não foi concluída
        automaticamente.

        O método verifica somente a URL e a existência do menu
        principal. Não lê registros de pacientes.

        O callback opcional ``cancelado`` permite que a interface
        interrompa a espera pelo login de forma responsiva.
        """

        if self.pagina is None:
            raise RuntimeError(
                "O navegador ainda não foi aberto."
            )

        if self.login_foi_concluido():
            return True

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

    def obter_mensagem_espera_login(self) -> str:
        if self.login_automatico_concluido:
            return (
                "Login automático concluído com segurança."
            )

        if self.login_automatico_ativado:
            if self.mensagem_login_automatico:
                return (
                    self.mensagem_login_automatico
                    + " Continue o login manualmente no navegador."
                )

            return (
                "O login automático está ativado. Caso a autenticação "
                "não seja concluída, continue manualmente no navegador."
            )

        return "Aguardando o login manual no SINAN."

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

    # ------------------------------------------------------------------
    # Login automático seguro
    # ------------------------------------------------------------------

    def _tentar_login_automatico_configurado(self) -> None:
        if self.pagina is None:
            return

        try:
            configuracoes = (
                ConfiguracoesService()
                .carregar()
            )
            self.login_automatico_ativado = bool(
                configuracoes.get(
                    "sinan",
                    {}
                ).get(
                    "login_automatico",
                    False
                )
            )
        except Exception:
            self.login_automatico_ativado = False
            return

        if not self.login_automatico_ativado:
            return

        self.login_automatico_tentado = True
        credencial: CredencialSinan | None = None

        try:
            if not self._pagina_oficial_do_sinan():
                raise RuntimeError(
                    "A página aberta não corresponde ao domínio "
                    "oficial do SINAN."
                )

            credencial = CredenciaisService().obter()

            if credencial is None:
                raise RuntimeError(
                    "Nenhuma credencial do SINAN foi encontrada "
                    "no Windows."
                )

            self.login_automatico_concluido = (
                self._executar_login_automatico(
                    credencial
                )
            )

            if self.login_automatico_concluido:
                self.mensagem_login_automatico = (
                    "Login automático concluído."
                )
                return

            raise RuntimeError(
                "O SINAN não confirmou o login automático."
            )

        except Exception as erro:
            self.login_automatico_falhou = True
            self.login_automatico_concluido = False
            self.mensagem_login_automatico = str(
                erro
            ).strip() or (
                "O login automático não foi concluído."
            )
            self._preparar_fallback_manual()

        finally:
            credencial = None

    def _executar_login_automatico(
        self,
        credencial: CredencialSinan
    ) -> bool:
        if self.pagina is None:
            return False

        campo_senha = self._primeiro_visivel(
            (
                self.pagina.get_by_label(
                    re.compile(
                        r"senha",
                        re.IGNORECASE
                    )
                ),
                self.pagina.locator(
                    'input[type="password"]'
                )
            )
        )

        if campo_senha is None:
            raise RuntimeError(
                "O campo de senha do SINAN não foi localizado."
            )

        campo_usuario = self._primeiro_visivel(
            (
                self.pagina.get_by_label(
                    re.compile(
                        r"usu[aá]rio|login",
                        re.IGNORECASE
                    )
                ),
                self.pagina.locator(
                    'input[name*="usuario" i]'
                ),
                self.pagina.locator(
                    'input[id*="usuario" i]'
                ),
                self.pagina.locator(
                    'input[name*="login" i]'
                ),
                self.pagina.locator(
                    'input[id*="login" i]'
                ),
                self.pagina.locator(
                    'input[type="text"]'
                )
            )
        )

        if campo_usuario is None:
            raise RuntimeError(
                "O campo de usuário do SINAN não foi localizado."
            )

        campo_usuario.fill(
            credencial.usuario,
            timeout=10_000
        )
        campo_senha.fill(
            credencial.senha,
            timeout=10_000
        )

        self._enviar_formulario_login(
            campo_senha
        )

        limite = (
            monotonic()
            + self.TEMPO_LOGIN_AUTOMATICO_SEGUNDOS
        )

        while monotonic() < limite:
            if self.pagina.is_closed():
                return False

            if self.login_foi_concluido():
                return True

            self.pagina.wait_for_timeout(250)

        return False

    def _enviar_formulario_login(
        self,
        campo_senha: Locator
    ) -> None:
        if self.pagina is None:
            return

        candidatos: list[Locator] = []

        try:
            candidatos.append(
                self.pagina.get_by_role(
                    "button",
                    name=re.compile(
                        r"entrar|acessar|login",
                        re.IGNORECASE
                    )
                )
            )
        except Exception:
            pass

        try:
            formulario = campo_senha.locator(
                "xpath=ancestor::form[1]"
            )

            if formulario.count() > 0:
                candidatos.append(
                    formulario.locator(
                        'button[type="submit"], '
                        'input[type="submit"], '
                        'input[type="image"]'
                    )
                )
        except Exception:
            pass

        for candidato in candidatos:
            elemento = self._primeiro_visivel(
                (candidato,)
            )

            if elemento is None:
                continue

            try:
                elemento.click(
                    timeout=5_000
                )
                return
            except Exception:
                continue

        campo_senha.press(
            "Enter",
            timeout=5_000
        )

    def _primeiro_visivel(
        self,
        localizadores: Iterable[Locator]
    ) -> Locator | None:
        for localizador in localizadores:
            try:
                quantidade = localizador.count()
            except Exception:
                continue

            for indice in range(quantidade):
                elemento = localizador.nth(
                    indice
                )

                try:
                    if (
                        elemento.is_visible()
                        and elemento.is_enabled()
                    ):
                        return elemento
                except Exception:
                    continue

        return None

    def _pagina_oficial_do_sinan(self) -> bool:
        if self.pagina is None:
            return False

        return url_https_corresponde_dominio(
            self.pagina.url,
            self.DOMINIO_OFICIAL,
        )

    def _preparar_fallback_manual(self) -> None:
        if self.pagina is None or self.pagina.is_closed():
            return

        try:
            campos_senha = self.pagina.locator(
                'input[type="password"]'
            )

            for indice in range(
                campos_senha.count()
            ):
                campo = campos_senha.nth(
                    indice
                )

                if campo.is_visible():
                    campo.fill("")
                    campo.focus()
                    break
        except Exception:
            pass
