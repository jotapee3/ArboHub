from __future__ import annotations

from queue import Empty, Queue
from threading import Event, Lock, Thread
from typing import Any

from app.automation.sinan.navegador_sinan import NavegadorSinan
from app.automation.sinan.verificacao_obitos import VerificacaoObitos
from app.services.checkpoint_service import CheckpointService


class ConsultaObitosService:
    """
    Orquestra a consulta de Dengue e Chikungunya fora da interface.

    Toda a automação do Playwright é criada e executada na mesma
    thread de trabalho. A interface recebe eventos por uma fila e
    continua responsiva durante login, carregamentos e pesquisas.
    """

    EVENTO_STATUS = "status"
    EVENTO_ATUALIZAR = "atualizar"
    EVENTO_CONFIRMAR = "confirmar"
    EVENTO_CONCLUIDO = "concluido"
    EVENTO_ERRO = "erro"
    EVENTO_CANCELADO = "cancelado"

    def __init__(
        self,
        checkpoint_service: CheckpointService | None = None
    ):
        self.checkpoint_service = (
            checkpoint_service or CheckpointService()
        )

        self._eventos: Queue[dict[str, Any]] = Queue()
        self._cancelamento = Event()
        self._lock = Lock()

        self._thread: Thread | None = None
        self._executando = False

        self._confirmacao_evento: Event | None = None
        self._confirmacao_resultado: dict[str, Any] | None = None
        self._confirmacao_agravo: str | None = None

    # ------------------------------------------------------------------
    # Controle público
    # ------------------------------------------------------------------

    def iniciar(self) -> bool:
        """
        Inicia a rotina em uma thread separada.

        Retorna False quando já existe uma execução em andamento.
        """

        with self._lock:
            if self._executando:
                return False

            self._executando = True
            self._cancelamento.clear()
            self._confirmacao_evento = None
            self._confirmacao_resultado = None
            self._confirmacao_agravo = None

            self._thread = Thread(
                target=self._executar_fluxo,
                name="ArboHub-ConsultaObitos",
                daemon=True
            )
            self._thread.start()

        return True

    def esta_em_execucao(self) -> bool:
        with self._lock:
            return self._executando

    def cancelar(self):
        """
        Solicita encerramento seguro no próximo ponto de controle.
        """

        self._cancelamento.set()

        with self._lock:
            evento = self._confirmacao_evento

        if evento is not None:
            evento.set()

    def responder_confirmacao(
        self,
        resultado: dict[str, Any]
    ):
        """
        Entrega à thread de automação a resposta da janela nativa.
        """

        with self._lock:
            evento = self._confirmacao_evento

            if evento is None:
                raise RuntimeError(
                    "Não existe confirmação pendente."
                )

            self._confirmacao_resultado = dict(resultado)
            evento.set()

    def obter_eventos(self) -> list[dict[str, Any]]:
        """
        Retira todos os eventos atualmente disponíveis na fila.
        """

        eventos: list[dict[str, Any]] = []

        while True:
            try:
                eventos.append(
                    self._eventos.get_nowait()
                )
            except Empty:
                return eventos

    # ------------------------------------------------------------------
    # Fluxo interno
    # ------------------------------------------------------------------

    def _executar_fluxo(self):
        navegador = NavegadorSinan()
        agravo_atual: str | None = None

        evento_final = self.EVENTO_CONCLUIDO
        mensagem_final = (
            "Verificação de Dengue e Chikungunya "
            "concluída com sucesso."
        )

        try:
            self._emitir_status(
                "Abrindo o navegador do SINAN..."
            )

            pagina = navegador.abrir()

            self._verificar_cancelamento()

            self._emitir_status(
                "Aguardando o login manual no SINAN."
            )

            navegador.aguardar_login_manual(
                tempo_limite_segundos=600,
                cancelado=self._cancelamento.is_set
            )

            self._verificar_cancelamento()

            verificacao = VerificacaoObitos(
                pagina
            )

            self._emitir_status(
                "Abrindo Consulta → Notificação Individual..."
            )

            verificacao.abrir_notificacao_individual()

            # --------------------------------------------------
            # Dengue
            # --------------------------------------------------

            agravo_atual = CheckpointService.AGRAVO_DENGUE

            self.checkpoint_service.marcar_obito_iniciado(
                agravo_atual
            )
            self._emitir_atualizacao()
            self._emitir_status(
                "Executando a consulta de Dengue..."
            )

            verificacao.executar_consulta_por_agravo(
                agravo="Dengue"
            )

            self._verificar_cancelamento()

            self.checkpoint_service.marcar_obito_aguardando_conferencia(
                agravo_atual
            )
            self._emitir_atualizacao()
            self._emitir_status(
                "Dengue concluída. Aguardando conferência humana."
            )

            confirmacao_dengue = self._aguardar_confirmacao(
                agravo="Dengue",
                acao_seguinte="consultar Chikungunya"
            )

            self.checkpoint_service.marcar_obito_concluido(
                agravo=agravo_atual,
                resultado_comparacao=(
                    confirmacao_dengue[
                        "resultado_comparacao"
                    ]
                ),
                observacao=confirmacao_dengue[
                    "observacao"
                ]
            )
            self._emitir_atualizacao()

            self._verificar_cancelamento()

            # --------------------------------------------------
            # Chikungunya
            # --------------------------------------------------

            agravo_atual = (
                CheckpointService.AGRAVO_CHIKUNGUNYA
            )

            self.checkpoint_service.marcar_obito_iniciado(
                agravo_atual
            )
            self._emitir_atualizacao()
            self._emitir_status(
                "Alterando o agravo para Chikungunya..."
            )

            verificacao.trocar_agravo_e_pesquisar(
                agravo="Chikungunya"
            )

            self._verificar_cancelamento()

            self.checkpoint_service.marcar_obito_aguardando_conferencia(
                agravo_atual
            )
            self._emitir_atualizacao()
            self._emitir_status(
                "Chikungunya concluída. "
                "Aguardando conferência humana."
            )

            confirmacao_chikungunya = (
                self._aguardar_confirmacao(
                    agravo="Chikungunya",
                    acao_seguinte="finalizar"
                )
            )

            self.checkpoint_service.marcar_obito_concluido(
                agravo=agravo_atual,
                resultado_comparacao=(
                    confirmacao_chikungunya[
                        "resultado_comparacao"
                    ]
                ),
                observacao=(
                    confirmacao_chikungunya[
                        "observacao"
                    ]
                )
            )
            self._emitir_atualizacao()

        except _FluxoCancelado:
            evento_final = self.EVENTO_CANCELADO
            mensagem_final = "A verificação foi cancelada."

        except Exception as erro:
            if self._cancelamento.is_set():
                evento_final = self.EVENTO_CANCELADO
                mensagem_final = "A verificação foi cancelada."
            else:
                evento_final = self.EVENTO_ERRO
                mensagem_final = str(erro)

                if agravo_atual is not None:
                    try:
                        self.checkpoint_service.marcar_obito_erro(
                            agravo_atual
                        )
                        self._emitir_atualizacao()
                    except Exception:
                        pass

        finally:
            navegador.fechar()

            with self._lock:
                self._executando = False
                self._confirmacao_evento = None
                self._confirmacao_resultado = None
                self._confirmacao_agravo = None

            self._emitir(
                evento_final,
                mensagem=mensagem_final
            )

    def _aguardar_confirmacao(
        self,
        agravo: str,
        acao_seguinte: str
    ) -> dict[str, Any]:
        evento = Event()

        with self._lock:
            self._confirmacao_evento = evento
            self._confirmacao_resultado = None
            self._confirmacao_agravo = agravo

        self._emitir(
            self.EVENTO_CONFIRMAR,
            agravo=agravo,
            acao_seguinte=acao_seguinte
        )

        while not evento.wait(0.2):
            self._verificar_cancelamento()

        self._verificar_cancelamento()

        with self._lock:
            resultado = self._confirmacao_resultado
            self._confirmacao_evento = None
            self._confirmacao_resultado = None
            self._confirmacao_agravo = None

        if not resultado or not resultado.get("confirmado"):
            raise RuntimeError(
                f"A conferência de {agravo} não foi confirmada."
            )

        return resultado

    # ------------------------------------------------------------------
    # Eventos e validações
    # ------------------------------------------------------------------

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

    def _emitir_status(
        self,
        mensagem: str
    ):
        self._emitir(
            self.EVENTO_STATUS,
            mensagem=mensagem
        )

    def _emitir_atualizacao(self):
        self._emitir(
            self.EVENTO_ATUALIZAR
        )

    def _verificar_cancelamento(self):
        if self._cancelamento.is_set():
            raise _FluxoCancelado()


class _FluxoCancelado(Exception):
    """Sinal interno de cancelamento controlado."""