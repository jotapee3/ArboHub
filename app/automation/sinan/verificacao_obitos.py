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

    Também pode adicionar o critério à lista e executar
    a pesquisa sem ler nem registrar dados pessoais das linhas.
    """

    # Limites máximos. Em conexão rápida, o programa avança
    # assim que o estado correto é detectado.
    TEMPO_MENU_SEGUNDOS = 120
    TEMPO_FORMULARIO_SEGUNDOS = 120
    TEMPO_PROCESSAMENTO_SEGUNDOS = 90
    TEMPO_PESQUISA_SEGUNDOS = 180
    JANELA_DETECCAO_PESQUISA_MS = 1200
    ESTABILIDADE_RESULTADO_PESQUISA_MS = 400
    INTERVALO_PESQUISA_MS = 60
    JANELA_INICIO_AJAX_MS = 450
    ESTABILIDADE_APOS_AJAX_MS = 160
    TENTATIVAS_ESTABILIZAR_EVOLUCAO = 4

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

        # Rastreia requisições assíncronas reais do SINAN.
        # A internet lenta aumenta a duração da requisição, mas
        # não cria esperas artificiais quando a conexão está boa.
        self._requisicoes_ajax_pendentes: set[int] = set()
        self._total_requisicoes_ajax = 0
        self._ultima_atividade_ajax = monotonic()

        self.pagina.on(
            "request",
            self._ao_iniciar_requisicao
        )
        self.pagina.on(
            "requestfinished",
            self._ao_finalizar_requisicao
        )
        self.pagina.on(
            "requestfailed",
            self._ao_finalizar_requisicao
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

        Cada seleção aguarda a requisição AJAX real terminar.
        Isso evita começar o campo seguinte enquanto uma resposta
        lenta ainda está reconstruindo o formulário.
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

        if not self._agravo_esta_selecionado():
            contexto = self._localizar_contexto_formulario()
            marcador_ajax = self._marcar_estado_ajax()

            self._selecionar_agravo_combo(
                contexto=contexto,
                nome_agravo=self._agravo_esperado
            )

            self._aguardar_ajax_apos_acao(
                marcador_ajax=marcador_ajax,
                descricao=f"Agravo {self._agravo_esperado}"
            )

        self._confirmar_rapido(
            condicao=self._agravo_esta_selecionado,
            descricao=f"Agravo {self._agravo_esperado}"
        )

        if not self._localizacao_esta_selecionada():
            contexto = self._localizar_contexto_formulario()
            marcador_ajax = self._marcar_estado_ajax()

            self._selecionar_notificacao_ou_residencia(
                contexto=contexto
            )

            self._aguardar_ajax_apos_acao(
                marcador_ajax=marcador_ajax,
                descricao="Notificação ou Residência"
            )

        self._confirmar_rapido(
            condicao=self._localizacao_esta_selecionada,
            descricao="Notificação ou Residência"
        )

        # Uma resposta AJAX pode reconstruir as datas. Só restaura
        # se algum valor tiver sido realmente alterado.
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

        Se uma resposta AJAX lenta reconstruir o formulário e voltar
        Campo para "Selecione", Evolução é aplicada novamente somente
        depois que a requisição anterior terminar.
        """

        texto_criterio = "2 - Óbito por Agravo"

        for _ in range(
            self.TENTATIVAS_ESTABILIZAR_EVOLUCAO
        ):
            self._garantir_filtros_basicos_rapido()

            if not self._evolucao_esta_selecionada():
                contexto = self._localizar_contexto_formulario()
                marcador_ajax = self._marcar_estado_ajax()

                self._selecionar_campo_evolucao(
                    contexto=contexto
                )

                self._aguardar_ajax_apos_acao(
                    marcador_ajax=marcador_ajax,
                    descricao="Campo Evolução"
                )

            # A resposta do servidor já terminou. Se ela apagou
            # Evolução, repete sem aguardar os 12 segundos do critério.
            if not self._evolucao_esta_selecionada():
                continue

            # Aguarda a opção surgir, mas abandona imediatamente
            # se o SINAN voltar Campo para "Selecione".
            criterio_disponivel = (
                self._aguardar_criterio_com_evolucao_estavel(
                    texto_criterio=texto_criterio,
                    tempo_limite_segundos=(
                        self.TEMPO_CARREGAR_CRITERIO_SEGUNDOS
                    )
                )
            )

            if not criterio_disponivel:
                continue

            # Uma resposta anterior pode ter alterado filtros básicos.
            if not self._filtros_basicos_estao_corretos_rapido():
                self._garantir_filtros_basicos_rapido()
                continue

            if not self._criterio_obito_esta_selecionado():
                contexto = self._localizar_contexto_formulario()
                marcador_ajax = self._marcar_estado_ajax()

                self._selecionar_criterio_obito_por_agravo(
                    contexto=contexto
                )

                self._aguardar_ajax_apos_acao(
                    marcador_ajax=marcador_ajax,
                    descricao=texto_criterio
                )

            if not self._evolucao_esta_selecionada():
                continue

            self._confirmar_rapido(
                condicao=self._criterio_obito_esta_selecionado,
                descricao="Critério 2 - Óbito por Agravo"
            )

            if self._estado_final_esta_correto():
                return {
                    "campo": "Evolução",
                    "criterio": texto_criterio
                }

        raise RuntimeError(
            "O SINAN reconstruiu o campo 'Evolução' "
            "repetidamente e não manteve o critério disponível."
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


    def pesquisar_obitos(self) -> dict[str, str | bool]:
        """
        Clica em Pesquisar e confirma que a consulta terminou.

        Antes do clique, instala um MutationObserver temporário.
        Assim, o código reconhece diretamente a atualização AJAX
        do SINAN, mesmo quando o popup Processando aparece rápido
        demais para ser capturado.

        Nenhum conteúdo das linhas de resultado é lido,
        impresso ou salvo.
        """

        if self._contar_criterios_obito_registrados() < 1:
            raise RuntimeError(
                "Adicione o critério de óbito antes "
                "de executar a pesquisa."
            )

        estado_antes = (
            self._capturar_estado_estrutural_resultado()
        )
        url_antes = self.pagina.url

        monitores_iniciais = (
            self._iniciar_monitoramento_pesquisa()
        )

        botao = self._aguardar_botao_pesquisar_habilitado(
            tempo_limite_segundos=8
        )

        try:
            self._clicar_elemento_resiliente(
                elemento=botao,
                descricao="Pesquisar"
            )

            confirmacao = self._aguardar_conclusao_pesquisa(
                estado_antes=estado_antes,
                url_antes=url_antes,
                monitores_iniciais=monitores_iniciais,
                tempo_limite_segundos=(
                    self.TEMPO_PESQUISA_SEGUNDOS
                )
            )

        finally:
            self._encerrar_monitoramento_pesquisa()

        return {
            "pesquisa_concluida": True,
            "confirmacao": confirmacao,
            "dados_lidos": False
        }


    def executar_consulta_por_agravo(
        self,
        agravo: str,
        data_referencia: date | None = None
    ) -> dict[str, str | bool | int]:
        """
        Executa a primeira consulta completa de um agravo.

        Este método configura datas, agravo, localização, campo,
        critério, adiciona o critério e pesquisa.
        """

        periodo = self.preencher_periodo_e_datas(
            data_referencia=data_referencia
        )

        filtros = self.preencher_agravo_e_residencia(
            agravo=agravo
        )

        criterio = self.preencher_criterio_obito()
        adicao = self.adicionar_criterio_obito()
        pesquisa = self.pesquisar_obitos()

        return {
            "agravo": filtros["agravo"],
            "data_inicial": periodo["data_inicial"],
            "data_final": periodo["data_final"],
            "campo": criterio["campo"],
            "criterio": criterio["criterio"],
            "criterios_adicionados": int(
                adicao["ocorrencias_depois"]
            ),
            "pesquisa_concluida": bool(
                pesquisa["pesquisa_concluida"]
            ),
            "confirmacao": str(
                pesquisa["confirmacao"]
            ),
            "dados_lidos": bool(
                pesquisa["dados_lidos"]
            )
        }

    def trocar_agravo_e_pesquisar(
        self,
        agravo: str
    ) -> dict[str, str | bool | int]:
        """
        Troca somente o agravo e executa uma nova pesquisa.

        O critério Evolução = 2 - Óbito por Agravo já adicionado
        permanece na lista. Ele não é removido nem adicionado
        novamente.
        """

        criterios_antes = (
            self._contar_criterios_obito_registrados()
        )

        if criterios_antes < 1:
            raise RuntimeError(
                "Não há critério de óbito registrado para "
                "reutilizar na troca de agravo."
            )

        filtros = self.preencher_agravo_e_residencia(
            agravo=agravo
        )

        criterios_depois = (
            self._contar_criterios_obito_registrados()
        )

        if criterios_depois < 1:
            raise RuntimeError(
                "O SINAN removeu o critério de óbito durante "
                "a troca de agravo."
            )

        pesquisa = self.pesquisar_obitos()

        return {
            "agravo": filtros["agravo"],
            "criterios_antes": criterios_antes,
            "criterios_depois": criterios_depois,
            "criterio_reutilizado": True,
            "pesquisa_concluida": bool(
                pesquisa["pesquisa_concluida"]
            ),
            "confirmacao": str(
                pesquisa["confirmacao"]
            ),
            "dados_lidos": bool(
                pesquisa["dados_lidos"]
            )
        }

    def solicitar_confirmacao_conferencia(
        self,
        agravo: str,
        acao_seguinte: str
    ) -> dict[str, str | bool]:
        """
        Exibe uma pequena janela flutuante dentro do navegador.

        O usuário informa se houve alteração e, quando houver,
        descreve o que mudou. A janela é arrastável e não bloqueia
        a interação com o restante da página do SINAN.

        Nenhum dado apresentado nos resultados é lido pelo código.
        Somente a resposta digitada pelo usuário é retornada.
        """

        self._garantir_pagina_aberta()
        self.pagina.bring_to_front()

        resultado = self.pagina.evaluate(
            """
            ({ agravo, acaoSeguinte }) => new Promise(resolve => {
                const idRaiz = "arbohub-confirmacao-conferencia";

                const existente = document.getElementById(idRaiz);

                if (existente) {
                    existente.remove();
                }

                const normalizarTexto = valor => (
                    String(valor || "").trim()
                );

                const raiz = document.createElement("div");
                raiz.id = idRaiz;

                Object.assign(raiz.style, {
                    position: "fixed",
                    inset: "0",
                    zIndex: "2147483647",
                    pointerEvents: "none",
                    fontFamily:
                        '"Segoe UI", Arial, sans-serif'
                });

                const janela = document.createElement("section");

                Object.assign(janela.style, {
                    position: "absolute",
                    left: "50%",
                    top: "50%",
                    transform: "translate(-50%, -50%)",
                    width: "min(440px, calc(100vw - 32px))",
                    boxSizing: "border-box",
                    borderRadius: "12px",
                    border: "1px solid #30363d",
                    background: "#161b22",
                    color: "#f0f6fc",
                    boxShadow:
                        "0 18px 55px rgba(0, 0, 0, 0.48)",
                    pointerEvents: "auto",
                    overflow: "hidden"
                });

                const cabecalho = document.createElement("div");

                Object.assign(cabecalho.style, {
                    display: "flex",
                    alignItems: "center",
                    gap: "12px",
                    padding: "16px 18px",
                    background: "#1c2128",
                    borderBottom: "1px solid #30363d",
                    cursor: "move",
                    userSelect: "none"
                });

                const icone = document.createElement("div");
                icone.textContent = "✓";

                Object.assign(icone.style, {
                    width: "34px",
                    height: "34px",
                    display: "grid",
                    placeItems: "center",
                    flex: "0 0 auto",
                    borderRadius: "8px",
                    background: "#21262d",
                    color: "#58a6ff",
                    fontWeight: "700",
                    fontSize: "17px"
                });

                const blocoTitulo = document.createElement("div");
                blocoTitulo.style.minWidth = "0";

                const etiqueta = document.createElement("div");
                etiqueta.textContent = "CONFERÊNCIA HUMANA";

                Object.assign(etiqueta.style, {
                    color: "#58a6ff",
                    fontSize: "10px",
                    fontWeight: "700",
                    letterSpacing: "0.08em",
                    marginBottom: "3px"
                });

                const titulo = document.createElement("div");
                titulo.textContent = `Verificação de ${agravo}`;

                Object.assign(titulo.style, {
                    color: "#f0f6fc",
                    fontSize: "17px",
                    fontWeight: "700"
                });

                blocoTitulo.append(
                    etiqueta,
                    titulo
                );

                cabecalho.append(
                    icone,
                    blocoTitulo
                );

                const conteudo = document.createElement("div");

                Object.assign(conteudo.style, {
                    padding: "18px"
                });

                const orientacao = document.createElement("p");
                orientacao.textContent =
                    "Confira os resultados no SINAN. " +
                    "Houve alguma alteração em relação " +
                    "à verificação anterior?";

                Object.assign(orientacao.style, {
                    margin: "0 0 14px",
                    color: "#c9d1d9",
                    fontSize: "13px",
                    lineHeight: "1.5"
                });

                const grupo = document.createElement("div");

                Object.assign(grupo.style, {
                    display: "grid",
                    gap: "8px",
                    marginBottom: "14px"
                });

                const criarOpcao = (
                    valor,
                    texto,
                    marcada
                ) => {
                    const label = document.createElement("label");

                    Object.assign(label.style, {
                        display: "flex",
                        alignItems: "center",
                        gap: "9px",
                        padding: "10px 12px",
                        border: "1px solid #30363d",
                        borderRadius: "8px",
                        background: "#0d1117",
                        color: "#c9d1d9",
                        cursor: "pointer",
                        fontSize: "13px"
                    });

                    const radio = document.createElement("input");
                    radio.type = "radio";
                    radio.name = "arbohub-alteracao";
                    radio.value = valor;
                    radio.checked = marcada;
                    radio.style.accentColor = "#2f81f7";

                    const span = document.createElement("span");
                    span.textContent = texto;

                    label.append(
                        radio,
                        span
                    );

                    return {
                        label,
                        radio
                    };
                };

                const opcaoIgual = criarOpcao(
                    "manteve_igual",
                    "Não houve alteração",
                    true
                );

                const opcaoMudou = criarOpcao(
                    "mudou",
                    "Houve alteração",
                    false
                );

                grupo.append(
                    opcaoIgual.label,
                    opcaoMudou.label
                );

                const rotuloObservacao =
                    document.createElement("label");

                rotuloObservacao.textContent = "O que mudou?";

                Object.assign(rotuloObservacao.style, {
                    display: "block",
                    marginBottom: "6px",
                    color: "#f0f6fc",
                    fontSize: "12px",
                    fontWeight: "600"
                });

                const observacao =
                    document.createElement("textarea");

                observacao.placeholder =
                    "Descreva resumidamente a alteração observada.";

                Object.assign(observacao.style, {
                    width: "100%",
                    minHeight: "82px",
                    resize: "vertical",
                    boxSizing: "border-box",
                    padding: "10px 11px",
                    borderRadius: "8px",
                    border: "1px solid #30363d",
                    outline: "none",
                    background: "#0d1117",
                    color: "#f0f6fc",
                    fontFamily:
                        '"Segoe UI", Arial, sans-serif',
                    fontSize: "12px",
                    lineHeight: "1.45"
                });

                const aviso = document.createElement("div");

                Object.assign(aviso.style, {
                    minHeight: "18px",
                    marginTop: "6px",
                    color: "#f85149",
                    fontSize: "11px"
                });

                const botao = document.createElement("button");
                botao.type = "button";
                botao.textContent =
                    `Sim, confirmar e ${acaoSeguinte}`;

                Object.assign(botao.style, {
                    width: "100%",
                    marginTop: "8px",
                    padding: "11px 14px",
                    border: "1px solid #388bfd",
                    borderRadius: "8px",
                    background: "#1f6feb",
                    color: "#ffffff",
                    cursor: "pointer",
                    fontFamily:
                        '"Segoe UI", Arial, sans-serif',
                    fontSize: "13px",
                    fontWeight: "700"
                });

                const atualizarObservacao = () => {
                    const mudou = opcaoMudou.radio.checked;

                    observacao.disabled = !mudou;
                    observacao.style.opacity = (
                        mudou ? "1" : "0.52"
                    );

                    if (!mudou) {
                        observacao.value = "";
                        aviso.textContent = "";
                    }
                };

                opcaoIgual.radio.addEventListener(
                    "change",
                    atualizarObservacao
                );

                opcaoMudou.radio.addEventListener(
                    "change",
                    atualizarObservacao
                );

                observacao.addEventListener(
                    "focus",
                    () => {
                        observacao.style.borderColor = "#58a6ff";
                    }
                );

                observacao.addEventListener(
                    "blur",
                    () => {
                        observacao.style.borderColor = "#30363d";
                    }
                );

                botao.addEventListener(
                    "mouseenter",
                    () => {
                        botao.style.background = "#388bfd";
                    }
                );

                botao.addEventListener(
                    "mouseleave",
                    () => {
                        botao.style.background = "#1f6feb";
                    }
                );

                botao.addEventListener(
                    "click",
                    () => {
                        const mudou = opcaoMudou.radio.checked;
                        const texto = normalizarTexto(
                            observacao.value
                        );

                        if (mudou && !texto) {
                            aviso.textContent =
                                "Descreva o que mudou para continuar.";
                            observacao.focus();
                            return;
                        }

                        raiz.remove();

                        resolve({
                            confirmado: true,
                            houve_alteracao: mudou,
                            resultado_comparacao: (
                                mudou
                                    ? "mudou"
                                    : "manteve_igual"
                            ),
                            observacao: texto
                        });
                    }
                );

                conteudo.append(
                    orientacao,
                    grupo,
                    rotuloObservacao,
                    observacao,
                    aviso,
                    botao
                );

                janela.append(
                    cabecalho,
                    conteudo
                );

                raiz.append(janela);
                document.body.append(raiz);

                atualizarObservacao();

                let arrastando = false;
                let inicioX = 0;
                let inicioY = 0;
                let origemX = 0;
                let origemY = 0;

                cabecalho.addEventListener(
                    "mousedown",
                    evento => {
                        arrastando = true;

                        const retangulo =
                            janela.getBoundingClientRect();

                        origemX = retangulo.left;
                        origemY = retangulo.top;
                        inicioX = evento.clientX;
                        inicioY = evento.clientY;

                        janela.style.left = `${origemX}px`;
                        janela.style.top = `${origemY}px`;
                        janela.style.transform = "none";

                        evento.preventDefault();
                    }
                );

                window.addEventListener(
                    "mousemove",
                    evento => {
                        if (!arrastando) {
                            return;
                        }

                        const largura = janela.offsetWidth;
                        const altura = janela.offsetHeight;

                        const novoX = Math.min(
                            Math.max(
                                8,
                                origemX
                                + evento.clientX
                                - inicioX
                            ),
                            window.innerWidth - largura - 8
                        );

                        const novoY = Math.min(
                            Math.max(
                                8,
                                origemY
                                + evento.clientY
                                - inicioY
                            ),
                            window.innerHeight - altura - 8
                        );

                        janela.style.left = `${novoX}px`;
                        janela.style.top = `${novoY}px`;
                    }
                );

                window.addEventListener(
                    "mouseup",
                    () => {
                        arrastando = false;
                    }
                );
            })
            """,
            {
                "agravo": agravo,
                "acaoSeguinte": acao_seguinte
            }
        )

        return {
            "confirmado": bool(
                resultado["confirmado"]
            ),
            "houve_alteracao": bool(
                resultado["houve_alteracao"]
            ),
            "resultado_comparacao": str(
                resultado["resultado_comparacao"]
            ),
            "observacao": str(
                resultado["observacao"]
            )
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
        """
        Garante o período e as duas datas mesmo quando o SINAN
        carrega o formulário em etapas.

        Em conexão lenta, o rótulo "Data Final" pode aparecer antes
        do respectivo input, ou o DOM pode ser reconstruído por AJAX.
        Essas situações são transitórias e não devem encerrar a
        rotina imediatamente.
        """

        if (
            self._data_inicial_esperada is None
            or self._data_final_esperada is None
        ):
            raise RuntimeError(
                "As datas esperadas ainda não foram definidas."
            )

        limite = (
            monotonic()
            + self.TEMPO_FORMULARIO_SEGUNDOS
        )
        ultima_falha: Exception | None = None

        while monotonic() < limite:
            self._garantir_pagina_aberta()

            try:
                if self._processamento_sinan_visivel():
                    self._aguardar_fim_processamento()

                contexto = self._localizar_contexto_formulario()

                if not self._periodo_data_esta_selecionado():
                    marcador_ajax = self._marcar_estado_ajax()

                    self._selecionar_periodo_data(
                        contexto
                    )

                    self._aguardar_ajax_apos_acao(
                        marcador_ajax=marcador_ajax,
                        descricao="Período de Notificação"
                    )

                contexto = self._localizar_contexto_formulario()

                campo_inicial = (
                    self._localizar_input_por_rotulo(
                        contexto=contexto,
                        rotulo="Data Inicial",
                        indice_fallback=0
                    )
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

                # O Tab do primeiro campo pode provocar uma
                # reconstrução parcial do formulário. O contexto e
                # o locator são obtidos novamente antes da Data Final.
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

            except Exception as erro:
                # Campo ausente, locator invalidado ou formulário
                # parcialmente carregado são falhas transitórias.
                ultima_falha = erro

            self.pagina.wait_for_timeout(250)

        detalhe = (
            f" Última tentativa: {ultima_falha}"
            if ultima_falha
            else ""
        )

        raise RuntimeError(
            "O SINAN não disponibilizou os campos de período e "
            "datas dentro do tempo esperado. Verifique a conexão "
            "e tente novamente."
            + detalhe
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
    # Pesquisa e confirmação segura
    # ------------------------------------------------------------------

    def _aguardar_botao_pesquisar_habilitado(
        self,
        tempo_limite_segundos: float
    ) -> Locator:
        """
        Localiza o botão Pesquisar dentro do formulário.
        """

        limite = monotonic() + tempo_limite_segundos

        while monotonic() < limite:
            self._garantir_pagina_aberta()

            if self._processamento_sinan_visivel():
                self._aguardar_fim_processamento()

            contexto = self._localizar_contexto_formulario()

            localizadores = [
                contexto.get_by_role(
                    "button",
                    name="Pesquisar",
                    exact=True
                ),
                contexto.locator(
                    "input[type='button'][value='Pesquisar'], "
                    "input[type='submit'][value='Pesquisar']"
                ),
                contexto.locator("button").filter(
                    has_text="Pesquisar"
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
            "O botão 'Pesquisar' não ficou habilitado "
            f"após {tempo_limite_segundos} segundos."
        )

    def _iniciar_monitoramento_pesquisa(self) -> int:
        """
        Instala um observador temporário de alterações no DOM.

        O observador registra somente quantidade e horário de
        mutações estruturais. Ele não lê nem armazena textos,
        células ou dados de pessoas.
        """

        script = """
            () => {
                try {
                    if (window.__arbohubPesquisaObserver) {
                        window.__arbohubPesquisaObserver.disconnect();
                    }

                    const estado = {
                        mutacoes: 0,
                        ultimaMutacao: performance.now()
                    };

                    const observador = new MutationObserver(
                        lista => {
                            let quantidade = 0;

                            for (const mutacao of lista) {
                                if (mutacao.type === "childList") {
                                    quantidade += (
                                        mutacao.addedNodes.length
                                        + mutacao.removedNodes.length
                                    );
                                } else if (
                                    mutacao.type === "characterData"
                                ) {
                                    quantidade += 1;
                                }
                            }

                            if (quantidade > 0) {
                                estado.mutacoes += quantidade;
                                estado.ultimaMutacao = performance.now();
                            }
                        }
                    );

                    observador.observe(
                        document.documentElement || document.body,
                        {
                            childList: true,
                            subtree: true,
                            characterData: true
                        }
                    );

                    window.__arbohubPesquisaEstado = estado;
                    window.__arbohubPesquisaObserver = observador;

                    return true;

                } catch (erro) {
                    return false;
                }
            }
        """

        instalados = 0

        for contexto in self._obter_contextos():
            try:
                if contexto.evaluate(script):
                    instalados += 1

            except Exception:
                continue

        return instalados

    def _ler_monitoramento_pesquisa(
        self
    ) -> dict[str, float | int]:
        """
        Retorna somente métricas técnicas do observador.
        """

        script = """
            () => {
                const estado = window.__arbohubPesquisaEstado;

                if (!estado) {
                    return null;
                }

                return {
                    mutacoes: estado.mutacoes,
                    estavel_ms: (
                        performance.now()
                        - estado.ultimaMutacao
                    )
                };
            }
        """

        monitores = 0
        mutacoes = 0
        estabilidades: list[float] = []

        for contexto in self._obter_contextos():
            try:
                estado = contexto.evaluate(script)

                if estado is None:
                    continue

                monitores += 1
                quantidade = int(
                    estado.get("mutacoes", 0)
                )
                mutacoes += quantidade

                if quantidade > 0:
                    estabilidades.append(
                        float(
                            estado.get("estavel_ms", 0)
                        )
                    )

            except Exception:
                continue

        estabilidade = (
            min(estabilidades)
            if estabilidades
            else 0.0
        )

        return {
            "monitores": monitores,
            "mutacoes": mutacoes,
            "estavel_ms": estabilidade
        }

    def _encerrar_monitoramento_pesquisa(self):
        """
        Desconecta o observador temporário, quando ainda existir.
        """

        script = """
            () => {
                try {
                    if (window.__arbohubPesquisaObserver) {
                        window.__arbohubPesquisaObserver.disconnect();
                    }

                    delete window.__arbohubPesquisaObserver;
                    delete window.__arbohubPesquisaEstado;

                } catch (erro) {
                    // O documento pode ter sido substituído.
                }
            }
        """

        for contexto in self._obter_contextos():
            try:
                contexto.evaluate(script)

            except Exception:
                continue

    def _aguardar_conclusao_pesquisa(
        self,
        estado_antes: dict[str, int],
        url_antes: str,
        monitores_iniciais: int,
        tempo_limite_segundos: float
    ) -> str:
        """
        Confirma a conclusão por atualização AJAX, popup,
        navegação, mudança estrutural ou ciclo do botão.

        O MutationObserver evita que a execução fique aguardando
        quando o popup Processando foi rápido demais para ser visto.
        """

        inicio = monotonic()
        limite = inicio + tempo_limite_segundos
        viu_botao_desabilitado = False
        proxima_verificacao_fallback = inicio

        while monotonic() < limite:
            self._garantir_pagina_aberta()
            agora = monotonic()

            if self._processamento_sinan_visivel():
                self._aguardar_fim_processamento()
                return "popup Processando concluído"

            if self.pagina.url != url_antes:
                return "navegação concluída"

            monitoramento = (
                self._ler_monitoramento_pesquisa()
            )

            monitores_atuais = int(
                monitoramento["monitores"]
            )
            mutacoes = int(
                monitoramento["mutacoes"]
            )
            estavel_ms = float(
                monitoramento["estavel_ms"]
            )

            # Um documento ou frame monitorado foi substituído.
            if (
                monitores_iniciais > 0
                and monitores_atuais < monitores_iniciais
                and agora - inicio >= 0.25
            ):
                return "documento ou frame atualizado"

            # Atualização AJAX detectada e já estabilizada.
            if (
                mutacoes > 0
                and estavel_ms
                >= self.ESTABILIDADE_RESULTADO_PESQUISA_MS
            ):
                return "atualização AJAX concluída"

            botao_habilitado = (
                self._botao_pesquisar_esta_habilitado()
            )

            if not botao_habilitado:
                viu_botao_desabilitado = True

            elif viu_botao_desabilitado:
                return "botão Pesquisar reabilitado"

            # Os sinais de fallback são mais caros. Verificamos
            # apenas duas vezes por segundo, e não a cada ciclo.
            if agora >= proxima_verificacao_fallback:
                proxima_verificacao_fallback = agora + 0.5

                mensagem = self._mensagem_resultado_segura()

                if mensagem is not None:
                    return mensagem

                estado_atual = (
                    self._capturar_estado_estrutural_resultado()
                )

                if estado_atual != estado_antes:
                    return "estrutura de resultados atualizada"

            self.pagina.wait_for_timeout(
                self.INTERVALO_PESQUISA_MS
            )

        raise RuntimeError(
            "A pesquisa foi acionada, mas o SINAN não "
            "apresentou um sinal técnico reconhecível de "
            "conclusão dentro de "
            f"{tempo_limite_segundos} segundos."
        )

    def _botao_pesquisar_esta_habilitado(self) -> bool:
        """
        Verifica rapidamente o estado do botão Pesquisar.
        """

        try:
            contexto = self._localizar_contexto_formulario()
        except RuntimeError:
            return False

        localizadores = [
            contexto.get_by_role(
                "button",
                name="Pesquisar",
                exact=True
            ),
            contexto.locator(
                "input[type='button'][value='Pesquisar'], "
                "input[type='submit'][value='Pesquisar']"
            ),
            contexto.locator("button").filter(
                has_text="Pesquisar"
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
                    if botao.is_visible():
                        return botao.is_enabled()

                except Exception:
                    continue

        return False

    def _mensagem_resultado_segura(self) -> str | None:
        """
        Procura somente mensagens genéricas de resultado.

        Não lê nomes, identificadores nem valores de linhas.
        """

        mensagens = [
            "Nenhum registro encontrado",
            "Nenhum resultado encontrado",
            "Não foram encontrados registros",
            "Consulta realizada com sucesso",
            "Resultado da pesquisa"
        ]

        for contexto in self._obter_contextos():
            for mensagem in mensagens:
                try:
                    candidatos = contexto.get_by_text(
                        mensagem,
                        exact=False
                    )

                    for indice in range(candidatos.count()):
                        if candidatos.nth(indice).is_visible():
                            return mensagem

                except Exception:
                    continue

        return None

    def _capturar_estado_estrutural_resultado(
        self
    ) -> dict[str, int]:
        """
        Captura apenas contagens estruturais da página.

        Não lê texto de células, nomes ou identificadores.
        """

        script = """
            raiz => {
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

                const tabelas = Array.from(
                    raiz.querySelectorAll("table")
                ).filter(visivel);

                let linhas = 0;

                for (const tabela of tabelas) {
                    linhas += Array.from(
                        tabela.querySelectorAll("tbody tr")
                    ).filter(visivel).length;
                }

                const regioesResultado = Array.from(
                    raiz.querySelectorAll(
                        "[id*='result' i], "
                        "[id*='resultado' i], "
                        "[class*='result' i], "
                        "[class*='resultado' i], "
                        "[class*='rich-table' i], "
                        "[class*='rf-dt' i]"
                    )
                ).filter(visivel).length;

                return {
                    tabelas: tabelas.length,
                    linhas: linhas,
                    regioes: regioesResultado
                };
            }
        """

        total = {
            "tabelas": 0,
            "linhas": 0,
            "regioes": 0
        }

        for contexto in self._obter_contextos():
            try:
                corpo = contexto.locator("body")

                if corpo.count() == 0:
                    continue

                estado = corpo.evaluate(script)

                total["tabelas"] += int(
                    estado.get("tabelas", 0)
                )
                total["linhas"] += int(
                    estado.get("linhas", 0)
                )
                total["regioes"] += int(
                    estado.get("regioes", 0)
                )

            except Exception:
                continue

        return total

    # ------------------------------------------------------------------
    # Sincronização pelas requisições reais do SINAN
    # ------------------------------------------------------------------

    def _requisicao_e_assincrona_relevante(
        self,
        requisicao
    ) -> bool:
        """
        Considera XHR, fetch e qualquer POST do formulário JSF.
        Não lê URL, corpo, cabeçalhos nem conteúdo da resposta.
        """

        try:
            return (
                requisicao.resource_type in {"xhr", "fetch"}
                or requisicao.method.upper() == "POST"
            )

        except Exception:
            return False

    def _ao_iniciar_requisicao(self, requisicao):
        if not self._requisicao_e_assincrona_relevante(
            requisicao
        ):
            return

        identificador = id(requisicao)
        self._requisicoes_ajax_pendentes.add(
            identificador
        )
        self._total_requisicoes_ajax += 1
        self._ultima_atividade_ajax = monotonic()

    def _ao_finalizar_requisicao(self, requisicao):
        identificador = id(requisicao)

        if identificador not in self._requisicoes_ajax_pendentes:
            return

        self._requisicoes_ajax_pendentes.discard(
            identificador
        )
        self._ultima_atividade_ajax = monotonic()

    def _marcar_estado_ajax(self) -> int:
        """
        Registra quantas requisições já haviam começado antes
        de uma ação do usuário automatizada.
        """

        return self._total_requisicoes_ajax

    def _aguardar_ajax_apos_acao(
        self,
        marcador_ajax: int,
        descricao: str
    ) -> bool:
        """
        Aguarda a requisição realmente iniciada pela ação.

        Internet boa: avança assim que a requisição termina.
        Internet lenta: aguarda somente o tempo real da resposta.
        Sem requisição: continua após uma janela curta de 450 ms.
        """

        inicio = monotonic()
        limite = inicio + self.TEMPO_PROCESSAMENTO_SEGUNDOS
        limite_inicio = (
            inicio + self.JANELA_INICIO_AJAX_MS / 1000
        )
        estabilidade = (
            self.ESTABILIDADE_APOS_AJAX_MS / 1000
        )
        viu_requisicao = False

        while monotonic() < limite:
            self._garantir_pagina_aberta()
            agora = monotonic()

            if self._total_requisicoes_ajax > marcador_ajax:
                viu_requisicao = True

            if self._processamento_sinan_visivel():
                self._aguardar_fim_processamento()
                viu_requisicao = True

            if viu_requisicao:
                if (
                    not self._requisicoes_ajax_pendentes
                    and agora - self._ultima_atividade_ajax
                    >= estabilidade
                ):
                    return True

            elif agora >= limite_inicio:
                return False

            self.pagina.wait_for_timeout(
                self.INTERVALO_VERIFICACAO_MS
            )

        raise RuntimeError(
            f"O processamento de '{descricao}' não terminou "
            f"após {self.TEMPO_PROCESSAMENTO_SEGUNDOS} segundos."
        )

    def _aguardar_criterio_com_evolucao_estavel(
        self,
        texto_criterio: str,
        tempo_limite_segundos: float
    ) -> bool:
        """
        Aguarda o critério ser carregado enquanto Evolução
        permanece selecionada.

        Se uma resposta tardia voltar Campo para "Selecione",
        encerra imediatamente para que o fluxo reaplique Evolução.
        """

        limite = monotonic() + tempo_limite_segundos

        while monotonic() < limite:
            self._garantir_pagina_aberta()

            if self._processamento_sinan_visivel():
                self._aguardar_fim_processamento()

            if not self._evolucao_esta_selecionada():
                return False

            if self._opcao_esta_disponivel_em_select(
                texto_opcao=texto_criterio,
                exato=True
            ):
                return True

            self.pagina.wait_for_timeout(
                self.INTERVALO_VERIFICACAO_MS
            )

        return False

    def _opcao_esta_disponivel_em_select(
        self,
        texto_opcao: str,
        exato: bool
    ) -> bool:
        """
        Verificação instantânea, sem timeout interno.
        """

        try:
            contexto = self._localizar_contexto_formulario()
            selects = contexto.locator("select")
            quantidade = selects.count()

        except Exception:
            return False

        for indice in range(quantidade):
            select = selects.nth(indice)

            try:
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
                    return True

            except Exception:
                continue

        return False

    def _filtros_basicos_estao_corretos_rapido(self) -> bool:
        return (
            self._periodo_e_datas_estao_corretos()
            and self._agravo_esta_selecionado()
            and self._localizacao_esta_selecionada()
        )

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