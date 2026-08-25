from __future__ import annotations

from datetime import date
from pathlib import Path
import re
from time import monotonic
from typing import Callable

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

    O método preparar_primeira_exportacao:
    - marca o checkbox de identificação do paciente;
    - para antes de clicar em Solicitar;
    - não altera o Agravo;
    - não lê dados de pacientes.

    Os métodos de solicitação:
    - confirmam todos os campos;
    - solicitam primeiro DENGUE;
    - alteram apenas o Agravo para FEBRE DE CHIKUNGUNYA;
    - restauram os demais campos se o AJAX os modificar;
    - capturam números operacionais distintos.

    O acompanhamento:
    - abre Consultar Exportações DBF;
    - procura exatamente os dois números salvos para o dia;
    - lê status, quantidade e disponibilidade do link;
    - atualiza em intervalos moderados até ambos ficarem prontos;
    - ainda não inicia downloads.
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
    TEXTO_SUCESSO_SOLICITACAO = (
        "Solicitação efetuada com sucesso"
    )
    TEXTO_CONSULTAR_DBF = "Consultar Exportações DBF"
    TEXTO_COLUNA_NUMERO = "Número da Solicitação"
    TEXTO_COLUNA_QUANTIDADE = "Quantidade de Registros"
    TEXTO_COLUNA_STATUS = "Status"
    TEXTO_COLUNA_LINK = "Link"
    TEXTO_LINK_DOWNLOAD = "Baixar arquivo DBF"
    TEXTO_STATUS_CONCLUIDO = "Processamento concluído"

    AGRAVO_DENGUE = "DENGUE"
    AGRAVO_CHIKUNGUNYA = "FEBRE DE CHIKUNGUNYA"

    CHAVE_AGRAVO_DENGUE = "dengue"
    CHAVE_AGRAVO_CHIKUNGUNYA = "chikungunya"

    TEMPO_ABRIR_EXPORTACAO_SEGUNDOS = 120
    TEMPO_CONFIRMAR_SOLICITACAO_SEGUNDOS = 90
    TEMPO_LOCALIZAR_CHECKPOINT_SEGUNDOS = 30
    TEMPO_ABRIR_CONSULTA_SEGUNDOS = 60
    TEMPO_CARREGAR_TABELA_SEGUNDOS = 30

    INTERVALO_ATUALIZACAO_PADRAO_SEGUNDOS = 15
    TEMPO_LIMITE_PROCESSAMENTO_PADRAO_SEGUNDOS = 1200
    TEMPO_LIMITE_DOWNLOAD_SEGUNDOS = 180

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

    def solicitar_exportacao_dengue(
        self
    ) -> dict[str, str | bool]:
        """
        Cria uma solicitação real de exportação para DENGUE.

        Este método deve ser chamado depois de
        ``preparar_primeira_exportacao``.
        """

        return self._solicitar_exportacao_agravo(
            agravo_esperado=self.AGRAVO_DENGUE
        )

    def preparar_exportacao_chikungunya(
        self,
        data_referencia: date | None = None
    ) -> dict[str, str | bool]:
        """
        Altera somente o Agravo para FEBRE DE CHIKUNGUNYA e
        garante que os demais campos continuem iguais aos da
        solicitação de Dengue.

        Se uma resposta AJAX limpar algum campo, o valor correto
        é reaplicado antes da segunda solicitação.
        """

        self._garantir_formulario_exportacao()

        self._selecionar_agravo_exportacao(
            self.AGRAVO_CHIKUNGUNYA
        )

        for _ in range(
            self.TENTATIVAS_ESTABILIZAR_FORMULARIO
        ):
            if not self._periodo_e_datas_exportacao_estao_corretos():
                self.preencher_periodo_e_datas_exportacao(
                    data_referencia=data_referencia
                )

            if not self._localizacao_exportacao_esta_selecionada():
                self.preencher_localizacao_exportacao()

            checkpoint = (
                self.marcar_checkpoint_identificacao_paciente()
            )

            agravo_correto = (
                self._agravo_exportacao_esta_selecionado(
                    self.AGRAVO_CHIKUNGUNYA
                )
            )

            campos_corretos = (
                self._periodo_e_datas_exportacao_estao_corretos()
                and self._localizacao_exportacao_esta_selecionada()
                and checkpoint["marcado"]
            )

            if agravo_correto and campos_corretos:
                return {
                    "agravo": self.AGRAVO_CHIKUNGUNYA,
                    "periodo": self.TEXTO_PERIODO_DATA,
                    "data_inicial":
                        self._data_inicial_exportacao or "",
                    "data_final":
                        self._data_final_exportacao or "",
                    "localizacao": self.TEXTO_LOCALIZACAO,
                    "checkpoint_marcado": True,
                    "campos_mantidos": True,
                    "solicitar_acionado": False,
                    "dados_de_pacientes_lidos": False
                }

            if not agravo_correto:
                self._selecionar_agravo_exportacao(
                    self.AGRAVO_CHIKUNGUNYA
                )

            self.pagina.wait_for_timeout(150)

        raise RuntimeError(
            "Não foi possível manter Agravo, datas, localização "
            "e checkbox corretos para FEBRE DE CHIKUNGUNYA."
        )

    def solicitar_exportacao_chikungunya(
        self,
        numero_solicitacao_dengue: str | None = None
    ) -> dict[str, str | bool]:
        """
        Cria a solicitação real de FEBRE DE CHIKUNGUNYA.

        O número da solicitação de Dengue é ignorado durante a
        captura para impedir que a mensagem anterior seja
        confundida com a confirmação nova.
        """

        numeros_ignorados = (
            {str(numero_solicitacao_dengue)}
            if numero_solicitacao_dengue is not None
            else None
        )

        resultado = self._solicitar_exportacao_agravo(
            agravo_esperado=self.AGRAVO_CHIKUNGUNYA,
            numeros_ignorados=numeros_ignorados
        )

        if (
            numero_solicitacao_dengue is not None
            and resultado["numero_solicitacao"]
            == str(numero_solicitacao_dengue)
        ):
            raise RuntimeError(
                "O SINAN retornou o mesmo número para Dengue "
                "e Chikungunya."
            )

        return resultado

    def _solicitar_exportacao_agravo(
        self,
        agravo_esperado: str,
        numeros_ignorados: set[str] | None = None
    ) -> dict[str, str | bool]:
        """
        Valida o formulário, aciona Solicitar e captura o número
        operacional da nova solicitação.
        """

        self._garantir_formulario_exportacao()

        if not self._periodo_e_datas_exportacao_estao_corretos():
            raise RuntimeError(
                "Período ou datas não estão corretos. "
                f"A solicitação de {agravo_esperado} "
                "não foi enviada."
            )

        if not self._localizacao_exportacao_esta_selecionada():
            raise RuntimeError(
                "'Notificação ou Residência' não permaneceu "
                "selecionado. A solicitação não foi enviada."
            )

        checkpoint = (
            self.marcar_checkpoint_identificacao_paciente()
        )

        if not checkpoint["marcado"]:
            raise RuntimeError(
                "O checkbox de identificação do paciente "
                "não permaneceu marcado."
            )

        if not self._agravo_exportacao_esta_selecionado(
            agravo_esperado
        ):
            agravo_atual = (
                self._obter_agravo_exportacao_atual()
            )

            raise RuntimeError(
                "O Agravo atual não corresponde ao esperado. "
                f"Esperado: {agravo_esperado}. "
                f"Encontrado: {agravo_atual}. "
                "A solicitação não foi enviada."
            )

        botao = self._localizar_botao_solicitar()
        marcador_ajax = self._marcar_estado_ajax()

        self._clicar_elemento_resiliente(
            elemento=botao,
            descricao=(
                f"Solicitar exportação de {agravo_esperado}"
            )
        )

        self._aguardar_ajax_apos_acao(
            marcador_ajax=marcador_ajax,
            descricao=(
                f"Solicitação de exportação de "
                f"{agravo_esperado}"
            )
        )

        numero = self._aguardar_numero_solicitacao(
            numeros_ignorados=numeros_ignorados
        )

        return {
            "agravo": agravo_esperado,
            "numero_solicitacao": numero,
            "solicitar_acionado": True,
            "solicitacao_confirmada": True,
            "dados_de_pacientes_lidos": False
        }

    def _selecionar_agravo_exportacao(
        self,
        agravo: str
    ):
        """
        Seleciona o Agravo em um select tradicional ou no combo
        antigo do SINAN.
        """

        if self._agravo_exportacao_esta_selecionado(
            agravo
        ):
            return

        contexto = self._localizar_contexto_exportacao()
        marcador_ajax = self._marcar_estado_ajax()

        selecionou = (
            self._selecionar_agravo_em_select_exportacao(
                contexto=contexto,
                agravo=agravo
            )
        )

        if not selecionou:
            self._agravo_esperado = agravo

            self._selecionar_agravo_combo(
                contexto=contexto,
                nome_agravo=agravo
            )

        self._aguardar_ajax_apos_acao(
            marcador_ajax=marcador_ajax,
            descricao=f"Agravo {agravo}"
        )

        self._confirmar_rapido(
            condicao=lambda: (
                self._agravo_exportacao_esta_selecionado(
                    agravo
                )
            ),
            descricao=f"Agravo {agravo}"
        )

    def _selecionar_agravo_em_select_exportacao(
        self,
        contexto: Page | Frame,
        agravo: str
    ) -> bool:
        alvo = self._normalizar_texto(agravo)
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

                opcoes = select.locator("option")
                textos = opcoes.all_text_contents()
                indice_opcao = None

                for indice_texto, texto in enumerate(textos):
                    if alvo in self._normalizar_texto(texto):
                        indice_opcao = indice_texto
                        break

                if indice_opcao is None:
                    continue

                opcao = opcoes.nth(indice_opcao)
                valor = opcao.get_attribute("value")

                if valor is not None:
                    select.select_option(value=valor)
                else:
                    select.select_option(index=indice_opcao)

                return True

            except Exception:
                continue

        return False

    def _agravo_exportacao_esta_selecionado(
        self,
        agravo: str
    ) -> bool:
        try:
            valor_atual = (
                self._obter_agravo_exportacao_atual()
            )
        except Exception:
            return False

        return (
            self._normalizar_texto(agravo)
            in self._normalizar_texto(valor_atual)
        )

    def _obter_agravo_exportacao_atual(
        self
    ) -> str:
        """
        Lê somente o valor operacional do controle Agravo.

        A tela pode usar ``select`` ou um combo antigo baseado
        em ``input``. Nenhum dado de paciente é acessado.
        """

        contexto = self._localizar_contexto_exportacao()

        # Primeiro tenta o controle associado ao rótulo Agravo.
        try:
            controles = contexto.get_by_label(
                "Agravo",
                exact=False
            )

            for indice in range(controles.count()):
                controle = controles.nth(indice)

                try:
                    if not controle.is_visible():
                        continue

                    valor = self._valor_textual_controle(
                        controle
                    )

                    if valor:
                        return valor

                except Exception:
                    continue

        except Exception:
            pass

        # Depois procura selects que contenham as opções dos
        # agravos usados pela rotina.
        selects = contexto.locator("select")

        try:
            quantidade_selects = selects.count()
        except Exception:
            quantidade_selects = 0

        for indice in range(quantidade_selects):
            select = selects.nth(indice)

            try:
                if not select.is_visible():
                    continue

                opcoes = select.locator(
                    "option"
                ).all_text_contents()

                opcoes_normalizadas = [
                    self._normalizar_texto(texto)
                    for texto in opcoes
                ]

                possui_agravo = any(
                    (
                        self._normalizar_texto(
                            self.AGRAVO_DENGUE
                        ) in texto
                        or self._normalizar_texto(
                            self.AGRAVO_CHIKUNGUNYA
                        ) in texto
                    )
                    for texto in opcoes_normalizadas
                )

                if not possui_agravo:
                    continue

                valor = self._valor_textual_controle(
                    select
                )

                if valor:
                    return valor

            except Exception:
                continue

        # Compatibilidade com combo antigo baseado em input.
        inputs = contexto.locator(
            "input:not([type]), "
            "input[type='text'], "
            "input[readonly], "
            "input[disabled]"
        )

        try:
            quantidade_inputs = inputs.count()
        except Exception:
            quantidade_inputs = 0

        for indice in range(quantidade_inputs):
            campo = inputs.nth(indice)

            try:
                if not campo.is_visible():
                    continue

                valor = campo.evaluate(
                    "elemento => elemento.value || ''"
                )
                valor = str(valor).strip()
                normalizado = self._normalizar_texto(
                    valor
                )

                if (
                    self._normalizar_texto(
                        self.AGRAVO_DENGUE
                    ) in normalizado
                    or self._normalizar_texto(
                        self.AGRAVO_CHIKUNGUNYA
                    ) in normalizado
                ):
                    return valor

            except Exception:
                continue

        raise RuntimeError(
            "Não foi possível identificar o valor atual "
            "do campo Agravo."
        )

    def _valor_textual_controle(
        self,
        controle: Locator
    ) -> str:
        tag = self._tag_name(controle)

        if tag == "select":
            valor = controle.evaluate(
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

            return str(valor).strip()

        if tag == "input":
            valor = controle.evaluate(
                "elemento => elemento.value || ''"
            )

            return str(valor).strip()

        return ""

    def _localizar_botao_solicitar(
        self
    ) -> Locator:
        """
        Localiza o botão principal Solicitar do formulário.

        Evita confundir o botão com os itens do menu Exportação.
        """

        contexto = self._localizar_contexto_exportacao()

        try:
            botoes = contexto.get_by_role(
                "button",
                name="Solicitar",
                exact=True
            )

            for indice in range(botoes.count()):
                botao = botoes.nth(indice)

                if (
                    botao.is_visible()
                    and botao.is_enabled()
                ):
                    return botao

        except Exception:
            pass

        inputs = contexto.locator(
            "input[type='submit'], "
            "input[type='button']"
        )

        try:
            quantidade = inputs.count()
        except Exception:
            quantidade = 0

        for indice in range(quantidade):
            botao = inputs.nth(indice)

            try:
                if (
                    not botao.is_visible()
                    or not botao.is_enabled()
                ):
                    continue

                valor = botao.get_attribute(
                    "value"
                ) or ""

                if (
                    self._normalizar_texto(valor)
                    == self._normalizar_texto("Solicitar")
                ):
                    return botao

            except Exception:
                continue

        botoes_html = contexto.locator("button")

        try:
            quantidade = botoes_html.count()
        except Exception:
            quantidade = 0

        for indice in range(quantidade):
            botao = botoes_html.nth(indice)

            try:
                if (
                    not botao.is_visible()
                    or not botao.is_enabled()
                ):
                    continue

                texto = botao.inner_text()

                if (
                    self._normalizar_texto(texto)
                    == self._normalizar_texto("Solicitar")
                ):
                    return botao

            except Exception:
                continue

        raise RuntimeError(
            "Não foi possível localizar o botão Solicitar."
        )

    def _aguardar_numero_solicitacao(
        self,
        numeros_ignorados: set[str] | None = None
    ) -> str:
        """
        Aguarda a mensagem:

        Solicitação efetuada com sucesso! Número: 1234567

        Na segunda solicitação, números já conhecidos podem ser
        ignorados para que a mensagem de Dengue não seja
        confundida com a de Chikungunya.
        """

        limite = (
            monotonic()
            + self.TEMPO_CONFIRMAR_SOLICITACAO_SEGUNDOS
        )

        ignorados = {
            str(numero)
            for numero in (numeros_ignorados or set())
        }

        padrao_numero = re.compile(
            r"N[uú]mero\s*:\s*(\d+)",
            re.IGNORECASE
        )

        while monotonic() < limite:
            self._garantir_pagina_aberta()
            numeros_encontrados: list[str] = []

            for contexto in self._obter_contextos():
                candidatos = contexto.get_by_text(
                    self.TEXTO_SUCESSO_SOLICITACAO,
                    exact=False
                )

                try:
                    quantidade = candidatos.count()
                except Exception:
                    continue

                for indice in range(quantidade):
                    candidato = candidatos.nth(indice)

                    try:
                        if not candidato.is_visible():
                            continue

                        textos = []

                        texto_direto = (
                            candidato.inner_text().strip()
                        )

                        if texto_direto:
                            textos.append(texto_direto)

                        bloco = candidato.locator(
                            "xpath=ancestor::*"
                            "[self::td or self::div or self::form]"
                            "[1]"
                        )

                        if bloco.count() > 0:
                            texto_bloco = (
                                bloco.first.inner_text().strip()
                            )

                            if texto_bloco:
                                textos.append(texto_bloco)

                        for texto in textos:
                            numeros_encontrados.extend(
                                padrao_numero.findall(texto)
                            )

                    except Exception:
                        continue

            for numero in reversed(numeros_encontrados):
                if numero not in ignorados:
                    return numero

            self.pagina.wait_for_timeout(
                self.INTERVALO_VERIFICACAO_MS
            )

        raise RuntimeError(
            "A solicitação foi acionada, mas não apareceu "
            "um número novo de confirmação dentro do tempo limite."
        )


    def abrir_consulta_exportacoes_dbf(self):
        """
        Abre de forma resiliente:

        Exportação
        → Consultar Exportações DBF

        O submenu do SINAN pode exibir o texto dentro de um ``span``
        enquanto o clique real pertence ao elemento ``a`` pai. Por
        isso, esta rotina procura o link clicável e usa estratégias
        progressivas, sem alterar o restante do fluxo.
        """

        if self._tela_consulta_exportacoes_esta_aberta():
            return

        # Após a segunda solicitação o JSF pode ainda estar
        # estabilizando a tela, mesmo depois da confirmação do número.
        self.pagina.wait_for_timeout(800)

        limite = (
            monotonic()
            + self.TEMPO_ABRIR_CONSULTA_SEGUNDOS
        )
        ultima_falha: Exception | None = None

        while monotonic() < limite:
            self._garantir_pagina_aberta()

            try:
                self._abrir_menu_exportacao()
                self.pagina.wait_for_timeout(250)

                self._clicar_consultar_exportacoes_dbf()

                if self._esperar_ate(
                    condicao=(
                        self._tela_consulta_exportacoes_esta_aberta
                    ),
                    tempo_limite_segundos=12
                ):
                    return

                raise RuntimeError(
                    "O item foi acionado, mas a tabela de "
                    "exportações ainda não apareceu."
                )

            except Exception as erro:
                ultima_falha = erro

                try:
                    self.pagina.keyboard.press("Escape")
                except Exception:
                    pass

                self.pagina.wait_for_timeout(500)

        detalhe = (
            f" Última tentativa: {ultima_falha}"
            if ultima_falha
            else ""
        )

        raise RuntimeError(
            "Não foi possível abrir Exportação → "
            "Consultar Exportações DBF."
            + detalhe
        )


    def consultar_solicitacoes_dbf(
        self,
        numero_dengue: str,
        numero_chikungunya: str
    ) -> dict[str, dict[str, object]]:
        """
        Consulta uma vez as duas solicitações informadas.

        Nesta etapa:
        - não atualiza a página repetidamente;
        - não clica em links;
        - não inicia downloads;
        - lê somente metadados operacionais da tabela.
        """

        self._garantir_tela_consulta_exportacoes()

        numero_dengue = self._validar_numero_solicitacao(
            numero_dengue
        )
        numero_chikungunya = (
            self._validar_numero_solicitacao(
                numero_chikungunya
            )
        )

        if numero_dengue == numero_chikungunya:
            raise ValueError(
                "Os números de Dengue e Chikungunya "
                "precisam ser diferentes."
            )

        return {
            "dengue": self._ler_solicitacao_na_tabela(
                numero_dengue
            ),
            "chikungunya": self._ler_solicitacao_na_tabela(
                numero_chikungunya
            )
        }

    def consultar_solicitacoes_selecionadas(
        self,
        solicitacoes: dict[str, str]
    ) -> dict[str, dict[str, object]]:
        """Consulta somente os números necessários à execução."""

        self._garantir_tela_consulta_exportacoes()

        if not solicitacoes:
            raise ValueError(
                "Informe pelo menos uma solicitação para consulta."
            )

        numeros: dict[str, str] = {}

        for agravo, numero in solicitacoes.items():
            chave = self._normalizar_agravo_consulta(agravo)

            if chave in numeros:
                raise ValueError(
                    "O mesmo agravo foi informado mais de uma vez "
                    "para consulta."
                )

            numeros[chave] = self._validar_numero_solicitacao(
                numero
            )

        if len(set(numeros.values())) != len(numeros):
            raise ValueError(
                "Os números das solicitações precisam ser diferentes."
            )

        return {
            agravo: self._ler_solicitacao_na_tabela(numero)
            for agravo, numero in numeros.items()
        }

    @classmethod
    def _normalizar_agravo_consulta(cls, agravo: object) -> str:
        """Converte nomes internos ou do portal para a chave interna."""

        chave = str(agravo).strip().casefold()
        aliases = {
            cls.CHAVE_AGRAVO_DENGUE: cls.CHAVE_AGRAVO_DENGUE,
            cls.AGRAVO_DENGUE.casefold(): cls.CHAVE_AGRAVO_DENGUE,
            cls.CHAVE_AGRAVO_CHIKUNGUNYA: (
                cls.CHAVE_AGRAVO_CHIKUNGUNYA
            ),
            "chiku": cls.CHAVE_AGRAVO_CHIKUNGUNYA,
            cls.AGRAVO_CHIKUNGUNYA.casefold(): (
                cls.CHAVE_AGRAVO_CHIKUNGUNYA
            )
        }

        try:
            return aliases[chave]
        except KeyError:
            raise ValueError(
                f"Agravo inválido para consulta: {agravo!r}."
            ) from None


    def atualizar_consulta_exportacoes_dbf(self):
        """
        Clica uma única vez em Atualizar e aguarda a tabela
        reaparecer.

        A ação não cria solicitações e não inicia downloads.
        """

        self._garantir_tela_consulta_exportacoes()

        botao = (
            self._localizar_botao_atualizar_exportacoes()
        )
        marcador_ajax = self._marcar_estado_ajax()

        self._clicar_elemento_resiliente(
            elemento=botao,
            descricao="Atualizar exportações DBF"
        )

        self._aguardar_ajax_apos_acao(
            marcador_ajax=marcador_ajax,
            descricao="Atualização das exportações DBF"
        )

        self._aguardar_tela_consulta_exportacoes()

    def aguardar_solicitacoes_prontas(
        self,
        numero_dengue: str,
        numero_chikungunya: str,
        intervalo_segundos: float | None = None,
        tempo_limite_segundos: float | None = None,
        ao_atualizar: Callable[
            [int, dict[str, dict[str, object]]],
            None
        ] | None = None,
        cancelado: Callable[[], bool] | None = None,
        modo_manual_ativo: Callable[[], bool] | None = None
    ) -> dict[str, object]:
        """
        Acompanha as duas solicitações até ambas apresentarem:

        - Status = Processamento concluído;
        - Link = Baixar arquivo DBF.

        A tabela é consultada imediatamente e, se necessário,
        atualizada em intervalos moderados.

        O método:
        - não cria novas solicitações;
        - não clica nos links de download;
        - não lê o conteúdo dos DBFs;
        - aceita cancelamento para futura integração à interface.
        """

        self._garantir_tela_consulta_exportacoes()

        numero_dengue = self._validar_numero_solicitacao(
            numero_dengue
        )
        numero_chikungunya = (
            self._validar_numero_solicitacao(
                numero_chikungunya
            )
        )

        if numero_dengue == numero_chikungunya:
            raise ValueError(
                "Os números de Dengue e Chikungunya "
                "precisam ser diferentes."
            )

        if intervalo_segundos is None:
            intervalo_segundos = (
                self.INTERVALO_ATUALIZACAO_PADRAO_SEGUNDOS
            )

        if tempo_limite_segundos is None:
            tempo_limite_segundos = (
                self.TEMPO_LIMITE_PROCESSAMENTO_PADRAO_SEGUNDOS
            )

        intervalo_segundos = float(
            intervalo_segundos
        )
        tempo_limite_segundos = float(
            tempo_limite_segundos
        )

        if intervalo_segundos < 5:
            raise ValueError(
                "O intervalo de atualização deve ser de "
                "pelo menos 5 segundos."
            )

        if tempo_limite_segundos <= 0:
            raise ValueError(
                "O tempo limite precisa ser maior que zero."
            )

        inicio = monotonic()
        tentativa = 0

        while True:
            self._verificar_cancelamento_exportacao(
                cancelado
            )

            tentativa += 1

            resultados = (
                self.consultar_solicitacoes_dbf(
                    numero_dengue=numero_dengue,
                    numero_chikungunya=(
                        numero_chikungunya
                    )
                )
            )

            if ao_atualizar is not None:
                ao_atualizar(
                    tentativa,
                    resultados
                )

            if self._duas_solicitacoes_estao_prontas(
                resultados
            ):
                return {
                    "tentativas": tentativa,
                    "tempo_decorrido_segundos": round(
                        monotonic() - inicio,
                        1
                    ),
                    "dengue": resultados["dengue"],
                    "chikungunya":
                        resultados["chikungunya"],
                    "ambas_prontas": True,
                    "downloads_iniciados": False,
                    "dados_de_pacientes_lidos": False
                }

            tempo_decorrido = monotonic() - inicio

            if tempo_decorrido >= tempo_limite_segundos:
                return {
                    "tentativas": tentativa,
                    "tempo_decorrido_segundos": round(
                        tempo_decorrido,
                        1
                    ),
                    "dengue": resultados["dengue"],
                    "chikungunya": resultados["chikungunya"],
                    "ambas_prontas": False,
                    "tempo_limite_atingido": True,
                    "downloads_iniciados": False,
                    "dados_de_pacientes_lidos": False
                }

            while (
                modo_manual_ativo is not None
                and modo_manual_ativo()
            ):
                self._aguardar_intervalo_exportacao(
                    segundos=min(0.5, max(
                        0.1,
                        tempo_limite_segundos
                        - (monotonic() - inicio)
                    )),
                    cancelado=cancelado
                )

                tempo_manual = monotonic() - inicio
                if tempo_manual >= tempo_limite_segundos:
                    return {
                        "tentativas": tentativa,
                        "tempo_decorrido_segundos": round(
                            tempo_manual,
                            1
                        ),
                        "dengue": resultados["dengue"],
                        "chikungunya": resultados["chikungunya"],
                        "ambas_prontas": False,
                        "tempo_limite_atingido": True,
                        "downloads_iniciados": False,
                        "dados_de_pacientes_lidos": False
                    }

            tempo_restante = (
                tempo_limite_segundos
                - tempo_decorrido
            )

            espera = min(
                intervalo_segundos,
                tempo_restante
            )

            self._aguardar_intervalo_exportacao(
                segundos=espera,
                cancelado=cancelado
            )

            self._verificar_cancelamento_exportacao(
                cancelado
            )

            self.atualizar_consulta_exportacoes_dbf()

    def aguardar_solicitacoes_selecionadas(
        self,
        solicitacoes: dict[str, str],
        intervalo_segundos: float | None = None,
        tempo_limite_segundos: float | None = None,
        ao_atualizar: Callable[
            [int, dict[str, dict[str, object]]],
            None
        ] | None = None,
        cancelado: Callable[[], bool] | None = None,
        modo_manual_ativo: Callable[[], bool] | None = None
    ) -> dict[str, object]:
        """Acompanha apenas as exportações exigidas pela seleção."""

        self._garantir_tela_consulta_exportacoes()

        if intervalo_segundos is None:
            intervalo_segundos = (
                self.INTERVALO_ATUALIZACAO_PADRAO_SEGUNDOS
            )

        if tempo_limite_segundos is None:
            tempo_limite_segundos = (
                self.TEMPO_LIMITE_PROCESSAMENTO_PADRAO_SEGUNDOS
            )

        intervalo_segundos = float(intervalo_segundos)
        tempo_limite_segundos = float(tempo_limite_segundos)

        if intervalo_segundos < 5:
            raise ValueError(
                "O intervalo de atualização deve ser de "
                "pelo menos 5 segundos."
            )

        if tempo_limite_segundos <= 0:
            raise ValueError(
                "O tempo limite precisa ser maior que zero."
            )

        inicio = monotonic()
        tentativa = 0
        resultados: dict[str, dict[str, object]] = {}

        while True:
            self._verificar_cancelamento_exportacao(cancelado)
            tentativa += 1
            resultados = self.consultar_solicitacoes_selecionadas(
                solicitacoes
            )

            if ao_atualizar is not None:
                ao_atualizar(tentativa, resultados)

            if self._duas_solicitacoes_estao_prontas(resultados):
                return {
                    "tentativas": tentativa,
                    "tempo_decorrido_segundos": round(
                        monotonic() - inicio,
                        1
                    ),
                    **resultados,
                    "todas_prontas": True,
                    "downloads_iniciados": False,
                    "dados_de_pacientes_lidos": False
                }

            tempo_decorrido = monotonic() - inicio

            if tempo_decorrido >= tempo_limite_segundos:
                return {
                    "tentativas": tentativa,
                    "tempo_decorrido_segundos": round(
                        tempo_decorrido,
                        1
                    ),
                    **resultados,
                    "todas_prontas": False,
                    "tempo_limite_atingido": True,
                    "downloads_iniciados": False,
                    "dados_de_pacientes_lidos": False
                }

            while (
                modo_manual_ativo is not None
                and modo_manual_ativo()
            ):
                self._aguardar_intervalo_exportacao(
                    segundos=min(
                        0.5,
                        max(
                            0.1,
                            tempo_limite_segundos
                            - (monotonic() - inicio)
                        )
                    ),
                    cancelado=cancelado
                )

                if monotonic() - inicio >= tempo_limite_segundos:
                    return {
                        "tentativas": tentativa,
                        "tempo_decorrido_segundos": round(
                            monotonic() - inicio,
                            1
                        ),
                        **resultados,
                        "todas_prontas": False,
                        "tempo_limite_atingido": True,
                        "downloads_iniciados": False,
                        "dados_de_pacientes_lidos": False
                    }

            espera = min(
                intervalo_segundos,
                tempo_limite_segundos - tempo_decorrido
            )
            self._aguardar_intervalo_exportacao(
                segundos=espera,
                cancelado=cancelado
            )
            self._verificar_cancelamento_exportacao(cancelado)
            self.atualizar_consulta_exportacoes_dbf()

    def _duas_solicitacoes_estao_prontas(
        self,
        resultados: dict[str, dict[str, object]]
    ) -> bool:
        return all(
            bool(resultado["encontrada"])
            and bool(
                resultado["processamento_concluido"]
            )
            and bool(resultado["link_disponivel"])
            for resultado in resultados.values()
        )

    def _aguardar_intervalo_exportacao(
        self,
        segundos: float,
        cancelado: Callable[[], bool] | None
    ):
        """
        Aguarda em pequenos blocos para permitir cancelamento
        responsivo na futura integração com o ArboHub.
        """

        limite = monotonic() + segundos

        while monotonic() < limite:
            self._garantir_pagina_aberta()
            self._verificar_cancelamento_exportacao(
                cancelado
            )

            restante = limite - monotonic()

            self.pagina.wait_for_timeout(
                int(
                    min(
                        restante,
                        0.25
                    )
                    * 1000
                )
            )

    def _verificar_cancelamento_exportacao(
        self,
        cancelado: Callable[[], bool] | None
    ):
        if (
            cancelado is not None
            and cancelado()
        ):
            raise RuntimeError(
                "O acompanhamento das exportações "
                "foi cancelado."
            )

    def _localizar_botao_atualizar_exportacoes(
        self
    ) -> Locator:
        """
        Localiza o botão Atualizar da tela de consulta.

        Suporta botão HTML, input JSF e link estilizado.
        """

        for contexto in self._obter_contextos():
            candidatos = [
                contexto.get_by_role(
                    "button",
                    name="Atualizar",
                    exact=True
                ),
                contexto.get_by_role(
                    "link",
                    name="Atualizar",
                    exact=True
                )
            ]

            for localizador in candidatos:
                try:
                    quantidade = localizador.count()
                except Exception:
                    continue

                for indice in range(quantidade):
                    elemento = localizador.nth(indice)

                    try:
                        if (
                            elemento.is_visible()
                            and elemento.is_enabled()
                        ):
                            return elemento

                    except Exception:
                        continue

            inputs = contexto.locator(
                "input[type='submit'], "
                "input[type='button']"
            )

            try:
                quantidade_inputs = inputs.count()
            except Exception:
                quantidade_inputs = 0

            for indice in range(quantidade_inputs):
                elemento = inputs.nth(indice)

                try:
                    if (
                        not elemento.is_visible()
                        or not elemento.is_enabled()
                    ):
                        continue

                    valor = (
                        elemento.get_attribute("value")
                        or ""
                    )

                    if (
                        self._normalizar_texto(valor)
                        == self._normalizar_texto(
                            "Atualizar"
                        )
                    ):
                        return elemento

                except Exception:
                    continue

        raise RuntimeError(
            "Não foi possível localizar o botão Atualizar "
            "na tela Consultar Exportações DBF."
        )

    def baixar_exportacao_dbf(
        self,
        numero_solicitacao: str,
        caminho_destino: str | Path
    ) -> dict[str, object]:
        """
        Baixa o ZIP associado ao número exato da solicitação.

        Pré-condições:
        - o navegador foi aberto com downloads permitidos;
        - a tela Consultar Exportações DBF está aberta;
        - a solicitação está concluída;
        - o link de download está disponível.

        O arquivo é salvo no caminho temporário informado.
        A validação do ZIP e a nomenclatura final pertencem ao
        serviço local de arquivos.
        """

        self._garantir_tela_consulta_exportacoes()

        numero_solicitacao = (
            self._validar_numero_solicitacao(
                numero_solicitacao
            )
        )

        resultado = self._ler_solicitacao_na_tabela(
            numero_solicitacao
        )

        if not resultado["encontrada"]:
            raise RuntimeError(
                "A solicitação não foi localizada na tabela: "
                f"{numero_solicitacao}."
            )

        if not resultado["processamento_concluido"]:
            raise RuntimeError(
                "A solicitação ainda não está concluída: "
                f"{numero_solicitacao}."
            )

        if not resultado["link_disponivel"]:
            raise RuntimeError(
                "O link de download ainda não está disponível: "
                f"{numero_solicitacao}."
            )

        link = (
            self._localizar_link_download_solicitacao(
                numero_solicitacao
            )
        )

        caminho_destino = Path(
            caminho_destino
        )
        caminho_destino.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        if caminho_destino.exists():
            raise FileExistsError(
                "O arquivo temporário já existe e não será "
                f"sobrescrito: {caminho_destino}"
            )

        try:
            with self.pagina.expect_download(
                timeout=(
                    self.TEMPO_LIMITE_DOWNLOAD_SEGUNDOS
                    * 1000
                )
            ) as evento_download:
                self._clicar_elemento_resiliente(
                    elemento=link,
                    descricao=(
                        "Baixar arquivo DBF da solicitação "
                        f"{numero_solicitacao}"
                    )
                )

            download = evento_download.value

            falha = download.failure()

            if falha:
                raise RuntimeError(
                    "O navegador informou falha no download: "
                    f"{falha}"
                )

            nome_sugerido = (
                download.suggested_filename
                or ""
            )

            download.save_as(
                str(caminho_destino)
            )

        except Exception:
            if caminho_destino.exists():
                caminho_destino.unlink()
            raise

        if (
            not caminho_destino.exists()
            or caminho_destino.stat().st_size <= 0
        ):
            raise RuntimeError(
                "O download terminou sem produzir "
                "um arquivo válido."
            )

        return {
            "numero_solicitacao": numero_solicitacao,
            "caminho_temporario": caminho_destino,
            "nome_sugerido": nome_sugerido,
            "tamanho_bytes":
                caminho_destino.stat().st_size,
            "download_concluido": True,
            "dados_de_pacientes_lidos": False
        }

    def _localizar_link_download_solicitacao(
        self,
        numero_solicitacao: str
    ) -> Locator:
        """
        Localiza o link da linha cujo número corresponde
        exatamente à solicitação informada.
        """

        tabela_info = (
            self._localizar_tabela_exportacoes()
        )

        if tabela_info is None:
            raise RuntimeError(
                "A tabela de exportações DBF "
                "não foi localizada."
            )

        tabela = tabela_info["tabela"]
        indices = tabela_info["indices"]
        indice_numero = indices["numero"]
        indice_link = indices.get("link")

        if indice_link is None:
            raise RuntimeError(
                "A coluna Link não foi localizada na tabela."
            )

        linhas = tabela.locator("tr")

        for indice_linha in range(linhas.count()):
            linha = linhas.nth(indice_linha)

            try:
                if not linha.is_visible():
                    continue

                celulas = linha.locator("th, td")

                if (
                    indice_numero >= celulas.count()
                    or indice_link >= celulas.count()
                ):
                    continue

                texto_numero = (
                    celulas.nth(
                        indice_numero
                    ).inner_text().strip()
                )
                numero_linha = re.sub(
                    r"\D",
                    "",
                    texto_numero
                )

                if numero_linha != numero_solicitacao:
                    continue

                links = celulas.nth(
                    indice_link
                ).locator("a")

                for indice_atual in range(
                    links.count()
                ):
                    link = links.nth(
                        indice_atual
                    )

                    if not link.is_visible():
                        continue

                    texto = (
                        link.inner_text().strip()
                    )

                    if (
                        self._normalizar_texto(
                            self.TEXTO_LINK_DOWNLOAD
                        )
                        in self._normalizar_texto(
                            texto
                        )
                    ):
                        return link

            except Exception:
                continue

        raise RuntimeError(
            "O link de download não foi localizado "
            "na linha da solicitação "
            f"{numero_solicitacao}."
        )

    def _validar_numero_solicitacao(
        self,
        numero: str
    ) -> str:
        numero = str(numero).strip()

        if not numero.isdigit():
            raise ValueError(
                f"Número de solicitação inválido: {numero!r}."
            )

        return numero

    def _ler_solicitacao_na_tabela(
        self,
        numero: str
    ) -> dict[str, object]:
        """
        Localiza a linha pelo número exato da solicitação.

        A tabela contém somente metadados da exportação:
        número, quantidade, status e link.
        """

        tabela_info = self._localizar_tabela_exportacoes()

        if tabela_info is None:
            raise RuntimeError(
                "A tabela de exportações DBF não foi localizada."
            )

        tabela = tabela_info["tabela"]
        indices = tabela_info["indices"]
        linhas = tabela.locator("tr")

        for indice_linha in range(linhas.count()):
            linha = linhas.nth(indice_linha)

            try:
                if not linha.is_visible():
                    continue

                celulas = linha.locator("th, td")

                if celulas.count() == 0:
                    continue

                textos = [
                    celulas.nth(indice).inner_text().strip()
                    for indice in range(celulas.count())
                ]

                indice_numero = indices["numero"]

                if indice_numero >= len(textos):
                    continue

                numero_linha = re.sub(
                    r"\D",
                    "",
                    textos[indice_numero]
                )

                if numero_linha != numero:
                    continue

                quantidade = self._texto_celula(
                    textos,
                    indices.get("quantidade")
                )
                status = self._texto_celula(
                    textos,
                    indices.get("status")
                )
                texto_link = self._texto_celula(
                    textos,
                    indices.get("link")
                )

                link_disponivel = False

                indice_link = indices.get("link")

                if (
                    indice_link is not None
                    and indice_link < celulas.count()
                ):
                    celula_link = celulas.nth(indice_link)
                    links = celula_link.locator("a")

                    for indice_link_atual in range(
                        links.count()
                    ):
                        link = links.nth(indice_link_atual)

                        try:
                            if not link.is_visible():
                                continue

                            texto_atual = (
                                link.inner_text().strip()
                            )

                            if (
                                self._normalizar_texto(
                                    self.TEXTO_LINK_DOWNLOAD
                                )
                                in self._normalizar_texto(
                                    texto_atual
                                )
                            ):
                                link_disponivel = True
                                texto_link = texto_atual
                                break

                        except Exception:
                            continue

                processamento_concluido = (
                    self._normalizar_texto(
                        self.TEXTO_STATUS_CONCLUIDO
                    )
                    in self._normalizar_texto(status)
                )

                return {
                    "numero_solicitacao": numero,
                    "encontrada": True,
                    "quantidade_registros": quantidade,
                    "status": status,
                    "processamento_concluido":
                        processamento_concluido,
                    "texto_link": texto_link,
                    "link_disponivel": link_disponivel
                }

            except Exception:
                continue

        return {
            "numero_solicitacao": numero,
            "encontrada": False,
            "quantidade_registros": "",
            "status": "Solicitação ainda não localizada",
            "processamento_concluido": False,
            "texto_link": "",
            "link_disponivel": False
        }

    def _texto_celula(
        self,
        textos: list[str],
        indice: int | None
    ) -> str:
        if indice is None or indice >= len(textos):
            return ""

        return textos[indice].strip()

    def _localizar_tabela_exportacoes(
        self
    ) -> dict[str, object] | None:
        """
        Localiza a tabela pelos títulos das colunas, sem depender
        de IDs internos do JSF.
        """

        alvo_numero = self._normalizar_texto(
            self.TEXTO_COLUNA_NUMERO
        )
        alvo_status = self._normalizar_texto(
            self.TEXTO_COLUNA_STATUS
        )

        for contexto in self._obter_contextos():
            tabelas = contexto.locator("table")

            try:
                quantidade_tabelas = tabelas.count()
            except Exception:
                continue

            for indice_tabela in range(quantidade_tabelas):
                tabela = tabelas.nth(indice_tabela)

                try:
                    if not tabela.is_visible():
                        continue

                    linhas = tabela.locator("tr")

                    for indice_linha in range(
                        min(linhas.count(), 5)
                    ):
                        linha = linhas.nth(indice_linha)
                        celulas = linha.locator("th, td")

                        if celulas.count() == 0:
                            continue

                        cabecalhos = [
                            celulas.nth(indice)
                            .inner_text()
                            .strip()
                            for indice in range(
                                celulas.count()
                            )
                        ]

                        normalizados = [
                            self._normalizar_texto(texto)
                            for texto in cabecalhos
                        ]

                        if (
                            not any(
                                alvo_numero in texto
                                for texto in normalizados
                            )
                            or not any(
                                alvo_status == texto
                                or alvo_status in texto
                                for texto in normalizados
                            )
                        ):
                            continue

                        return {
                            "tabela": tabela,
                            "indices": {
                                "numero":
                                    self._indice_cabecalho(
                                        normalizados,
                                        self.TEXTO_COLUNA_NUMERO
                                    ),
                                "quantidade":
                                    self._indice_cabecalho(
                                        normalizados,
                                        self.TEXTO_COLUNA_QUANTIDADE,
                                        obrigatorio=False
                                    ),
                                "status":
                                    self._indice_cabecalho(
                                        normalizados,
                                        self.TEXTO_COLUNA_STATUS
                                    ),
                                "link":
                                    self._indice_cabecalho(
                                        normalizados,
                                        self.TEXTO_COLUNA_LINK,
                                        obrigatorio=False
                                    )
                            }
                        }

                except Exception:
                    continue

        return None

    def _indice_cabecalho(
        self,
        cabecalhos_normalizados: list[str],
        texto_esperado: str,
        obrigatorio: bool = True
    ) -> int | None:
        alvo = self._normalizar_texto(
            texto_esperado
        )

        for indice, texto in enumerate(
            cabecalhos_normalizados
        ):
            if alvo == texto or alvo in texto:
                return indice

        if obrigatorio:
            raise RuntimeError(
                f"A coluna {texto_esperado!r} "
                "não foi localizada na tabela."
            )

        return None

    def _clicar_consultar_exportacoes_dbf(self):
        """
        Aciona especificamente o item Consultar Exportações DBF.

        Prioriza o elemento ``a`` clicável. O fallback por JavaScript
        é usado somente quando o clique normal e o clique forçado não
        conseguem acionar o submenu visível.
        """

        candidatos = (
            self._localizar_candidatos_consultar_exportacoes()
        )

        if not candidatos:
            raise RuntimeError(
                'O item "Consultar Exportações DBF" ficou visível, '
                "mas nenhum link clicável foi localizado."
            )

        falhas: list[str] = []

        for elemento in candidatos:
            try:
                elemento.scroll_into_view_if_needed()
            except Exception:
                pass

            estrategias = (
                (
                    "clique normal",
                    lambda: elemento.click(
                        timeout=5_000
                    )
                ),
                (
                    "clique forçado",
                    lambda: elemento.click(
                        timeout=5_000,
                        force=True
                    )
                ),
                (
                    "clique direto no link",
                    lambda: elemento.evaluate(
                        """
                        (elemento) => {
                            const link =
                                elemento.closest("a")
                                || elemento.querySelector("a")
                                || elemento;

                            link.click();
                        }
                        """
                    )
                )
            )

            for descricao, acao in estrategias:
                try:
                    acao()

                    # Uma mudança de tela pode ocorrer por navegação
                    # completa ou AJAX. A tabela é a confirmação real.
                    if self._esperar_ate(
                        condicao=(
                            self._tela_consulta_exportacoes_esta_aberta
                        ),
                        tempo_limite_segundos=4
                    ):
                        return

                    # O clique pode ter fechado o submenu sem navegar.
                    # Reabre antes da próxima estratégia.
                    self._abrir_menu_exportacao()
                    self.pagina.wait_for_timeout(200)

                except Exception as erro:
                    falhas.append(
                        f"{descricao}: {erro}"
                    )

                    try:
                        self._abrir_menu_exportacao()
                        self.pagina.wait_for_timeout(200)
                    except Exception:
                        pass

        resumo = (
            falhas[-1]
            if falhas
            else "nenhuma estratégia acionou a tela"
        )

        raise RuntimeError(
            "O submenu de exportação foi aberto, mas não foi "
            "possível acionar Consultar Exportações DBF. "
            f"Detalhe: {resumo}"
        )

    def _localizar_candidatos_consultar_exportacoes(
        self
    ) -> list[Locator]:
        """
        Retorna somente candidatos visíveis e converte textos
        internos para o link ``a`` ancestral quando necessário.
        """

        candidatos: list[Locator] = []

        for contexto in self._obter_contextos():
            localizadores = (
                contexto.get_by_role(
                    "link",
                    name=self.TEXTO_CONSULTAR_DBF,
                    exact=True
                ),
                contexto.get_by_role(
                    "link",
                    name=self.TEXTO_CONSULTAR_DBF,
                    exact=False
                ),
                contexto.locator("a").filter(
                    has_text=self.TEXTO_CONSULTAR_DBF
                ),
                contexto.get_by_text(
                    self.TEXTO_CONSULTAR_DBF,
                    exact=False
                )
            )

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

                        link_ancestral = elemento.locator(
                            "xpath=ancestor-or-self::a[1]"
                        )

                        if (
                            link_ancestral.count() > 0
                            and link_ancestral.first.is_visible()
                        ):
                            candidatos.append(
                                link_ancestral.first
                            )
                        else:
                            candidatos.append(
                                elemento
                            )

                    except Exception:
                        continue

        return candidatos

    def _aguardar_tela_consulta_exportacoes(self):
        limite = (
            monotonic()
            + self.TEMPO_CARREGAR_TABELA_SEGUNDOS
        )

        while monotonic() < limite:
            self._garantir_pagina_aberta()

            if self._tela_consulta_exportacoes_esta_aberta():
                return

            self.pagina.wait_for_timeout(
                self.INTERVALO_VERIFICACAO_MS
            )

        raise RuntimeError(
            "A tela Consultar Exportações DBF não carregou "
            "dentro do tempo limite."
        )

    def _garantir_tela_consulta_exportacoes(self):
        if not self._tela_consulta_exportacoes_esta_aberta():
            raise RuntimeError(
                "A tela Consultar Exportações DBF "
                "ainda não está aberta."
            )

    def _tela_consulta_exportacoes_esta_aberta(
        self
    ) -> bool:
        return self._localizar_tabela_exportacoes() is not None

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
