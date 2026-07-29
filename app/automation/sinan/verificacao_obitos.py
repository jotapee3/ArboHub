from __future__ import annotations

import unicodedata
from datetime import date
from time import monotonic

from playwright.sync_api import Frame, Locator, Page


class VerificacaoObitos:
    """
    Automatiza o preenchimento seguro da consulta de óbitos.

    Nesta etapa, a classe:
    - abre Consulta → Notificação Individual;
    - preenche o período e as datas;
    - seleciona Dengue ou Chikungunya;
    - seleciona Notificação ou Residência;
    - seleciona Evolução;
    - seleciona 2 - Óbito por Agravo.

    Também pode adicionar o critério à lista.

    Ainda não clica em Pesquisar.
    """

    # Limites máximos. Em conexão rápida, o programa avança
    # assim que o estado correto é detectado.
    TEMPO_MENU_SEGUNDOS = 120
    TEMPO_FORMULARIO_SEGUNDOS = 120
    TEMPO_PROCESSAMENTO_SEGUNDOS = 90

    # Confirmações curtas: eliminam as antigas pausas de 15/30 s.
    TEMPO_CONFIRMACAO_RAPIDA_SEGUNDOS = 3
    TEMPO_CARREGAR_CRITERIO_SEGUNDOS = 12

    # O popup é observado somente após Agravo, Localização,
    # Campo e Critério. Quando não aparece, o custo máximo
    # é de 350 ms por campo.
    JANELA_DETECCAO_PROCESSAMENTO_MS = 350
    INTERVALO_VERIFICACAO_MS = 40
    ESTABILIDADE_APOS_PROCESSAMENTO_MS = 120

    def __init__(self, pagina: Page):
        self.pagina = pagina

        self._data_inicial_esperada: str | None = None
        self._data_final_esperada: str | None = None
        self._agravo_esperado: str | None = None
        self._localizacao_esperada = (
            "Notificação ou Residência"
        )

    # ------------------------------------------------------------------
    # Fluxo público
    # ------------------------------------------------------------------

    def abrir_notificacao_individual(self):
        """
        Acessa Consulta → Notificação Individual.

        Tolera submenu por hover, internet lenta, frames e
        atualizações parciais do SINAN.
        """

        if self._formulario_consulta_esta_aberto():
            return

        limite = monotonic() + self.TEMPO_MENU_SEGUNDOS
        ultima_falha: Exception | None = None

        while monotonic() < limite:
            self._garantir_pagina_aberta()

            try:
                self._abrir_menu_consulta()

                item = self._aguardar_elemento_visivel(
                    texto="Notificação Individual",
                    tempo_limite_segundos=5
                )

                self._clicar_elemento_resiliente(
                    elemento=item,
                    descricao="Notificação Individual"
                )

                self._aguardar_formulario_consulta()
                return

            except Exception as erro:
                ultima_falha = erro
                self.pagina.wait_for_timeout(250)

        detalhe = (
            f" Última tentativa: {ultima_falha}"
            if ultima_falha
            else ""
        )

        raise RuntimeError(
            "Não foi possível abrir "
            "Consulta → Notificação Individual "
            f"após {self.TEMPO_MENU_SEGUNDOS} segundos."
            f"{detalhe}"
        )

    def preencher_periodo_e_datas(
        self,
        data_referencia: date | None = None
    ) -> dict[str, str]:
        """
        Configura:

        Período de Notificação: Data
        Data Inicial: primeiro dia do ano atual
        Data Final: data de referência ou data atual
        """

        data_referencia = data_referencia or date.today()

        self._data_inicial_esperada = date(
            year=data_referencia.year,
            month=1,
            day=1
        ).strftime("%d/%m/%Y")

        self._data_final_esperada = (
            data_referencia.strftime("%d/%m/%Y")
        )

        self._garantir_periodo_e_datas()

        return {
            "data_inicial": self._data_inicial_esperada,
            "data_final": self._data_final_esperada
        }

    def preencher_agravo_e_residencia(
        self,
        agravo: str = "Dengue"
    ) -> dict[str, str]:
        """
        Seleciona e confirma, em sequência direta:

        Agravo: Dengue ou Chikungunya
        Localização: Notificação ou Residência
        """

        agravos_permitidos = {
            "dengue": "Dengue",
            "chikungunya": "Chikungunya",
            "chiku": "Chikungunya"
        }

        agravo_normalizado = self._normalizar_texto(
            agravo
        )

        if agravo_normalizado not in agravos_permitidos:
            raise ValueError(
                "Agravo inválido. Use Dengue ou Chikungunya."
            )

        self._agravo_esperado = agravos_permitidos[
            agravo_normalizado
        ]

        self._garantir_periodo_e_datas()

        # 1. Seleciona Agravo.
        if not self._agravo_esta_selecionado():
            contexto = self._localizar_contexto_formulario()

            self._selecionar_agravo_combo(
                contexto=contexto,
                nome_agravo=self._agravo_esperado
            )

        # Aguarda somente o popup real, caso apareça.
        self._sincronizar_processamento_relevante()

        # Confirma o Agravo em até 3 s, sem espera fixa.
        self._confirmar_rapido(
            condicao=self._agravo_esta_selecionado,
            descricao=f"Agravo {self._agravo_esperado}"
        )

        # 2. Seleciona Notificação ou Residência.
        contexto = self._localizar_contexto_formulario()

        if not self._localizacao_esta_selecionada():
            self._selecionar_notificacao_ou_residencia(
                contexto=contexto
            )

        self._sincronizar_processamento_relevante()

        self._confirmar_rapido(
            condicao=self._localizacao_esta_selecionada,
            descricao="Notificação ou Residência"
        )

        # Só restaura as datas se o AJAX realmente as apagou.
        if not self._periodo_e_datas_estao_corretos():
            self._garantir_periodo_e_datas()

        return {
            "agravo": self._agravo_esperado,
            "localizacao": self._localizacao_esperada
        }

    def preencher_criterio_obito(self) -> dict[str, str]:
        """
        Seleciona e confirma:

        Campo: Evolução
        Critério de Seleção: 2 - Óbito por Agravo
        """

        self._garantir_filtros_basicos_rapido()

        # O SINAN pode reconstruir o formulário após Evolução.
        # São permitidas duas tentativas curtas, não esperas longas.
        for _ in range(2):
            # 1. Campo = Evolução.
            if not self._evolucao_esta_selecionada():
                contexto = self._localizar_contexto_formulario()

                self._selecionar_campo_evolucao(
                    contexto=contexto
                )

            self._sincronizar_processamento_relevante()

            self._confirmar_rapido(
                condicao=self._evolucao_esta_selecionada,
                descricao="Campo Evolução"
            )

            # Restaura somente o que o AJAX tiver apagado.
            self._garantir_filtros_basicos_rapido()

            # Restaurar filtros pode reconstruir a área de critérios.
            if not self._evolucao_esta_selecionada():
                continue

            # 2. Aguarda a opção do critério realmente existir.
            self._aguardar_opcao_em_select(
                texto_opcao="2 - Óbito por Agravo",
                exato=True,
                tempo_limite_segundos=(
                    self.TEMPO_CARREGAR_CRITERIO_SEGUNDOS
                )
            )

            if not self._criterio_obito_esta_selecionado():
                contexto = self._localizar_contexto_formulario()

                self._selecionar_criterio_obito_por_agravo(
                    contexto=contexto
                )

            self._sincronizar_processamento_relevante()

            self._confirmar_rapido(
                condicao=self._criterio_obito_esta_selecionado,
                descricao="Critério 2 - Óbito por Agravo"
            )

            if self._estado_final_esta_correto():
                return {
                    "campo": "Evolução",
                    "criterio": "2 - Óbito por Agravo"
                }

        raise RuntimeError(
            "O SINAN não manteve todos os filtros "
            "corretos ao mesmo tempo."
        )


    def adicionar_criterio_obito(self) -> dict[str, int | str]:
        """
        Clica em Adicionar e confirma que o critério passou
        a existir na lista de critérios da consulta.

        Não clica em Pesquisar.
        """

        if not self._estado_final_esta_correto():
            raise RuntimeError(
                "Os filtros precisam estar corretamente "
                "preenchidos antes de clicar em Adicionar."
            )

        ocorrencias_antes = (
            self._contar_criterios_obito_registrados()
        )

        botao = self._aguardar_botao_adicionar_habilitado(
            tempo_limite_segundos=5
        )

        self._clicar_elemento_resiliente(
            elemento=botao,
            descricao="Adicionar"
        )

        # O botão pode disparar o popup AJAX do SINAN.
        self._sincronizar_processamento_relevante()

        ocorrencias_depois = (
            self._aguardar_criterio_obito_adicionado(
                ocorrencias_antes=ocorrencias_antes,
                tempo_limite_segundos=12
            )
        )

        return {
            "campo": "Evolução",
            "operador": "Igual",
            "criterio": "2 - Óbito por Agravo",
            "ocorrencias_antes": ocorrencias_antes,
            "ocorrencias_depois": ocorrencias_depois
        }

    # ------------------------------------------------------------------
    # Navegação
    # ------------------------------------------------------------------

    def _abrir_menu_consulta(self):
        elemento = self._aguardar_elemento_visivel(
            texto="Consulta",
            tempo_limite_segundos=10
        )

        try:
            elemento.scroll_into_view_if_needed()
        except Exception:
            pass

        try:
            elemento.hover(timeout=5_000)

            if self._esperar_ate(
                condicao=lambda: (
                    self._procurar_elemento_visivel(
                        "Notificação Individual"
                    )
                    is not None
                ),
                tempo_limite_segundos=0.8
            ):
                return

        except Exception:
            pass

        self._clicar_elemento_resiliente(
            elemento=elemento,
            descricao="Consulta"
        )

    def _aguardar_elemento_visivel(
        self,
        texto: str,
        tempo_limite_segundos: float
    ) -> Locator:
        limite = monotonic() + tempo_limite_segundos

        while monotonic() < limite:
            self._garantir_pagina_aberta()

            elemento = self._procurar_elemento_visivel(
                texto
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

    def _clicar_elemento_resiliente(
        self,
        elemento: Locator,
        descricao: str
    ):
        try:
            elemento.scroll_into_view_if_needed()
        except Exception:
            pass

        try:
            elemento.click(timeout=8_000)
            return

        except Exception:
            pass

        try:
            elemento.click(
                timeout=8_000,
                force=True
            )

        except Exception as erro:
            raise RuntimeError(
                f'Não foi possível clicar em "{descricao}".'
            ) from erro

    # ------------------------------------------------------------------
    # Período e datas
    # ------------------------------------------------------------------

    def _garantir_periodo_e_datas(self):
        if (
            self._data_inicial_esperada is None
            or self._data_final_esperada is None
        ):
            raise RuntimeError(
                "As datas esperadas ainda não foram definidas."
            )

        for _ in range(3):
            contexto = self._localizar_contexto_formulario()

            if not self._periodo_data_esta_selecionado():
                self._selecionar_periodo_data(
                    contexto
                )

            contexto = self._localizar_contexto_formulario()

            campo_inicial = self._localizar_input_por_rotulo(
                contexto=contexto,
                rotulo="Data Inicial",
                indice_fallback=0
            )

            if (
                campo_inicial.input_value().strip()
                != self._data_inicial_esperada
            ):
                self._preencher_input(
                    campo=campo_inicial,
                    valor=self._data_inicial_esperada,
                    nome_campo="Data Inicial"
                )

            contexto = self._localizar_contexto_formulario()

            campo_final = self._localizar_input_por_rotulo(
                contexto=contexto,
                rotulo="Data Final",
                indice_fallback=1
            )

            if (
                campo_final.input_value().strip()
                != self._data_final_esperada
            ):
                self._preencher_input(
                    campo=campo_final,
                    valor=self._data_final_esperada,
                    nome_campo="Data Final"
                )

            if self._periodo_e_datas_estao_corretos():
                return

            self.pagina.wait_for_timeout(40)

        raise RuntimeError(
            "O SINAN apagou ou alterou as datas repetidamente."
        )

    def _selecionar_periodo_data(
        self,
        contexto: Page | Frame
    ):
        if self._selecionar_opcao_em_qualquer_select(
            contexto=contexto,
            texto_opcao="Data",
            exato=True
        ):
            return

        raise RuntimeError(
            "Não foi possível localizar o campo "
            "'Período de Notificação'."
        )

    def _periodo_data_esta_selecionado(self) -> bool:
        try:
            contexto = self._localizar_contexto_formulario()

            return self._select_tem_opcao_selecionada(
                contexto=contexto,
                texto_opcao="Data",
                exato=True
            )

        except Exception:
            return False

    def _periodo_e_datas_estao_corretos(self) -> bool:
        if (
            self._data_inicial_esperada is None
            or self._data_final_esperada is None
        ):
            return False

        try:
            contexto = self._localizar_contexto_formulario()

            if not self._periodo_data_esta_selecionado():
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
                inicial == self._data_inicial_esperada
                and final == self._data_final_esperada
            )

        except Exception:
            return False

    # ------------------------------------------------------------------
    # Agravo
    # ------------------------------------------------------------------

    def _selecionar_agravo_combo(
        self,
        contexto: Page | Frame,
        nome_agravo: str
    ):
        campo, container = self._localizar_campo_agravo(
            contexto
        )

        campo.scroll_into_view_if_needed()

        if (
            container is not None
            and self._clicar_seta_combo(container)
        ):
            if self._esperar_ate(
                condicao=lambda: (
                    self._opcao_combo_esta_visivel(
                        nome_agravo
                    )
                ),
                tempo_limite_segundos=2
            ):
                if self._clicar_opcao_combo_visivel(
                    nome_agravo
                ):
                    return

        try:
            campo.click(timeout=6_000)
            campo.press("Control+A")
            campo.fill(nome_agravo)

        except Exception:
            campo.click(timeout=6_000)
            campo.press("Control+A")
            campo.type(
                nome_agravo,
                delay=40
            )

        if self._esperar_ate(
            condicao=lambda: (
                self._opcao_combo_esta_visivel(
                    nome_agravo
                )
            ),
            tempo_limite_segundos=2
        ):
            if self._clicar_opcao_combo_visivel(
                nome_agravo
            ):
                return

        campo.press("ArrowDown")
        campo.press("Enter")

    def _localizar_campo_agravo(
        self,
        contexto: Page | Frame
    ) -> tuple[Locator, Locator | None]:
        try:
            controles = contexto.get_by_label(
                "Agravo",
                exact=False
            )

            for indice in range(controles.count()):
                controle = controles.nth(indice)

                if (
                    controle.is_visible()
                    and self._tag_name(controle) == "input"
                ):
                    return (
                        controle,
                        self._container_proximo(controle)
                    )

        except Exception:
            pass

        candidatos = contexto.locator(
            "td, div"
        ).filter(
            has_text="Agravo"
        )

        for indice in range(candidatos.count()):
            candidato = candidatos.nth(indice)

            try:
                if not candidato.is_visible():
                    continue

                inputs = candidato.locator(
                    "input:not([type]), "
                    "input[type='text']"
                )

                for indice_input in range(inputs.count()):
                    campo = inputs.nth(indice_input)

                    if (
                        campo.is_visible()
                        and campo.is_enabled()
                    ):
                        return campo, candidato

            except Exception:
                continue

        inputs_visiveis = self._inputs_texto_visiveis(
            contexto
        )

        if len(inputs_visiveis) >= 3:
            campo = inputs_visiveis[2]

            return (
                campo,
                self._container_proximo(campo)
            )

        raise RuntimeError(
            "Não foi possível localizar o campo 'Agravo'."
        )

    def _agravo_esta_selecionado(self) -> bool:
        """
        Confirma o Agravo sem acionar esperas automáticas longas.

        O SINAN pode recriar o input durante o AJAX. Por isso,
        o valor é lido diretamente do DOM atual, aceitando textos
        como "Dengue" e "A90 - DENGUE".
        """

        if self._agravo_esperado is None:
            return False

        alvo = self._normalizar_texto(
            self._agravo_esperado
        )

        for contexto in self._obter_contextos():
            controles = contexto.locator(
                "input:not([type]), "
                "input[type='text'], "
                "input[readonly], "
                "input[disabled]"
            )

            try:
                quantidade = controles.count()
            except Exception:
                continue

            for indice in range(quantidade):
                controle = controles.nth(indice)

                try:
                    if not controle.is_visible():
                        continue

                    # evaluate lê a propriedade value diretamente,
                    # sem esperar até 30 segundos por um subelemento.
                    valor_atual = controle.evaluate(
                        "elemento => elemento.value || ''"
                    )

                    if alvo in self._normalizar_texto(
                        str(valor_atual)
                    ):
                        return True

                except Exception:
                    continue

        return False

    # ------------------------------------------------------------------
    # Localização, Evolução e Critério
    # ------------------------------------------------------------------

    def _selecionar_notificacao_ou_residencia(
        self,
        contexto: Page | Frame
    ):
        if self._selecionar_opcao_em_qualquer_select(
            contexto=contexto,
            texto_opcao=self._localizacao_esperada,
            exato=True
        ):
            return

        raise RuntimeError(
            "Não foi possível selecionar a opção "
            "'Notificação ou Residência'."
        )

    def _localizacao_esta_selecionada(self) -> bool:
        try:
            contexto = self._localizar_contexto_formulario()

            return self._select_tem_opcao_selecionada(
                contexto=contexto,
                texto_opcao=self._localizacao_esperada,
                exato=True
            )

        except Exception:
            return False

    def _selecionar_campo_evolucao(
        self,
        contexto: Page | Frame
    ):
        if self._selecionar_opcao_em_qualquer_select(
            contexto=contexto,
            texto_opcao="Evolução",
            exato=False
        ):
            return

        raise RuntimeError(
            "Não foi possível selecionar a opção "
            "'Evolução' no campo 'Campo'."
        )

    def _evolucao_esta_selecionada(self) -> bool:
        try:
            contexto = self._localizar_contexto_formulario()

            return self._select_tem_opcao_selecionada(
                contexto=contexto,
                texto_opcao="Evolução",
                exato=False
            )

        except Exception:
            return False

    def _selecionar_criterio_obito_por_agravo(
        self,
        contexto: Page | Frame
    ):
        texto_criterio = "2 - Óbito por Agravo"

        if self._selecionar_opcao_em_qualquer_select(
            contexto=contexto,
            texto_opcao=texto_criterio,
            exato=True
        ):
            return

        campo, container = self._localizar_campo_criterio(
            contexto
        )

        campo.scroll_into_view_if_needed()

        if (
            container is not None
            and self._clicar_seta_combo(container)
        ):
            if self._esperar_ate(
                condicao=lambda: (
                    self._opcao_combo_esta_visivel(
                        texto_criterio
                    )
                ),
                tempo_limite_segundos=2
            ):
                if self._clicar_opcao_combo_visivel(
                    texto_criterio
                ):
                    return

        try:
            campo.click(timeout=6_000)
            campo.press("Control+A")
            campo.fill(texto_criterio)

        except Exception:
            campo.click(timeout=6_000)
            campo.press("Control+A")
            campo.type(
                texto_criterio,
                delay=35
            )

        if self._esperar_ate(
            condicao=lambda: (
                self._opcao_combo_esta_visivel(
                    texto_criterio
                )
            ),
            tempo_limite_segundos=2
        ):
            if self._clicar_opcao_combo_visivel(
                texto_criterio
            ):
                return

        campo.press("ArrowDown")
        campo.press("Enter")

    def _localizar_campo_criterio(
        self,
        contexto: Page | Frame
    ) -> tuple[Locator, Locator | None]:
        try:
            controles = contexto.get_by_label(
                "Critério de Seleção",
                exact=False
            )

            for indice in range(controles.count()):
                controle = controles.nth(indice)

                if (
                    controle.is_visible()
                    and self._tag_name(controle) == "input"
                ):
                    return (
                        controle,
                        self._container_proximo(controle)
                    )

        except Exception:
            pass

        candidatos = contexto.locator(
            "td, div"
        ).filter(
            has_text="Critério de Seleção"
        )

        for indice in range(candidatos.count()):
            candidato = candidatos.nth(indice)

            try:
                if not candidato.is_visible():
                    continue

                inputs = candidato.locator(
                    "input:not([type]), "
                    "input[type='text']"
                )

                for indice_input in range(inputs.count()):
                    campo = inputs.nth(indice_input)

                    if (
                        campo.is_visible()
                        and campo.is_enabled()
                    ):
                        return campo, candidato

            except Exception:
                continue

        inputs = contexto.locator(
            "input:not([type]), "
            "input[type='text']"
        )

        for indice in range(inputs.count()):
            campo = inputs.nth(indice)

            try:
                if not campo.is_visible():
                    continue

                valor = self._normalizar_texto(
                    campo.input_value()
                )

                placeholder = self._normalizar_texto(
                    campo.get_attribute("placeholder") or ""
                )

                if (
                    "selecione valor no campo" in valor
                    or "selecione valor no campo" in placeholder
                ):
                    return (
                        campo,
                        self._container_proximo(campo)
                    )

            except Exception:
                continue

        raise RuntimeError(
            "Não foi possível localizar o campo "
            "'Critério de Seleção'."
        )

    def _criterio_obito_esta_selecionado(self) -> bool:
        try:
            contexto = self._localizar_contexto_formulario()

            return self._select_tem_opcao_selecionada(
                contexto=contexto,
                texto_opcao="2 - Óbito por Agravo",
                exato=True
            )

        except Exception:
            # Compatibilidade com um possível combo antigo.
            alvo = self._normalizar_texto(
                "2 - Óbito por Agravo"
            )

            for contexto in self._obter_contextos():
                try:
                    campo, _ = self._localizar_campo_criterio(
                        contexto
                    )

                    if alvo in self._normalizar_texto(
                        campo.input_value()
                    ):
                        return True

                except Exception:
                    continue

            return False

    # ------------------------------------------------------------------
    # Componentes antigos
    # ------------------------------------------------------------------

    def _clicar_seta_combo(
        self,
        container: Locator
    ) -> bool:
        seletores = [
            "[class*='combobox-button']",
            "[class*='combo-button']",
            "[class*='combo'][class*='button']",
            "input[type='button']",
            "button",
            "img",
            "a"
        ]

        for seletor in seletores:
            elementos = container.locator(seletor)

            for indice in range(elementos.count()):
                elemento = elementos.nth(indice)

                try:
                    if not elemento.is_visible():
                        continue

                    elemento.click(
                        timeout=3_000,
                        force=True
                    )
                    return True

                except Exception:
                    continue

        return False

    def _opcao_combo_esta_visivel(
        self,
        texto_opcao: str
    ) -> bool:
        alvo = self._normalizar_texto(
            texto_opcao
        )

        for contexto in self._obter_contextos():
            candidatos = contexto.get_by_text(
                texto_opcao,
                exact=False
            )

            try:
                for indice in range(candidatos.count()):
                    candidato = candidatos.nth(indice)

                    if not candidato.is_visible():
                        continue

                    if self._tag_name(candidato) == "input":
                        continue

                    texto = self._normalizar_texto(
                        candidato.inner_text()
                    )

                    if alvo in texto:
                        return True

            except Exception:
                continue

        return False

    def _clicar_opcao_combo_visivel(
        self,
        texto_opcao: str
    ) -> bool:
        alvo = self._normalizar_texto(
            texto_opcao
        )

        for contexto in self._obter_contextos():
            candidatos = contexto.get_by_text(
                texto_opcao,
                exact=False
            )

            try:
                for indice in range(candidatos.count()):
                    candidato = candidatos.nth(indice)

                    if not candidato.is_visible():
                        continue

                    if self._tag_name(candidato) == "input":
                        continue

                    texto = self._normalizar_texto(
                        candidato.inner_text()
                    )

                    if alvo not in texto:
                        continue

                    candidato.click(
                        timeout=6_000,
                        force=True
                    )
                    return True

            except Exception:
                continue

        return False

    # ------------------------------------------------------------------
    # Selects e inputs
    # ------------------------------------------------------------------

    def _selecionar_opcao_em_qualquer_select(
        self,
        contexto: Page | Frame,
        texto_opcao: str,
        exato: bool
    ) -> bool:
        selects = contexto.locator("select")

        for indice in range(selects.count()):
            select = selects.nth(indice)

            try:
                if not select.is_visible():
                    continue

                textos = select.locator(
                    "option"
                ).all_text_contents()

                if not self._select_contem_opcao(
                    textos=textos,
                    alvo=texto_opcao,
                    exato=exato
                ):
                    continue

                self._selecionar_opcao_select(
                    select=select,
                    textos=textos,
                    alvo=texto_opcao,
                    exato=exato
                )
                return True

            except RuntimeError:
                raise

            except Exception:
                continue

        return False

    def _select_contem_opcao(
        self,
        textos: list[str],
        alvo: str,
        exato: bool
    ) -> bool:
        alvo_normalizado = self._normalizar_texto(
            alvo
        )

        for texto in textos:
            atual = self._normalizar_texto(
                texto
            )

            corresponde = (
                atual == alvo_normalizado
                if exato
                else alvo_normalizado in atual
            )

            if corresponde:
                return True

        return False

    def _selecionar_opcao_select(
        self,
        select: Locator,
        textos: list[str],
        alvo: str,
        exato: bool
    ):
        alvo_normalizado = self._normalizar_texto(
            alvo
        )

        opcoes = select.locator("option")

        for indice, texto in enumerate(textos):
            atual = self._normalizar_texto(
                texto
            )

            corresponde = (
                atual == alvo_normalizado
                if exato
                else alvo_normalizado in atual
            )

            if not corresponde:
                continue

            opcao = opcoes.nth(indice)
            valor = opcao.get_attribute("value")

            if valor is not None:
                select.select_option(value=valor)
            else:
                select.select_option(label=texto)

            return

        raise RuntimeError(
            f"A opção '{alvo}' não foi encontrada."
        )

    def _select_tem_opcao_selecionada(
        self,
        contexto: Page | Frame,
        texto_opcao: str,
        exato: bool
    ) -> bool:
        """
        Verifica opções selecionadas sem usar
        ``option:checked.inner_text()``.

        Em alguns selects antigos do SINAN não há um elemento
        ``option:checked`` acessível ao Playwright. O método anterior
        esperava o timeout padrão de 30 segundos antes de continuar.

        Aqui o texto selecionado é lido diretamente de
        ``selectedIndex`` no próprio elemento ``select``.
        """

        alvo = self._normalizar_texto(
            texto_opcao
        )

        selects = contexto.locator("select")

        try:
            quantidade = selects.count()
        except Exception:
            return False

        for indice in range(quantidade):
            select = selects.nth(indice)

            try:
                if not select.is_visible():
                    continue

                texto_selecionado = select.evaluate(
                    """
                    elemento => {
                        const indice = elemento.selectedIndex;

                        if (
                            indice < 0
                            || !elemento.options
                            || !elemento.options[indice]
                        ) {
                            return "";
                        }

                        return (
                            elemento.options[indice].textContent
                            || elemento.options[indice].innerText
                            || ""
                        );
                    }
                    """
                )

                selecionado = self._normalizar_texto(
                    str(texto_selecionado)
                )

                corresponde = (
                    selecionado == alvo
                    if exato
                    else alvo in selecionado
                )

                if corresponde:
                    return True

            except Exception:
                continue

        return False

    def _localizar_input_por_rotulo(
        self,
        contexto: Page | Frame,
        rotulo: str,
        indice_fallback: int
    ) -> Locator:
        try:
            controles = contexto.get_by_label(
                rotulo,
                exact=False
            )

            for indice in range(controles.count()):
                controle = controles.nth(indice)

                if (
                    controle.is_visible()
                    and self._tag_name(controle) == "input"
                ):
                    return controle

        except Exception:
            pass

        inputs_visiveis = self._inputs_texto_visiveis(
            contexto
        )

        if indice_fallback < len(inputs_visiveis):
            return inputs_visiveis[indice_fallback]

        raise RuntimeError(
            f"Não foi possível localizar o campo '{rotulo}'."
        )

    def _inputs_texto_visiveis(
        self,
        contexto: Page | Frame
    ) -> list[Locator]:
        resultado: list[Locator] = []

        inputs = contexto.locator(
            "input:not([type]), "
            "input[type='text']"
        )

        for indice in range(inputs.count()):
            campo = inputs.nth(indice)

            try:
                if (
                    campo.is_visible()
                    and campo.is_enabled()
                ):
                    resultado.append(campo)

            except Exception:
                continue

        return resultado

    def _preencher_input(
        self,
        campo: Locator,
        valor: str,
        nome_campo: str
    ):
        campo.scroll_into_view_if_needed()
        campo.click(timeout=6_000)
        campo.fill(valor)
        campo.press("Tab")

        try:
            valor_atual = campo.input_value().strip()

            if valor_atual != valor:
                raise RuntimeError(
                    f"O campo '{nome_campo}' não aceitou "
                    f"o valor esperado."
                )

        except RuntimeError:
            raise

        except Exception:
            # O DOM pode ter sido reconstruído. A validação externa
            # localizará o campo atual.
            pass


    # ------------------------------------------------------------------
    # Adição e confirmação do critério
    # ------------------------------------------------------------------

    def _aguardar_botao_adicionar_habilitado(
        self,
        tempo_limite_segundos: float
    ) -> Locator:
        """
        Localiza o botão Adicionar na página ou nos frames
        e aguarda somente até ele ficar habilitado.
        """

        limite = monotonic() + tempo_limite_segundos

        while monotonic() < limite:
            self._garantir_pagina_aberta()

            if self._processamento_sinan_visivel():
                self._aguardar_fim_processamento()

            for contexto in self._obter_contextos():
                localizadores = [
                    contexto.get_by_role(
                        "button",
                        name="Adicionar",
                        exact=True
                    ),
                    contexto.locator(
                        "input[type='button'][value='Adicionar'], "
                        "input[type='submit'][value='Adicionar']"
                    ),
                    contexto.locator("button").filter(
                        has_text="Adicionar"
                    )
                ]

                for localizador in localizadores:
                    try:
                        quantidade = localizador.count()
                    except Exception:
                        continue

                    for indice in range(quantidade):
                        botao = localizador.nth(indice)

                        try:
                            if (
                                botao.is_visible()
                                and botao.is_enabled()
                            ):
                                return botao

                        except Exception:
                            continue

            self.pagina.wait_for_timeout(
                self.INTERVALO_VERIFICACAO_MS
            )

        raise RuntimeError(
            "O botão 'Adicionar' não ficou habilitado "
            f"após {tempo_limite_segundos} segundos."
        )

    def _aguardar_criterio_obito_adicionado(
        self,
        ocorrencias_antes: int,
        tempo_limite_segundos: float
    ) -> int:
        """
        Aguarda a criação de uma nova ocorrência visível do
        critério fora dos campos de edição.

        A confirmação não depende de nomes de classes específicos
        do SINAN. Ela procura uma linha ou bloco visível contendo
        simultaneamente Evolução e Óbito por Agravo, fora de selects.
        """

        limite = monotonic() + tempo_limite_segundos
        maior_contagem = ocorrencias_antes

        while monotonic() < limite:
            self._garantir_pagina_aberta()

            if self._processamento_sinan_visivel():
                self._aguardar_fim_processamento()

            contagem_atual = (
                self._contar_criterios_obito_registrados()
            )

            maior_contagem = max(
                maior_contagem,
                contagem_atual
            )

            if contagem_atual > ocorrencias_antes:
                return contagem_atual

            self.pagina.wait_for_timeout(
                self.INTERVALO_VERIFICACAO_MS
            )

        raise RuntimeError(
            "O botão Adicionar foi acionado, mas não foi "
            "possível confirmar o critério na lista. "
            f"Ocorrências antes: {ocorrencias_antes}; "
            f"maior contagem observada: {maior_contagem}."
        )

    def _contar_criterios_obito_registrados(self) -> int:
        """
        Conta blocos visíveis que representam um critério já
        adicionado, ignorando os valores que ainda estão nos
        campos select do editor.

        A leitura ocorre em uma única avaliação JavaScript por
        contexto, evitando timeouts e buscas lentas.
        """

        script = """
            raiz => {
                const normalizar = texto => (
                    String(texto || "")
                        .normalize("NFD")
                        .replace(/[\\u0300-\\u036f]/g, "")
                        .toLowerCase()
                        .replace(/\\s+/g, " ")
                        .trim()
                );

                const visivel = elemento => {
                    if (!elemento) {
                        return false;
                    }

                    const estilo = window.getComputedStyle(elemento);
                    const retangulo = elemento.getBoundingClientRect();

                    return (
                        estilo.display !== "none"
                        && estilo.visibility !== "hidden"
                        && retangulo.width > 0
                        && retangulo.height > 0
                    );
                };

                const encontrados = new Set();

                const registrar = elementoInicial => {
                    let elemento = elementoInicial;

                    for (
                        let nivel = 0;
                        elemento
                            && elemento !== raiz
                            && nivel < 8;
                        nivel += 1
                    ) {
                        if (!visivel(elemento)) {
                            elemento = elemento.parentElement;
                            continue;
                        }

                        const texto = normalizar(
                            elemento.innerText
                            || elemento.textContent
                            || ""
                        );

                        const contemSelect = Boolean(
                            elemento.querySelector("select")
                        );

                        if (
                            !contemSelect
                            && texto.includes("evolucao")
                            && texto.includes("obito por agravo")
                        ) {
                            encontrados.add(elemento);
                            break;
                        }

                        elemento = elemento.parentElement;
                    }
                };

                const caminhante = document.createTreeWalker(
                    raiz,
                    NodeFilter.SHOW_TEXT
                );

                let noTexto = caminhante.nextNode();

                while (noTexto) {
                    const pai = noTexto.parentElement;

                    if (
                        pai
                        && !pai.closest(
                            "select, option, script, style"
                        )
                    ) {
                        const texto = normalizar(
                            noTexto.nodeValue
                        );

                        if (texto.includes("obito por agravo")) {
                            registrar(pai);
                        }
                    }

                    noTexto = caminhante.nextNode();
                }

                const controles = raiz.querySelectorAll(
                    "input, textarea"
                );

                for (const controle of controles) {
                    if (
                        !visivel(controle)
                        || controle.closest("select")
                    ) {
                        continue;
                    }

                    const valor = normalizar(
                        controle.value
                    );

                    if (valor.includes("obito por agravo")) {
                        registrar(controle);
                    }
                }

                return encontrados.size;
            }
        """

        total = 0

        for contexto in self._obter_contextos():
            try:
                corpo = contexto.locator("body")

                if corpo.count() == 0:
                    continue

                total += int(
                    corpo.evaluate(script)
                )

            except Exception:
                continue

        return total

    # ------------------------------------------------------------------
    # Sincronização específica com "Processando"
    # ------------------------------------------------------------------

    def _sincronizar_processamento_relevante(self) -> bool:
        """
        Observa o popup somente depois dos quatro campos que
        realmente podem dispará-lo.

        Sem popup: continua em até 350 ms.
        Com popup: espera apenas até ele desaparecer.
        """

        limite = (
            monotonic()
            + self.JANELA_DETECCAO_PROCESSAMENTO_MS / 1000
        )

        while monotonic() < limite:
            self._garantir_pagina_aberta()

            if self._processamento_sinan_visivel():
                self._aguardar_fim_processamento()
                return True

            self.pagina.wait_for_timeout(
                self.INTERVALO_VERIFICACAO_MS
            )

        return False

    def _aguardar_fim_processamento(self):
        limite = (
            monotonic()
            + self.TEMPO_PROCESSAMENTO_SEGUNDOS
        )

        ausente_desde: float | None = None
        estabilidade = (
            self.ESTABILIDADE_APOS_PROCESSAMENTO_MS / 1000
        )

        while monotonic() < limite:
            self._garantir_pagina_aberta()
            agora = monotonic()

            if self._processamento_sinan_visivel():
                ausente_desde = None

            else:
                if ausente_desde is None:
                    ausente_desde = agora

                elif agora - ausente_desde >= estabilidade:
                    return

            self.pagina.wait_for_timeout(
                self.INTERVALO_VERIFICACAO_MS
            )

        raise RuntimeError(
            "O SINAN permaneceu em processamento por mais de "
            f"{self.TEMPO_PROCESSAMENTO_SEGUNDOS} segundos."
        )

    def _processamento_sinan_visivel(self) -> bool:
        """
        Detecta somente o texto real Processando.

        Não usa seletores genéricos de modal, pois eles podem
        permanecer no DOM e causar falsos positivos e pausas longas.
        """

        for contexto in self._obter_contextos():
            try:
                candidatos = contexto.get_by_text(
                    "Processando",
                    exact=False
                )

                for indice in range(candidatos.count()):
                    if candidatos.nth(indice).is_visible():
                        return True

            except Exception:
                continue

        return False

    # ------------------------------------------------------------------
    # Confirmações rápidas e restauração pontual
    # ------------------------------------------------------------------

    def _confirmar_rapido(
        self,
        condicao,
        descricao: str
    ):
        limite = (
            monotonic()
            + self.TEMPO_CONFIRMACAO_RAPIDA_SEGUNDOS
        )

        while monotonic() < limite:
            self._garantir_pagina_aberta()

            if self._processamento_sinan_visivel():
                self._aguardar_fim_processamento()

            try:
                if condicao():
                    return

            except Exception:
                pass

            self.pagina.wait_for_timeout(
                self.INTERVALO_VERIFICACAO_MS
            )

        raise RuntimeError(
            f"Não foi possível confirmar {descricao}."
        )

    def _garantir_filtros_basicos_rapido(self):
        if (
            self._data_inicial_esperada is not None
            and self._data_final_esperada is not None
            and not self._periodo_e_datas_estao_corretos()
        ):
            self._garantir_periodo_e_datas()

        if (
            self._agravo_esperado is not None
            and not self._agravo_esta_selecionado()
        ):
            contexto = self._localizar_contexto_formulario()

            self._selecionar_agravo_combo(
                contexto=contexto,
                nome_agravo=self._agravo_esperado
            )

            self._sincronizar_processamento_relevante()

            self._confirmar_rapido(
                condicao=self._agravo_esta_selecionado,
                descricao=f"Agravo {self._agravo_esperado}"
            )

        if not self._localizacao_esta_selecionada():
            contexto = self._localizar_contexto_formulario()

            self._selecionar_notificacao_ou_residencia(
                contexto=contexto
            )

            self._sincronizar_processamento_relevante()

            self._confirmar_rapido(
                condicao=self._localizacao_esta_selecionada,
                descricao="Notificação ou Residência"
            )

    def _estado_final_esta_correto(self) -> bool:
        return (
            self._periodo_e_datas_estao_corretos()
            and self._agravo_esta_selecionado()
            and self._localizacao_esta_selecionada()
            and self._evolucao_esta_selecionada()
            and self._criterio_obito_esta_selecionado()
        )

    # ------------------------------------------------------------------
    # Esperas curtas por estado
    # ------------------------------------------------------------------

    def _aguardar_opcao_em_select(
        self,
        texto_opcao: str,
        exato: bool,
        tempo_limite_segundos: float
    ):
        limite = monotonic() + tempo_limite_segundos

        while monotonic() < limite:
            self._garantir_pagina_aberta()

            if self._processamento_sinan_visivel():
                self._aguardar_fim_processamento()

            try:
                contexto = self._localizar_contexto_formulario()
                selects = contexto.locator("select")

                for indice in range(selects.count()):
                    select = selects.nth(indice)

                    if not select.is_visible():
                        continue

                    textos = select.locator(
                        "option"
                    ).all_text_contents()

                    if self._select_contem_opcao(
                        textos=textos,
                        alvo=texto_opcao,
                        exato=exato
                    ):
                        return

            except Exception:
                pass

            self.pagina.wait_for_timeout(
                self.INTERVALO_VERIFICACAO_MS
            )

        raise RuntimeError(
            f"A opção '{texto_opcao}' não ficou disponível "
            f"após {tempo_limite_segundos} segundos."
        )

    def _esperar_ate(
        self,
        condicao,
        tempo_limite_segundos: float
    ) -> bool:
        limite = monotonic() + tempo_limite_segundos

        while monotonic() < limite:
            try:
                if condicao():
                    return True

            except Exception:
                pass

            self.pagina.wait_for_timeout(
                self.INTERVALO_VERIFICACAO_MS
            )

        return False

    # ------------------------------------------------------------------
    # Formulário, frames e utilidades
    # ------------------------------------------------------------------

    def _aguardar_formulario_consulta(self):
        limite = (
            monotonic()
            + self.TEMPO_FORMULARIO_SEGUNDOS
        )

        while monotonic() < limite:
            self._garantir_pagina_aberta()

            if self._formulario_consulta_esta_aberto():
                return

            self.pagina.wait_for_timeout(
                self.INTERVALO_VERIFICACAO_MS
            )

        raise RuntimeError(
            "A tela de Notificação Individual não foi "
            f"confirmada após "
            f"{self.TEMPO_FORMULARIO_SEGUNDOS} segundos."
        )

    def _formulario_consulta_esta_aberto(self) -> bool:
        try:
            self._localizar_contexto_formulario()
            return True

        except RuntimeError:
            return False

    def _localizar_contexto_formulario(
        self
    ) -> Page | Frame:
        textos_esperados = [
            "Período de Notificação",
            "Data Inicial",
            "Data Final",
            "Agravo"
        ]

        for contexto in self._obter_contextos():
            encontrados = sum(
                self._texto_existe_no_contexto(
                    contexto,
                    texto
                )
                for texto in textos_esperados
            )

            if encontrados >= 3:
                return contexto

        raise RuntimeError(
            "O formulário de Notificação Individual "
            "não foi localizado."
        )

    def _procurar_elemento_visivel(
        self,
        texto: str
    ) -> Locator | None:
        for contexto in self._obter_contextos():
            localizadores = [
                contexto.get_by_role(
                    "link",
                    name=texto,
                    exact=True
                ),
                contexto.get_by_text(
                    texto,
                    exact=True
                )
            ]

            for localizador in localizadores:
                try:
                    for indice in range(
                        localizador.count()
                    ):
                        elemento = localizador.nth(indice)

                        if elemento.is_visible():
                            return elemento

                except Exception:
                    continue

        return None

    def _texto_existe_no_contexto(
        self,
        contexto: Page | Frame,
        texto: str
    ) -> bool:
        try:
            localizador = contexto.get_by_text(
                texto,
                exact=False
            )

            for indice in range(localizador.count()):
                if localizador.nth(indice).is_visible():
                    return True

        except Exception:
            pass

        return False

    def _obter_contextos(
        self
    ) -> list[Page | Frame]:
        contextos: list[Page | Frame] = [
            self.pagina
        ]

        for frame in self.pagina.frames:
            if frame != self.pagina.main_frame:
                contextos.append(frame)

        return contextos

    def _container_proximo(
        self,
        elemento: Locator
    ) -> Locator | None:
        try:
            return elemento.locator(
                "xpath=ancestor::*[self::td or self::div][1]"
            )

        except Exception:
            return None

    def _tag_name(
        self,
        elemento: Locator
    ) -> str:
        return elemento.evaluate(
            "elemento => elemento.tagName.toLowerCase()"
        )

    def _garantir_pagina_aberta(self):
        if self.pagina.is_closed():
            raise RuntimeError(
                "A janela do navegador foi fechada."
            )

        url_atual = self.pagina.url.lower()

        if "/login/" in url_atual:
            raise RuntimeError(
                "A sessão do SINAN expirou ou retornou "
                "à página de login."
            )

    def _normalizar_texto(
        self,
        texto: str
    ) -> str:
        texto_sem_acentos = "".join(
            caractere
            for caractere in unicodedata.normalize(
                "NFD",
                texto
            )
            if unicodedata.category(caractere) != "Mn"
        )

        return " ".join(
            texto_sem_acentos.strip().casefold().split()
        )