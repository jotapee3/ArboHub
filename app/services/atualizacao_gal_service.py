from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from queue import Empty, Queue
from tempfile import TemporaryDirectory
from threading import Event, Lock, Thread
from typing import Any

from app.automation.gal.exportacao_sorotipo import (
    ExportacaoSorotipoGal
)
from app.automation.gal.navegador_gal import NavegadorGal
from app.services.arquivos_gal_service import ArquivosGalService
from app.services.dashboard_service import DashboardService


class AtualizacaoGalService:
    """Executa a rotina semanal do GAL fora da thread da interface."""

    EVENTO_STATUS = "status"
    EVENTO_ETAPA = "etapa"
    EVENTO_CONCLUIDO = "concluido"
    EVENTO_ERRO = "erro"
    EVENTO_CANCELADO = "cancelado"

    ETAPA_ACESSO = "acesso"
    ETAPA_RELATORIO = "relatorio"
    ETAPA_DOWNLOAD = "download"
    ETAPA_HISTORICO = "historico"
    ETAPA_BANCO_ATUAL = "banco_atual"
    ETAPA_TESTE_SORO = "teste_soro"
    ETAPA_FINALIZACAO = "finalizacao"

    def __init__(
        self,
        arquivos_service: ArquivosGalService | None = None,
        dashboard_service: DashboardService | None = None
    ):
        self.arquivos_service = (
            arquivos_service or ArquivosGalService()
        )
        self.dashboard_service = (
            dashboard_service or DashboardService()
        )

        self._eventos: Queue[dict[str, Any]] = Queue()
        self._cancelamento = Event()
        self._lock = Lock()
        self._thread: Thread | None = None
        self._executando = False
        self._etapa_atual: str | None = None

    def iniciar(self) -> bool:
        return self._iniciar_thread(
            alvo=self._executar_automatico,
            nome="ArboHub-AtualizacaoGAL"
        )

    def iniciar_importacao_manual(
        self,
        caminho_arquivo: str | Path
    ) -> bool:
        return self._iniciar_thread(
            alvo=self._executar_importacao_manual,
            nome="ArboHub-ImportacaoGAL",
            kwargs={
                "caminho_arquivo": str(caminho_arquivo)
            }
        )

    def esta_em_execucao(self) -> bool:
        with self._lock:
            return self._executando

    def esta_concluida_hoje(self) -> bool:
        estado = self.dashboard_service.obter_estado_dia(
            date.today()
        )
        return bool(estado["gal"]["concluido"])

    def cancelar(self):
        self._cancelamento.set()
        self._emitir(
            self.EVENTO_STATUS,
            mensagem=(
                "Cancelamento solicitado. Aguardando um ponto seguro."
            )
        )

    def obter_eventos(self) -> list[dict[str, Any]]:
        eventos: list[dict[str, Any]] = []

        while True:
            try:
                eventos.append(self._eventos.get_nowait())
            except Empty:
                return eventos

    def _iniciar_thread(
        self,
        alvo,
        nome: str,
        kwargs: dict[str, object] | None = None
    ) -> bool:
        with self._lock:
            if self._executando:
                return False

            self._executando = True
            self._cancelamento.clear()
            self._etapa_atual = None
            self._thread = Thread(
                target=alvo,
                kwargs=kwargs or {},
                name=nome,
                daemon=True
            )
            self._thread.start()

        return True

    def _executar_automatico(self):
        navegador: NavegadorGal | None = None

        try:
            data_inicio, data_fim = (
                self.arquivos_service.intervalo_semanal()
            )
            self.arquivos_service.validar_destinos()

            self._etapa(
                self.ETAPA_ACESSO,
                "iniciada",
                "Abrindo o portal oficial do GAL."
            )
            navegador = NavegadorGal(permitir_downloads=True)
            navegador.abrir()

            self._etapa(
                self.ETAPA_ACESSO,
                "em_andamento",
                "Faça o login e preencha o CAPTCHA manualmente."
            )
            navegador.aguardar_login_manual(
                tempo_limite_segundos=900,
                cancelado=self._cancelamento.is_set
            )
            self._verificar_cancelamento()
            self._etapa(
                self.ETAPA_ACESSO,
                "concluida",
                "Login detectado com segurança."
            )

            self._etapa(
                self.ETAPA_RELATORIO,
                "iniciada",
                "Abrindo e configurando o relatório epidemiológico."
            )

            with TemporaryDirectory(
                prefix="arbohub_gal_download_"
            ) as pasta_temporaria:
                exportacao = ExportacaoSorotipoGal(navegador)
                arquivo, data_inicio = (
                    self._baixar_ate_diferir_do_csv_vazio(
                        exportacao=exportacao,
                        pasta_temporaria=pasta_temporaria,
                        data_inicio=data_inicio,
                        data_fim=data_fim
                    )
                )

                self._etapa(
                    self.ETAPA_RELATORIO,
                    "concluida",
                    "Relatório preenchido e geração solicitada."
                )
                self._etapa(
                    self.ETAPA_DOWNLOAD,
                    "concluida",
                    f"Arquivo recebido: {arquivo.name}"
                )
                self._verificar_cancelamento()
                resultado = self._organizar_arquivo(
                    arquivo,
                    data_inicio=data_inicio
                )

            self._concluir(resultado)

        except Exception as erro:
            self._tratar_falha(erro)
        finally:
            if navegador is not None:
                navegador.fechar()

            self._finalizar_execucao()

    def _baixar_ate_diferir_do_csv_vazio(
        self,
        exportacao: ExportacaoSorotipoGal,
        pasta_temporaria: str | Path,
        data_inicio: date,
        data_fim: date
    ) -> tuple[Path, date]:
        while True:
            self._verificar_cancelamento()
            arquivo = exportacao.baixar(
                pasta_temporaria=pasta_temporaria,
                data_inicio=data_inicio,
                data_fim=data_fim,
                cancelado=self._cancelamento.is_set,
                ao_status=self._atualizar_status_relatorio
            )

            if not self.arquivos_service.corresponde_ao_csv_vazio(
                arquivo
            ):
                return arquivo, data_inicio

            data_inicio -= timedelta(days=7)
            self._emitir(
                self.EVENTO_STATUS,
                mensagem=(
                    "O arquivo recebido corresponde ao modelo vazio. "
                    "Repetindo a geração com início em "
                    f"{data_inicio.strftime('%d/%m/%Y')} e mantendo "
                    f"o fim em {data_fim.strftime('%d/%m/%Y')}."
                ),
                etapa=self.ETAPA_RELATORIO
            )

    def _executar_importacao_manual(self, caminho_arquivo: str):
        try:
            self._etapa(
                self.ETAPA_ACESSO,
                "ignorada",
                "Login e geração realizados manualmente."
            )
            self._etapa(
                self.ETAPA_RELATORIO,
                "ignorada",
                "Usando o relatório selecionado pelo usuário."
            )
            self._etapa(
                self.ETAPA_DOWNLOAD,
                "concluida",
                f"Arquivo selecionado: {Path(caminho_arquivo).name}"
            )
            resultado = self._organizar_arquivo(
                Path(caminho_arquivo)
            )
            self._concluir(resultado)
        except Exception as erro:
            self._tratar_falha(erro)
        finally:
            self._finalizar_execucao()

    def _organizar_arquivo(
        self,
        arquivo: Path,
        data_inicio: date | None = None
    ) -> dict[str, object]:
        self._verificar_cancelamento()
        self._etapa(
            self.ETAPA_HISTORICO,
            "iniciada",
            "Preservando o arquivo no histórico mensal do GAL."
        )
        resultado = self.arquivos_service.processar_download(
            arquivo,
            data_inicio=data_inicio
        )
        self._etapa(
            self.ETAPA_HISTORICO,
            "concluida",
            "ZIP semanal atualizado com o nome da segunda-feira final."
        )
        self._etapa(
            self.ETAPA_BANCO_ATUAL,
            "concluida",
            "Banco_Atual atualizado como gal_sorotipo."
        )
        self._etapa(
            self.ETAPA_TESTE_SORO,
            "concluida",
            "TesteSORO atualizado como gal_sorotipo-TESTE."
        )
        return resultado

    def _concluir(self, resultado: dict[str, object]):
        self._verificar_cancelamento()
        self.dashboard_service.marcar_gal_concluido()
        self._etapa(
            self.ETAPA_FINALIZACAO,
            "concluida",
            "Atualização semanal do GAL concluída."
        )
        self._emitir(
            self.EVENTO_CONCLUIDO,
            mensagem=(
                "O histórico, o Banco_Atual e o TesteSORO "
                "foram atualizados."
            ),
            resultado=resultado
        )

    def _atualizar_status_relatorio(self, mensagem: str):
        self._emitir(
            self.EVENTO_STATUS,
            mensagem=mensagem,
            etapa=self.ETAPA_RELATORIO
        )

    def _tratar_falha(self, erro: Exception):
        if self._cancelamento.is_set():
            self._emitir(
                self.EVENTO_CANCELADO,
                mensagem="A atualização do GAL foi cancelada.",
                etapa=self._etapa_atual
            )
            return

        self._emitir(
            self.EVENTO_ERRO,
            mensagem=str(erro),
            etapa=self._etapa_atual
        )

    def _etapa(
        self,
        etapa: str,
        estado: str,
        mensagem: str
    ):
        self._etapa_atual = etapa
        self._emitir(
            self.EVENTO_ETAPA,
            etapa=etapa,
            estado=estado,
            mensagem=mensagem
        )

    def _emitir(self, tipo: str, **dados: Any):
        self._eventos.put({"tipo": tipo, **dados})

    def _verificar_cancelamento(self):
        if self._cancelamento.is_set():
            raise _AtualizacaoGalCancelada()

    def _finalizar_execucao(self):
        with self._lock:
            self._executando = False


class _AtualizacaoGalCancelada(Exception):
    """Sinal interno de cancelamento cooperativo."""
