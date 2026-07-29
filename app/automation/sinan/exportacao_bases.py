from __future__ import annotations

from datetime import date
from time import monotonic

from playwright.sync_api import Frame, Locator, Page

from app.automation.sinan.verificacao_obitos import (
    VerificacaoObitos
)


class ExportacaoBasesDbf(VerificacaoObitos):
    """
    Prepara a tela de exportação de bases do SINAN em DBF.

    Primeira etapa validada:
    - Exportação;
    - Solicitar Exportação de Base de Dados em DBF;
    - Período de Notificação = Data;
    - Data Inicial = 01/01 do ano atual;
    - Data Final = data atual;
    - Notificação ou Residência;
    - alcança o checkbox
      Exportar dados de identificação do paciente.

    Nesta etapa:
    - marca o checkbox de identificação do paciente;
    - não clica em Solicitar;
    - não altera o Agravo;
    - não lê dados de pacientes.
    """

    TEXTO_MENU_EXPORTACAO = "Exportação"
    TEXTO_SOLICITAR_DBF = (
        "Solicitar Exportação de Base de Dados em DBF"
    )
    TEXTO_PERIODO_DATA = "Data"
    TEXTO_LOCALIZACAO = "Notificação ou Residência"
    TEXTO_CHECKPOINT_IDENTIFICACAO = (
        "Exportar dados de identificação do paciente"
    )

    TEMPO_ABRIR_EXPORTACAO_SEGUNDOS = 120
    TEMPO_LOCALIZAR_CHECKPOINT_SEGUNDOS = 30
    TENTATIVAS_ESTABILIZAR_FORMULARIO = 4

    def __init__(self, pagina: Page):
        super().__init__(pagina)

        self._data_inicial_exportacao: str | None = None
        self._data_final_exportacao: str | None = None

    # ------------------------------------------------------------------
    # Fluxo público
    # ------------------------------------------------------------------

    def abrir_solicitacao_exportacao_dbf(self):
        """
        Abre:

        Exportação
        → Solicitar Exportação de Base de Dados em DBF
        """

        if self._formulario_exportacao_esta_aberto():
            return

        limite = (
            monotonic()
            + self.TEMPO_ABRIR_EXPORTACAO_SEGUNDOS
        )
        ultima_falha: Exception | None = None

        while monotonic() < limite:
            self._garantir_pagina_aberta()

            try:
                self._abrir_menu_exportacao()

                item = self._aguardar_texto_visivel(
                    texto=self.TEXTO_SOLICITAR_DBF,
                    tempo_limite_segundos=8,
                    exato=False
                )

                self._clicar_elemento_resiliente(
                    elemento=item,
                    descricao=self.TEXTO_SOLICITAR_DBF
                )

                self._aguardar_formulario_exportacao()
                return

            except Exception as erro:
                ultima_falha = erro
                self.pagina.wait_for_timeout(300)

        detalhe = (
            f" Última tentativa: {ultima_falha}"
            if ultima_falha
            else ""
        )

        raise RuntimeError(
            "Não foi possível abrir Exportação → "
            "Solicitar Exportação de Base de Dados em DBF "
            f"após {self.TEMPO_ABRIR_EXPORTACAO_SEGUNDOS} "
            f"segundos.{detalhe}"
        )

    def preparar_primeira_exportacao(
        self,
        data_referencia: date | None = None
    ) -> dict[str, str | bool]:
        """
        Preenche o formulário até o checkpoint solicitado.

        "Exportar dados de identificação do paciente" é um
        checkbox e deve permanecer marcado.

        A automação ainda para antes de clicar em Solicitar.
        """

        self._garantir_formulario_exportacao()

        periodo_datas = (
            self.preencher_periodo_e_datas_exportacao(
                data_referencia=data_referencia
            )
        )

        localizacao = (
            self.preencher_localizacao_exportacao()
        )

        checkpoint = (
            self.marcar_checkpoint_identificacao_paciente()
        )

        # Uma resposta AJAX tardia pode reconstruir as datas,
        # a localização ou o próprio checkbox. A estabilização
        # reaplica somente o que tiver sido alterado.
        self._estabilizar_campos_primeira_exportacao(
            data_referencia=data_referencia
        )

        checkpoint = (
            self.marcar_checkpoint_identificacao_paciente()
        )

        return {
            "periodo": self.TEXTO_PERIODO_DATA,
            "data_inicial": periodo_datas["data_inicial"],
            "data_final": periodo_datas["data_final"],
            "localizacao": localizacao,
            "checkpoint": (
                self.TEXTO_CHECKPOINT_IDENTIFICACAO
            ),
            "checkpoint_encontrado": bool(
                checkpoint["encontrado"]
            ),
            "checkpoint_marcado": bool(
                checkpoint["marcado"]
            ),
            "agravo_alterado": False,
            "solicitar_acionado": False,
            "dados_de_pacientes_lidos": False
        }

    def preencher_periodo_e_datas_exportacao(
        self,
        data_referencia: date | None = None
    ) -> dict[str, str]:
        """
        Configura:

        Período de Notificação = Data
        Data Inicial = 01/01 do ano atual
        Data Final = data atual ou data de referência
        """

        data_referencia = data_referencia or date.today()

        self._data_inicial_exportacao = date(
            year=data_referencia.year,
            month=1,
            day=1
        ).strftime("%d/%m/%Y")

        self._data_final_exportacao = (
            data_referencia.strftime("%d/%m/%Y")
        )

        for _ in range(
            self.TENTATIVAS_ESTABILIZAR_FORMULARIO
        ):
            contexto = self._localizar_contexto_exportacao()

            if not self._periodo_data_exportacao_esta_selecionado():
                marcador_ajax = self._marcar_estado_ajax()

                self._selecionar_periodo_data_exportacao(
                    contexto
                )

                self._aguardar_ajax_apos_acao(
                    marcador_ajax=marcador_ajax,
                    descricao="Período de Notificação = Data"
                )

            contexto = self._localizar_contexto_exportacao()

            campo_inicial = self._localizar_input_por_rotulo(
                contexto=contexto,
                rotulo="Data Inicial",
                indice_fallback=0
            )

            if (
                campo_inicial.input_value().strip()
                != self._data_inicial_exportacao
            ):
                self._preencher_input(
                    campo=campo_inicial,
                    valor=self._data_inicial_exportacao,
                    nome_campo="Data Inicial"
                )

            contexto = self._localizar_contexto_exportacao()

            campo_final = self._localizar_input_por_rotulo(
                contexto=contexto,
                rotulo="Data Final",
                indice_fallback=1
            )

            if (
                campo_final.input_value().strip()
                != self._data_final_exportacao
            ):
                self._preencher_input(
                    campo=campo_final,
                    valor=self._data_final_exportacao,
                    nome_campo="Data Final"
                )

            if self._periodo_e_datas_exportacao_estao_corretos():
                return {
                    "data_inicial":
                        self._data_inicial_exportacao,
                    "data_final":
                        self._data_final_exportacao
                }

            self.pagina.wait_for_timeout(100)

        raise RuntimeError(
            "Não foi possível manter Período = Data, "
            "Data Inicial e Data Final na tela de exportação."
        )

    def preencher_localizacao_exportacao(self) -> str:
        """
        Seleciona exatamente:

        Notificação ou Residência
        """

        if self._localizacao_exportacao_esta_selecionada():
            return self.TEXTO_LOCALIZACAO

        contexto = self._localizar_contexto_exportacao()
        marcador_ajax = self._marcar_estado_ajax()

        selecionou = self._selecionar_opcao_em_qualquer_select(
            contexto=contexto,
            texto_opcao=self.TEXTO_LOCALIZACAO,
            exato=True
        )

        if not selecionou:
            raise RuntimeError(
                "Não foi possível selecionar "
                "'Notificação ou Residência' "
                "na tela de exportação."
            )

        self._aguardar_ajax_apos_acao(
            marcador_ajax=marcador_ajax,
            descricao=self.TEXTO_LOCALIZACAO
        )

        self._confirmar_rapido(
            condicao=(
                self._localizacao_exportacao_esta_selecionada
            ),
            descricao=self.TEXTO_LOCALIZACAO
        )

        return self.TEXTO_LOCALIZACAO

    def marcar_checkpoint_identificacao_paciente(
        self
    ) -> dict[str, bool]:
        """
        Localiza e marca o checkbox:

        Exportar dados de identificação do paciente

        O método é idempotente: se o checkbox já estiver marcado,
        não clica novamente.
        """

        limite = (
            monotonic()
            + self.TEMPO_LOCALIZAR_CHECKPOINT_SEGUNDOS
        )

        while monotonic() < limite:
            self._garantir_pagina_aberta()

            for contexto in self._obter_contextos():
                checkbox = self._procurar_checkbox_identificacao(
                    contexto
                )

                if checkbox is None:
                    continue

                try:
                    checkbox.scroll_into_view_if_needed()
                except Exception:
                    pass

                try:
                    if not checkbox.is_checked():
                        marcador_ajax = self._marcar_estado_ajax()

                        try:
                            checkbox.check(
                                timeout=6_000
                            )
                        except Exception:
                            checkbox.check(
                                timeout=6_000,
                                force=True
                            )

                        self._aguardar_ajax_apos_acao(
                            marcador_ajax=marcador_ajax,
                            descricao=(
                                "Exportar dados de identificação "
                                "do paciente"
                            )
                        )

                    if checkbox.is_checked():
                        return {
                            "encontrado": True,
                            "marcado": True
                        }

                except Exception:
                    # O DOM pode ter sido reconstruído depois do clique.
                    # O próximo ciclo procura o checkbox atual.
                    pass

            self.pagina.wait_for_timeout(
                self.INTERVALO_VERIFICACAO_MS
            )

        raise RuntimeError(
            "O checkbox 'Exportar dados de identificação "
            "do paciente' foi localizado, mas não permaneceu "
            "marcado."
        )

    def _procurar_checkbox_identificacao(
        self,
        contexto: Page | Frame
    ) -> Locator | None:
        """
        Procura o checkbox pelo rótulo e por relações de DOM.

        A tela do SINAN pode associar o texto ao input por
        ``label[for]`` ou manter ambos dentro do mesmo bloco.
        """

        texto = self.TEXTO_CHECKPOINT_IDENTIFICACAO

        try:
            controles = contexto.get_by_label(
                texto,
                exact=False
            )

            for indice in range(controles.count()):
                controle = controles.nth(indice)

                try:
                    if (
                        controle.is_visible()
                        and self._tag_name(controle) == "input"
                        and (
                            controle.get_attribute("type")
                            or ""
                        ).casefold() == "checkbox"
                    ):
                        return controle

                except Exception:
                    continue

        except Exception:
            pass

        try:
            labels = contexto.locator("label").filter(
                has_text=texto
            )

            for indice in range(labels.count()):
                label = labels.nth(indice)

                try:
                    if not label.is_visible():
                        continue

                    internos = label.locator(
                        "input[type='checkbox']"
                    )

                    for indice_input in range(
                        internos.count()
                    ):
                        checkbox = internos.nth(
                            indice_input
                        )

                        if checkbox.is_visible():
                            return checkbox

                    identificador = label.get_attribute(
                        "for"
                    )

                    if identificador:
                        associado = contexto.locator(
                            f"#{identificador}"
                        )

                        if (
                            associado.count() > 0
                            and associado.first.is_visible()
                            and (
                                associado.first.get_attribute(
                                    "type"
                                )
                                or ""
                            ).casefold() == "checkbox"
                        ):
                            return associado.first

                except Exception:
                    continue

        except Exception:
            pass

        try:
            textos = contexto.get_by_text(
                texto,
                exact=False
            )

            for indice in range(textos.count()):
                elemento_texto = textos.nth(indice)

                try:
                    if not elemento_texto.is_visible():
                        continue

                    bloco = elemento_texto.locator(
                        "xpath=ancestor::*"
                        "[self::td or self::div or self::span]"
                        "[1]"
                    )

                    checkboxes = bloco.locator(
                        "input[type='checkbox']"
                    )

                    for indice_checkbox in range(
                        checkboxes.count()
                    ):
                        checkbox = checkboxes.nth(
                            indice_checkbox
                        )

                        if checkbox.is_visible():
                            return checkbox

                    anterior = elemento_texto.locator(
                        "xpath=preceding::input"
                        "[@type='checkbox'][1]"
                    )

                    if (
                        anterior.count() > 0
                        and anterior.first.is_visible()
                    ):
                        return anterior.first

                except Exception:
                    continue

        except Exception:
            pass

        return None

    def _estabilizar_campos_primeira_exportacao(
        self,
        data_referencia: date | None
    ):
        """
        Reaplica Período, datas, localização e checkbox caso uma
        resposta AJAX tardia tenha reconstruído o formulário.
        """

        for _ in range(
            self.TENTATIVAS_ESTABILIZAR_FORMULARIO
        ):
            tudo_correto = True

            if not self._periodo_e_datas_exportacao_estao_corretos():
                self.preencher_periodo_e_datas_exportacao(
                    data_referencia=data_referencia
                )
                tudo_correto = False

            if not self._localizacao_exportacao_esta_selecionada():
                self.preencher_localizacao_exportacao()
                tudo_correto = False

            try:
                checkpoint = (
                    self.marcar_checkpoint_identificacao_paciente()
                )

                if not checkpoint["marcado"]:
                    tudo_correto = False

            except RuntimeError:
                tudo_correto = False

            if (
                tudo_correto
                and self._periodo_e_datas_exportacao_estao_corretos()
                and self._localizacao_exportacao_esta_selecionada()
            ):
                return

            self.pagina.wait_for_timeout(120)

        raise RuntimeError(
            "O SINAN alterou repetidamente algum campo "
            "da primeira etapa da exportação."
        )

    def _selecionar_periodo_data_exportacao(
        self,
        contexto: Page | Frame
    ):
        """
        Prioriza o select associado a Período de Notificação.
        Usa busca global apenas como fallback.
        """

        try:
            controles = contexto.get_by_label(
                "Período de Notificação",
                exact=False
            )

            for indice in range(controles.count()):
                controle = controles.nth(indice)

                if (
                    controle.is_visible()
                    and self._tag_name(controle) == "select"
                ):
                    textos = controle.locator(
                        "option"
                    ).all_text_contents()

                    if self._select_contem_opcao(
                        textos=textos,
                        alvo=self.TEXTO_PERIODO_DATA,
                        exato=True
                    ):
                        self._selecionar_opcao_select(
                            select=controle,
                            textos=textos,
                            alvo=self.TEXTO_PERIODO_DATA,
                            exato=True
                        )
                        return

        except Exception:
            pass

        if self._selecionar_opcao_em_qualquer_select(
            contexto=contexto,
            texto_opcao=self.TEXTO_PERIODO_DATA,
            exato=True
        ):
            return

        raise RuntimeError(
            "Não foi possível selecionar 'Data' no campo "
            "'Período de Notificação'."
        )

    def _periodo_data_exportacao_esta_selecionado(
        self
    ) -> bool:
        try:
            contexto = self._localizar_contexto_exportacao()

            return self._select_tem_opcao_selecionada(
                contexto=contexto,
                texto_opcao=self.TEXTO_PERIODO_DATA,
                exato=True
            )

        except Exception:
            return False

    def _periodo_e_datas_exportacao_estao_corretos(
        self
    ) -> bool:
        if (
            self._data_inicial_exportacao is None
            or self._data_final_exportacao is None
        ):
            return False

        try:
            contexto = self._localizar_contexto_exportacao()

            if not self._periodo_data_exportacao_esta_selecionado():
                return False

            inicial = self._localizar_input_por_rotulo(
                contexto=contexto,
                rotulo="Data Inicial",
                indice_fallback=0
            ).input_value().strip()

            final = self._localizar_input_por_rotulo(
                contexto=contexto,
                rotulo="Data Final",
                indice_fallback=1
            ).input_value().strip()

            return (
                inicial == self._data_inicial_exportacao
                and final == self._data_final_exportacao
            )

        except Exception:
            return False

    def _localizacao_exportacao_esta_selecionada(
        self
    ) -> bool:
        try:
            contexto = self._localizar_contexto_exportacao()

            return self._select_tem_opcao_selecionada(
                contexto=contexto,
                texto_opcao=self.TEXTO_LOCALIZACAO,
                exato=True
            )

        except Exception:
            return False

    def _abrir_menu_exportacao(self):
        menu = self._aguardar_texto_visivel(
            texto=self.TEXTO_MENU_EXPORTACAO,
            tempo_limite_segundos=10,
            exato=True
        )

        try:
            menu.scroll_into_view_if_needed()
        except Exception:
            pass

        try:
            menu.hover(timeout=5_000)

            if self._esperar_ate(
                condicao=lambda: (
                    self._procurar_texto_visivel(
                        texto=self.TEXTO_SOLICITAR_DBF,
                        exato=False
                    )
                    is not None
                ),
                tempo_limite_segundos=1
            ):
                return

        except Exception:
            pass

        self._clicar_elemento_resiliente(
            elemento=menu,
            descricao=self.TEXTO_MENU_EXPORTACAO
        )

    def _aguardar_texto_visivel(
        self,
        texto: str,
        tempo_limite_segundos: float,
        exato: bool
    ) -> Locator:
        limite = monotonic() + tempo_limite_segundos

        while monotonic() < limite:
            self._garantir_pagina_aberta()

            elemento = self._procurar_texto_visivel(
                texto=texto,
                exato=exato
            )

            if elemento is not None:
                return elemento

            self.pagina.wait_for_timeout(
                self.INTERVALO_VERIFICACAO_MS
            )

        raise RuntimeError(
            f'Não foi possível localizar "{texto}" '
            f"após {tempo_limite_segundos} segundos."
        )

    def _procurar_texto_visivel(
        self,
        texto: str,
        exato: bool
    ) -> Locator | None:
        alvo = self._normalizar_texto(texto)

        for contexto in self._obter_contextos():
            localizadores = [
                contexto.get_by_role(
                    "link",
                    name=texto,
                    exact=exato
                ),
                contexto.get_by_text(
                    texto,
                    exact=exato
                )
            ]

            for localizador in localizadores:
                try:
                    quantidade = localizador.count()
                except Exception:
                    continue

                for indice in range(quantidade):
                    elemento = localizador.nth(indice)

                    try:
                        if not elemento.is_visible():
                            continue

                        if exato:
                            return elemento

                        texto_atual = self._normalizar_texto(
                            elemento.inner_text()
                        )

                        if alvo in texto_atual:
                            return elemento

                    except Exception:
                        continue

        return None

    # ------------------------------------------------------------------
    # Formulário
    # ------------------------------------------------------------------

    def _aguardar_formulario_exportacao(self):
        limite = (
            monotonic()
            + self.TEMPO_FORMULARIO_SEGUNDOS
        )

        while monotonic() < limite:
            self._garantir_pagina_aberta()

            if self._formulario_exportacao_esta_aberto():
                return

            self.pagina.wait_for_timeout(
                self.INTERVALO_VERIFICACAO_MS
            )

        raise RuntimeError(
            "A tela de solicitação de exportação em DBF "
            "não foi confirmada após "
            f"{self.TEMPO_FORMULARIO_SEGUNDOS} segundos."
        )

    def _garantir_formulario_exportacao(self):
        if not self._formulario_exportacao_esta_aberto():
            raise RuntimeError(
                "A tela de solicitação de exportação em DBF "
                "ainda não está aberta."
            )

    def _formulario_exportacao_esta_aberto(self) -> bool:
        try:
            self._localizar_contexto_exportacao()
            return True

        except RuntimeError:
            return False

    def _localizar_contexto_exportacao(
        self
    ) -> Page | Frame:
        textos_esperados = [
            "Período de Notificação",
            "Data Inicial",
            "Data Final",
            "Notificação ou Residência",
            "Pular para Checkpoint"
        ]

        maior_quantidade = 0

        for contexto in self._obter_contextos():
            encontrados = sum(
                self._texto_existe_no_contexto(
                    contexto,
                    texto
                )
                for texto in textos_esperados
            )

            maior_quantidade = max(
                maior_quantidade,
                encontrados
            )

            if encontrados >= 3:
                return contexto

        raise RuntimeError(
            "O formulário de solicitação de exportação em DBF "
            "não foi localizado. "
            f"Maior quantidade de campos reconhecidos: "
            f"{maior_quantidade}."
        )