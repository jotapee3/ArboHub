from __future__ import annotations

from datetime import date
from queue import Empty, Queue
from threading import Event, Lock, Thread
from time import monotonic
from typing import Any

from app.automation.sinan.exportacao_bases import (
    ExportacaoBasesDbf
)
from app.automation.sinan.navegador_sinan import (
    NavegadorSinan
)
from app.services.checkpoint_service import (
    CheckpointService
)
from app.services.configuracoes_service import (
    ConfiguracoesService
)
from app.services.rotina_bases_service import (
    EventoRotinaBases,
    ProcessamentoBasesPendente,
    RotinaBasesCancelada,
    RotinaBasesService
)
from app.services.selecao_destinos_bases import (
    SelecaoDestinosBases
)


class AtualizacaoBasesService:
    """
    Executa a rotina completa das bases fora da thread da interface.

    O Playwright, o navegador e toda a automação permanecem na
    mesma thread de trabalho. A tela do ArboHub recebe somente
    eventos operacionais por uma fila thread-safe.

    Nenhuma credencial ou conteúdo interno dos DBFs é enviado
    para a interface.
    """

    EVENTO_STATUS = "status"
    EVENTO_ETAPA = "etapa"
    EVENTO_ATUALIZAR = "atualizar"
    EVENTO_CONCLUIDO = "concluido"
    EVENTO_ERRO = "erro"
    EVENTO_CANCELADO = "cancelado"
    EVENTO_ALERTA_PROCESSAMENTO = "alerta_processamento"
    EVENTO_MODO_MANUAL = "modo_manual"
    EVENTO_PENDENTE = "processamento_pendente"
    EVENTO_CORRECAO_MANUAL = "correcao_manual"

    ETAPA_ACESSO = "acesso"
    ETAPA_SOLICITACOES = (
        RotinaBasesService.ETAPA_SOLICITACOES
    )
    ETAPA_PROCESSAMENTO = (
        RotinaBasesService.ETAPA_PROCESSAMENTO
    )
    ETAPA_DOWNLOAD = RotinaBasesService.ETAPA_DOWNLOAD
    ETAPA_HISTORICO = RotinaBasesService.ETAPA_HISTORICO
    ETAPA_EXTRACAO = RotinaBasesService.ETAPA_EXTRACAO
    ETAPA_PASTAS_TESTE = (
        RotinaBasesService.ETAPA_PASTAS_TESTE
    )
    ETAPA_BANCOS_ATUAIS = (
        RotinaBasesService.ETAPA_BANCOS_ATUAIS
    )
    ETAPA_FINALIZACAO = (
        RotinaBasesService.ETAPA_FINALIZACAO
    )

    def __init__(
        self,
        checkpoint_service: CheckpointService | None = None,
        rotina_service: RotinaBasesService | None = None,
        configuracoes_service:
            ConfiguracoesService | None = None
    ):
        self.checkpoint_service = (
            checkpoint_service
            or CheckpointService()
        )
        self.configuracoes_service = (
            configuracoes_service
            or ConfiguracoesService()
        )
        self.rotina_service = (
            rotina_service
            or RotinaBasesService()
        )

        self._eventos: Queue[dict[str, Any]] = Queue()
        self._cancelamento = Event()
        self._modo_manual = Event()
        self._lock = Lock()

        self._modo_manual_disponivel = False
        self._pendencia_atual: dict[str, object] | None = None
        self._thread: Thread | None = None
        self._executando = False
        self._etapa_atual: str | None = None


    # ------------------------------------------------------------------
    # Estado público
    # ------------------------------------------------------------------

    def avaliar_estado_do_dia(
        self,
        selecao_destinos: SelecaoDestinosBases | None = None
    ) -> dict[str, object]:
        """
        Informa à interface se haverá novas solicitações, acesso ao
        navegador ou simples reutilização dos arquivos do dia.
        """

        return self.rotina_service.avaliar_estado_do_dia(
            selecao_destinos=(
                selecao_destinos
                or SelecaoDestinosBases.completa()
            )
        )

    def iniciar(
        self,
        solicitacoes_autorizadas: bool = False,
        selecao_destinos: SelecaoDestinosBases | None = None
    ) -> bool:
        """
        Inicia a rotina em segundo plano.

        Retorna False quando já existe uma execução em andamento ou
        quando a atualização de Bases do dia já foi concluída.
        """

        rotina = self.checkpoint_service.obter_rotina()
        selecao = (
            selecao_destinos
            or SelecaoDestinosBases.completa()
        )

        if rotina["atualizacao_bases"]:
            return False

        with self._lock:
            if self._executando:
                return False

            self._executando = True
            self._cancelamento.clear()
            self._modo_manual.clear()
            self._modo_manual_disponivel = False
            self._pendencia_atual = None
            self._etapa_atual = None

            self._thread = Thread(
                target=self._executar,
                kwargs={
                    "solicitacoes_autorizadas":
                        bool(solicitacoes_autorizadas),
                    "selecao_destinos": selecao
                },
                name="ArboHub-AtualizacaoBases",
                daemon=True
            )
            self._thread.start()

        return True

    def esta_em_execucao(self) -> bool:
        with self._lock:
            return self._executando

    def modo_manual_esta_disponivel(self) -> bool:
        with self._lock:
            return (
                self._executando
                and self._modo_manual_disponivel
            )

    def modo_manual_esta_ativo(self) -> bool:
        return self._modo_manual.is_set()

    def ativar_modo_manual(self) -> bool:
        """
        Pausa somente as atualizações automáticas da tabela.

        O navegador permanece aberto na thread de trabalho para que
        o usuário acompanhe o SINAN. A rotina pode ser retomada pela
        interface sem criar novas solicitações.
        """

        with self._lock:
            if (
                not self._executando
                or not self._modo_manual_disponivel
            ):
                return False

            self._modo_manual.set()

        self._emitir(
            self.EVENTO_MODO_MANUAL,
            ativo=True,
            mensagem=(
                "Acompanhamento manual ativado. O navegador do "
                "SINAN permanece aberto e as atualizações "
                "automáticas estão pausadas."
            )
        )
        return True

    def retomar_modo_automatico(self) -> bool:
        with self._lock:
            if not self._executando:
                return False

            self._modo_manual.clear()

        self._emitir(
            self.EVENTO_MODO_MANUAL,
            ativo=False,
            mensagem=(
                "Acompanhamento automático retomado."
            )
        )
        return True

    def cancelar(self):
        """
        Solicita cancelamento no próximo ponto seguro.

        Operações atômicas de substituição já iniciadas não são
        interrompidas no meio; o cancelamento é aplicado antes da
        próxima etapa.
        """

        self._cancelamento.set()
        self._modo_manual.clear()

        self._emitir(
            self.EVENTO_STATUS,
            mensagem=(
                "Cancelamento solicitado. "
                "Aguardando um ponto seguro."
            )
        )

    def obter_eventos(self) -> list[dict[str, Any]]:
        eventos: list[dict[str, Any]] = []

        while True:
            try:
                eventos.append(
                    self._eventos.get_nowait()
                )
            except Empty:
                return eventos

    def obter_pendencia_atual(
        self
    ) -> dict[str, object] | None:
        with self._lock:
            if self._pendencia_atual is None:
                return None

            return dict(
                self._pendencia_atual
            )

    def iniciar_correcao_manual(
        self,
        caminho_zip: str
    ) -> bool:
        """
        Inicia, em segundo plano, a validação de um ZIP obtido
        manualmente para o agravo que ficou pendente.

        O arquivo só é aceito após validação de integridade e
        identificação por DENGON ou CHIKON.
        """

        caminho_zip = str(
            caminho_zip
        ).strip()

        if not caminho_zip:
            raise ValueError(
                "Selecione o ZIP que será validado."
            )

        with self._lock:
            if self._executando:
                return False

            if self._pendencia_atual is None:
                raise RuntimeError(
                    "Não existe uma pendência de Bases registrada "
                    "nesta execução."
                )

            self._executando = True
            self._cancelamento.clear()
            self._modo_manual.clear()
            self._modo_manual_disponivel = False
            self._etapa_atual = self.ETAPA_PROCESSAMENTO

            pendencia = dict(
                self._pendencia_atual
            )

            self._thread = Thread(
                target=self._executar_correcao_manual,
                kwargs={
                    "caminho_zip": caminho_zip,
                    "pendencia": pendencia
                },
                name="ArboHub-CorrecaoManualBases",
                daemon=True
            )
            self._thread.start()

        self._emitir(
            self.EVENTO_CORRECAO_MANUAL,
            estado="iniciada",
            mensagem=(
                "Validando o arquivo selecionado para resolver "
                "a pendência."
            )
        )

        return True

    # ------------------------------------------------------------------
    # Execução
    # ------------------------------------------------------------------

    def _executar(
        self,
        solicitacoes_autorizadas: bool,
        selecao_destinos: SelecaoDestinosBases
    ):
        navegador: NavegadorSinan | None = None
        exportacao: ExportacaoBasesDbf | None = None
        try:
            configuracoes_exportacao = (
                self.configuracoes_service
                .carregar()
                ["operacional"]
                ["exportacao"]
            )

            estado = (
                self.rotina_service.avaliar_estado_do_dia(
                    selecao_destinos=selecao_destinos
                )
            )

            self._emitir(
                self.EVENTO_STATUS,
                mensagem=(
                    "Situação do dia verificada. "
                    "Preparando a rotina."
                ),
                estado_dia=estado
            )

            self._verificar_cancelamento()

            if estado["requer_navegador"]:
                self._etapa_atual = self.ETAPA_ACESSO

                self._emitir_etapa(
                    etapa=self._etapa_atual,
                    estado="iniciada",
                    mensagem=(
                        "Abrindo o navegador seguro do SINAN."
                    )
                )

                navegador = NavegadorSinan(
                    permitir_downloads=True,
                    usar_login_automatico=True
                )
                pagina = navegador.abrir()

                if navegador.login_automatico_concluido:
                    self._emitir_etapa(
                        etapa=self._etapa_atual,
                        estado="em_andamento",
                        mensagem=(
                            "Login automático concluído com segurança."
                        )
                    )
                else:
                    self._emitir_etapa(
                        etapa=self._etapa_atual,
                        estado="em_andamento",
                        mensagem=(
                            navegador.obter_mensagem_espera_login()
                        )
                    )

                    self._aguardar_login_cancelavel(
                        navegador=navegador,
                        tempo_limite_segundos=600
                    )

                self._emitir_etapa(
                    etapa=self._etapa_atual,
                    estado="concluida",
                    mensagem=(
                        "Login detectado. A automação pode "
                        "continuar."
                    )
                )

                exportacao = ExportacaoBasesDbf(
                    pagina
                )

            else:
                self._emitir_etapa(
                    etapa=self.ETAPA_ACESSO,
                    estado="ignorada",
                    mensagem=(
                        "Acesso ao SINAN não foi necessário, "
                        "pois os arquivos válidos do dia já "
                        "estão no histórico."
                    )
                )

            self._verificar_cancelamento()

            resultado = (
                self.rotina_service.executar_rotina_selecionada(
                    selecao_destinos=selecao_destinos,
                    exportacao=exportacao,
                    solicitacoes_autorizadas=(
                        solicitacoes_autorizadas
                    ),
                    intervalo_consulta_segundos=(
                        configuracoes_exportacao[
                            "intervalo_consulta_segundos"
                        ]
                    ),
                    tempo_limite_segundos=(
                        configuracoes_exportacao[
                            "tempo_limite_segundos"
                        ]
                    ),
                    aviso_inicial_segundos=(
                        configuracoes_exportacao[
                            "aviso_inicial_segundos"
                        ]
                    ),
                    aviso_lento_segundos=(
                        configuracoes_exportacao[
                            "aviso_lento_segundos"
                        ]
                    ),
                    aviso_reforcado_segundos=(
                        configuracoes_exportacao[
                            "aviso_reforcado_segundos"
                        ]
                    ),
                    ao_evento=(
                        self._receber_evento_rotina
                    ),
                    cancelado=(
                        self._cancelamento.is_set
                    ),
                    modo_manual_ativo=(
                        self._modo_manual.is_set
                    )
                )
            )

            self._verificar_cancelamento()

            if selecao_destinos.esta_completa:
                self.checkpoint_service.marcar_atualizacao_bases()

            self._emitir(
                self.EVENTO_ATUALIZAR
            )
            self._emitir(
                self.EVENTO_CONCLUIDO,
                mensagem=(
                    "Destinos selecionados atualizados com sucesso: "
                    f"{selecao_destinos.resumo()}."
                ),
                resultado=resultado,
                selecao_destinos=selecao_destinos.para_dict(),
                checkpoint_completo=(
                    selecao_destinos.esta_completa
                )
            )

        except ProcessamentoBasesPendente as pendencia:
            self._modo_manual.clear()

            with self._lock:
                self._pendencia_atual = dict(
                    pendencia.dados
                )

            self._emitir(
                self.EVENTO_PENDENTE,
                mensagem=str(pendencia),
                etapa=self.ETAPA_PROCESSAMENTO,
                dados=pendencia.dados
            )

        except (
            RotinaBasesCancelada,
            _AtualizacaoBasesCancelada
        ):
            self._emitir(
                self.EVENTO_CANCELADO,
                mensagem=(
                    "A atualização das bases foi cancelada."
                ),
                etapa=self._etapa_atual
            )

        except Exception as erro:
            if self._cancelamento.is_set():
                self._emitir(
                    self.EVENTO_CANCELADO,
                    mensagem=(
                        "A atualização das bases foi cancelada."
                    ),
                    etapa=self._etapa_atual
                )
            else:
                self._emitir(
                    self.EVENTO_ERRO,
                    mensagem=str(erro),
                    etapa=self._etapa_atual
                )

        finally:
            if navegador is not None:
                navegador.fechar()

            with self._lock:
                self._executando = False
                self._modo_manual_disponivel = False
                self._modo_manual.clear()

    def _executar_correcao_manual(
        self,
        caminho_zip: str,
        pendencia: dict[str, object]
    ):
        try:
            data_referencia_texto = str(
                pendencia.get(
                    "data_referencia",
                    date.today().isoformat()
                )
            )

            try:
                data_referencia = date.fromisoformat(
                    data_referencia_texto
                )
            except ValueError:
                data_referencia = date.today()

            agravos_pendentes = tuple(
                pendencia.get(
                    "agravos_pendentes",
                    ()
                )
            )
            selecao_destinos = SelecaoDestinosBases.de_dict(
                pendencia.get("selecao_destinos")
            )

            resultado = (
                self.rotina_service
                .processar_correcao_manual_selecionada(
                    caminho_zip=caminho_zip,
                    agravos_pendentes=agravos_pendentes,
                    selecao_destinos=selecao_destinos,
                    data_referencia=data_referencia,
                    ao_evento=(
                        self._receber_evento_rotina
                    ),
                    cancelado=(
                        self._cancelamento.is_set
                    )
                )
            )

            self._verificar_cancelamento()

            if resultado["concluida"]:
                if selecao_destinos.esta_completa:
                    self.checkpoint_service.marcar_atualizacao_bases(
                        data_referencia=data_referencia
                    )

                with self._lock:
                    self._pendencia_atual = None

                self._emitir(
                    self.EVENTO_ATUALIZAR
                )
                self._emitir(
                    self.EVENTO_CONCLUIDO,
                    mensagem=(
                        "A pendência foi corrigida, validada e a "
                        "rotina de Bases está completa."
                    ),
                    resultado=resultado,
                    correcao_manual=True,
                    selecao_destinos=(
                        selecao_destinos.para_dict()
                    ),
                    checkpoint_completo=(
                        selecao_destinos.esta_completa
                    )
                )
                return

            pendentes_restantes = tuple(
                resultado.get(
                    "agravos_pendentes",
                    ()
                )
            )
            processados_anteriores = list(
                pendencia.get(
                    "agravos_processados",
                    ()
                )
            )
            rotulo_corrigido = str(
                resultado.get(
                    "rotulo_corrigido",
                    ""
                )
            )

            if (
                rotulo_corrigido
                and rotulo_corrigido
                not in processados_anteriores
            ):
                processados_anteriores.append(
                    rotulo_corrigido
                )

            nova_pendencia = {
                **pendencia,
                "agravos_processados": tuple(
                    processados_anteriores
                ),
                "agravos_pendentes":
                    pendentes_restantes,
                "correcao_manual_disponivel":
                    bool(pendentes_restantes),
                "data_referencia":
                    data_referencia.isoformat(),
                "selecao_destinos": (
                    selecao_destinos.para_dict()
                )
            }

            with self._lock:
                self._pendencia_atual = (
                    nova_pendencia
                )

            self._emitir(
                self.EVENTO_PENDENTE,
                mensagem=(
                    "Um arquivo foi corrigido manualmente, mas "
                    "ainda existe outra exportação pendente."
                ),
                etapa=self.ETAPA_PROCESSAMENTO,
                dados=nova_pendencia
            )

        except (
            RotinaBasesCancelada,
            _AtualizacaoBasesCancelada
        ):
            self._emitir(
                self.EVENTO_CANCELADO,
                mensagem=(
                    "A correção manual foi cancelada."
                ),
                etapa=self.ETAPA_PROCESSAMENTO
            )

        except Exception as erro:
            self._emitir(
                self.EVENTO_ERRO,
                mensagem=str(erro),
                etapa=self.ETAPA_PROCESSAMENTO,
                correcao_manual=True
            )

        finally:
            with self._lock:
                self._executando = False
                self._modo_manual_disponivel = False
                self._modo_manual.clear()

    def _aguardar_login_cancelavel(
        self,
        navegador: NavegadorSinan,
        tempo_limite_segundos: int
    ):
        """
        Aguarda o login sem depender de uma assinatura específica
        de ``aguardar_login_manual`` do navegador.
        """

        pagina = navegador.pagina

        if pagina is None:
            raise RuntimeError(
                "O navegador não possui uma página ativa."
            )

        limite = monotonic() + tempo_limite_segundos

        while monotonic() < limite:
            self._verificar_cancelamento()

            if pagina.is_closed():
                raise RuntimeError(
                    "A janela do navegador foi fechada "
                    "antes da conclusão do login."
                )

            if navegador.login_foi_concluido():
                return

            pagina.wait_for_timeout(500)

        raise TimeoutError(
            "O tempo para realizar o login no SINAN foi encerrado."
        )

    # ------------------------------------------------------------------
    # Conversão de eventos
    # ------------------------------------------------------------------

    def _receber_evento_rotina(
        self,
        evento: EventoRotinaBases
    ):
        """
        Converte o dataclass do coordenador em um evento simples
        para a fila consumida pelo CustomTkinter.
        """

        self._etapa_atual = evento.etapa

        if evento.dados.get("alerta_processamento"):
            permitir_manual = bool(
                evento.dados.get(
                    "permitir_modo_manual",
                    False
                )
            )

            if permitir_manual:
                with self._lock:
                    self._modo_manual_disponivel = True

            self._emitir(
                self.EVENTO_ALERTA_PROCESSAMENTO,
                mensagem=evento.mensagem,
                etapa=evento.etapa,
                dados=evento.dados
            )
            return

        if evento.etapa == RotinaBasesService.ETAPA_LOTE:
            self._emitir(
                self.EVENTO_STATUS,
                mensagem=evento.mensagem,
                dados=evento.dados
            )
            return

        self._emitir_etapa(
            etapa=evento.etapa,
            estado=evento.estado,
            mensagem=evento.mensagem,
            dados=evento.dados
        )

    def _emitir_etapa(
        self,
        etapa: str,
        estado: str,
        mensagem: str,
        dados: dict[str, object] | None = None
    ):
        self._emitir(
            self.EVENTO_ETAPA,
            etapa=etapa,
            estado=estado,
            mensagem=mensagem,
            dados=dados or {}
        )

    def _emitir(
        self,
        tipo: str,
        **dados: Any
    ):
        self._eventos.put(
            {
                "tipo": tipo,
                **dados
            }
        )

    def _verificar_cancelamento(self):
        if self._cancelamento.is_set():
            raise _AtualizacaoBasesCancelada()


class _AtualizacaoBasesCancelada(Exception):
    """Sinal interno de cancelamento controlado."""
