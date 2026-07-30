from __future__ import annotations

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
from app.services.rotina_bases_service import (
    EventoRotinaBases,
    RotinaBasesCancelada,
    RotinaBasesService
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
        rotina_service: RotinaBasesService | None = None
    ):
        self.checkpoint_service = (
            checkpoint_service
            or CheckpointService()
        )
        self.rotina_service = (
            rotina_service
            or RotinaBasesService()
        )

        self._eventos: Queue[dict[str, Any]] = Queue()
        self._cancelamento = Event()
        self._lock = Lock()

        self._thread: Thread | None = None
        self._executando = False
        self._etapa_atual: str | None = None

    # ------------------------------------------------------------------
    # Estado público
    # ------------------------------------------------------------------

    def avaliar_estado_do_dia(self) -> dict[str, object]:
        """
        Informa à interface se haverá novas solicitações, acesso ao
        navegador ou simples reutilização dos arquivos do dia.
        """

        return self.rotina_service.avaliar_estado_do_dia()

    def iniciar(
        self,
        solicitacoes_autorizadas: bool = False
    ) -> bool:
        """
        Inicia a rotina em segundo plano.

        Retorna False quando já existe uma execução em andamento.
        """

        with self._lock:
            if self._executando:
                return False

            self._executando = True
            self._cancelamento.clear()
            self._etapa_atual = None

            self._thread = Thread(
                target=self._executar,
                kwargs={
                    "solicitacoes_autorizadas":
                        bool(solicitacoes_autorizadas)
                },
                name="ArboHub-AtualizacaoBases",
                daemon=True
            )
            self._thread.start()

        return True

    def esta_em_execucao(self) -> bool:
        with self._lock:
            return self._executando

    def cancelar(self):
        """
        Solicita cancelamento no próximo ponto seguro.

        Operações atômicas de substituição já iniciadas não são
        interrompidas no meio; o cancelamento é aplicado antes da
        próxima etapa.
        """

        self._cancelamento.set()

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

    # ------------------------------------------------------------------
    # Execução
    # ------------------------------------------------------------------

    def _executar(
        self,
        solicitacoes_autorizadas: bool
    ):
        navegador: NavegadorSinan | None = None
        exportacao: ExportacaoBasesDbf | None = None
        try:
            estado = (
                self.rotina_service.avaliar_estado_do_dia()
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
                    permitir_downloads=True
                )
                pagina = navegador.abrir()

                self._emitir_etapa(
                    etapa=self._etapa_atual,
                    estado="em_andamento",
                    mensagem=(
                        "Aguardando o login manual no SINAN."
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
                self.rotina_service.executar_rotina_completa(
                    exportacao=exportacao,
                    solicitacoes_autorizadas=(
                        solicitacoes_autorizadas
                    ),
                    usar_historico_existente=True,
                    substituir_historico=False,
                    atualizar_pastas_teste=True,
                    atualizar_bancos_atuais=True,
                    intervalo_consulta_segundos=15,
                    tempo_limite_segundos=1800,
                    ao_evento=(
                        self._receber_evento_rotina
                    ),
                    cancelado=(
                        self._cancelamento.is_set
                    )
                )
            )

            self._verificar_cancelamento()

            self.checkpoint_service.marcar_atualizacao_bases()

            self._emitir(
                self.EVENTO_ATUALIZAR
            )
            self._emitir(
                self.EVENTO_CONCLUIDO,
                mensagem=(
                    "Bases atualizadas com sucesso no histórico, "
                    "nas pastas de teste e em Bancos_Atuais."
                ),
                resultado=resultado
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