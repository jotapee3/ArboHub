from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from time import monotonic
from pathlib import Path
from typing import Callable

from app.automation.sinan.exportacao_bases import (
    ExportacaoBasesDbf
)
from app.services.arquivos_exportacao_dbf_service import (
    ArquivosExportacaoDbfService
)
from app.services.exportacao_dbf_service import (
    ExportacaoDbfService
)


class RotinaBasesCancelada(RuntimeError):
    """Indica cancelamento solicitado pelo usuário."""


class ProcessamentoBasesPendente(RuntimeError):
    """
    Indica que o limite de acompanhamento foi atingido sem que
    as duas exportações ficassem disponíveis.
    """

    def __init__(
        self,
        mensagem: str,
        dados: dict[str, object]
    ):
        super().__init__(mensagem)
        self.dados = dados


@dataclass(frozen=True)
class EventoRotinaBases:
    """
    Evento operacional emitido durante a rotina.

    Os eventos contêm apenas informações de execução, como etapa,
    estado, números de solicitação e caminhos de arquivos. Nenhum
    registro interno dos DBFs é incluído.
    """

    etapa: str
    estado: str
    mensagem: str
    dados: dict[str, object] = field(
        default_factory=dict
    )


CallbackEvento = Callable[
    [EventoRotinaBases],
    None
]
CallbackCancelamento = Callable[
    [],
    bool
]


class RotinaBasesService:
    """
    Coordena a rotina diária completa das bases DBF.

    A rotina:
    - reutiliza solicitações completas já salvas no dia;
    - retoma com segurança um lote parcial;
    - cria Dengue e Chikungunya quando ainda não existem;
    - captura e salva cada número diretamente da tela;
    - recupera o lote completo do dia;
    - reutiliza ZIPs históricos válidos, quando já existem;
    - caso contrário, acompanha o processamento e baixa a dupla;
    - arquiva os ZIPs no histórico;
    - valida a extração;
    - atualiza os destinos configurados de Dengue e Chikungunya;
    - atualiza Documents\\SINAN\\Bancos_Atuais.

    O serviço foi separado da interface para permitir:
    - teste por terminal;
    - execução futura em thread;
    - atualização da linha do tempo da aba Bases;
    - cancelamento entre etapas;
    - reaproveitamento das mesmas regras de segurança.
    """

    ETAPA_SOLICITACOES = "solicitacoes"
    ETAPA_LOTE = "lote"
    ETAPA_HISTORICO = "historico"
    ETAPA_PROCESSAMENTO = "processamento"
    ETAPA_DOWNLOAD = "download"
    ETAPA_EXTRACAO = "extracao"
    ETAPA_PASTAS_TESTE = "pastas_teste"
    ETAPA_BANCOS_ATUAIS = "bancos_atuais"
    ETAPA_FINALIZACAO = "finalizacao"

    ESTADO_INICIADA = "iniciada"
    ESTADO_EM_ANDAMENTO = "em_andamento"
    ESTADO_CONCLUIDA = "concluida"
    ESTADO_IGNORADA = "ignorada"

    def __init__(
        self,
        registro_service: ExportacaoDbfService | None = None,
        arquivos_service:
            ArquivosExportacaoDbfService | None = None
    ):
        self.registro_service = (
            registro_service
            or ExportacaoDbfService()
        )
        self.arquivos_service = (
            arquivos_service
            or ArquivosExportacaoDbfService()
        )

    def avaliar_estado_do_dia(
        self,
        data_referencia: date | None = None
    ) -> dict[str, object]:
        """
        Avalia o que será necessário antes de abrir o navegador.

        O navegador só é necessário quando:
        - ainda falta uma das solicitações do dia; ou
        - os ZIPs históricos do dia ainda não estão completos.
        """

        data_referencia = (
            data_referencia
            or date.today()
        )

        self.arquivos_service.validar_destinos_operacionais(
            incluir_historico=True,
            incluir_pastas_teste=True,
            incluir_bancos_atuais=True
        )

        lote_completo = (
            self.registro_service
            .obter_lote_completo_do_dia(
                data_referencia=data_referencia
            )
        )

        lote_parcial = None

        if lote_completo is None:
            lote_parcial = (
                self.registro_service
                .obter_lote_parcial_do_dia(
                    data_referencia=data_referencia
                )
            )

        caminhos_historico = {
            "dengue":
                self.arquivos_service.caminho_historico(
                    agravo=(
                        ArquivosExportacaoDbfService
                        .AGRAVO_DENGUE
                    ),
                    data_referencia=data_referencia
                ),
            "chikungunya":
                self.arquivos_service.caminho_historico(
                    agravo=(
                        ArquivosExportacaoDbfService
                        .AGRAVO_CHIKUNGUNYA
                    ),
                    data_referencia=data_referencia
                )
        }

        historico_completo = all(
            caminho.exists()
            for caminho in caminhos_historico.values()
        )

        solicitacoes_faltantes = []

        if lote_completo is None:
            if (
                lote_parcial is None
                or lote_parcial["dengue"] is None
            ):
                solicitacoes_faltantes.append(
                    ExportacaoDbfService.AGRAVO_DENGUE
                )

            if (
                lote_parcial is None
                or lote_parcial["chikungunya"] is None
            ):
                solicitacoes_faltantes.append(
                    ExportacaoDbfService
                    .AGRAVO_CHIKUNGUNYA
                )

        requer_novas_solicitacoes = bool(
            solicitacoes_faltantes
        )

        return {
            "data_referencia":
                data_referencia.isoformat(),
            "lote_completo": lote_completo,
            "lote_parcial": lote_parcial,
            "solicitacoes_faltantes":
                solicitacoes_faltantes,
            "requer_novas_solicitacoes":
                requer_novas_solicitacoes,
            "historico": caminhos_historico,
            "historico_completo":
                historico_completo,
            "requer_navegador": (
                requer_novas_solicitacoes
                or not historico_completo
            )
        }

    def garantir_solicitacoes_do_dia(
        self,
        exportacao: ExportacaoBasesDbf | None,
        data_referencia: date | None = None,
        solicitacoes_autorizadas: bool = False,
        ao_evento: CallbackEvento | None = None,
        cancelado: CallbackCancelamento | None = None
    ) -> dict[str, object]:
        """
        Garante um par completo de solicitações para o dia.

        Comportamento seguro:
        - se o par completo já existe, não solicita novamente;
        - se somente Dengue existe, cria apenas Chikungunya;
        - se somente Chikungunya existe, cria apenas Dengue;
        - se nenhuma existe, cria as duas;
        - cada número é salvo imediatamente após ser capturado.

        Novas solicitações só são enviadas quando
        ``solicitacoes_autorizadas`` é verdadeiro.
        """

        data_referencia = (
            data_referencia
            or date.today()
        )

        self._verificar_cancelamento(
            cancelado
        )

        lote_completo = (
            self.registro_service
            .obter_lote_completo_do_dia(
                data_referencia=data_referencia
            )
        )

        if lote_completo is not None:
            self._emitir(
                ao_evento=ao_evento,
                etapa=self.ETAPA_SOLICITACOES,
                estado=self.ESTADO_IGNORADA,
                mensagem=(
                    "As solicitações de Dengue e "
                    "Chikungunya já existem para o dia. "
                    "Nenhuma nova solicitação foi criada."
                ),
                dados={
                    "numero_dengue":
                        lote_completo[
                            "dengue"
                        ]["numero_solicitacao"],
                    "numero_chikungunya":
                        lote_completo[
                            "chikungunya"
                        ]["numero_solicitacao"]
                }
            )

            return {
                "lote": lote_completo,
                "reutilizado": True,
                "retomado_parcial": False,
                "novas_solicitacoes": []
            }

        lote_parcial = (
            self.registro_service
            .obter_lote_parcial_do_dia(
                data_referencia=data_referencia
            )
        )

        dengue_existente = (
            lote_parcial["dengue"]
            if lote_parcial is not None
            else None
        )
        chikungunya_existente = (
            lote_parcial["chikungunya"]
            if lote_parcial is not None
            else None
        )

        faltantes = []

        if dengue_existente is None:
            faltantes.append(
                ExportacaoDbfService.AGRAVO_DENGUE
            )

        if chikungunya_existente is None:
            faltantes.append(
                ExportacaoDbfService
                .AGRAVO_CHIKUNGUNYA
            )

        if not solicitacoes_autorizadas:
            raise PermissionError(
                "Há solicitações reais pendentes para hoje: "
                f"{', '.join(faltantes)}. "
                "A execução não foi autorizada."
            )

        if exportacao is None:
            raise RuntimeError(
                "É necessário um navegador autenticado no SINAN "
                "para criar as solicitações pendentes."
            )

        lote_id = (
            lote_parcial["lote_id"]
            if lote_parcial is not None
            else None
        )
        novas_solicitacoes = []

        self._emitir(
            ao_evento=ao_evento,
            etapa=self.ETAPA_SOLICITACOES,
            estado=self.ESTADO_INICIADA,
            mensagem=(
                "Preparando as solicitações DBF do dia."
            ),
            dados={
                "retomando_lote_parcial":
                    lote_parcial is not None,
                "faltantes": tuple(faltantes)
            }
        )

        exportacao.abrir_solicitacao_exportacao_dbf()

        numero_dengue = (
            str(
                dengue_existente[
                    "numero_solicitacao"
                ]
            )
            if dengue_existente is not None
            else None
        )

        if numero_dengue is None:
            self._verificar_cancelamento(
                cancelado
            )

            self._emitir(
                ao_evento=ao_evento,
                etapa=self.ETAPA_SOLICITACOES,
                estado=self.ESTADO_EM_ANDAMENTO,
                mensagem=(
                    "Preparando o formulário de Dengue."
                )
            )

            preparacao_dengue = (
                exportacao.preparar_primeira_exportacao(
                    data_referencia=data_referencia
                )
            )

            if not preparacao_dengue[
                "checkpoint_marcado"
            ]:
                raise RuntimeError(
                    "O checkbox de identificação do paciente "
                    "não permaneceu marcado para Dengue."
                )

            self._verificar_cancelamento(
                cancelado
            )

            resultado_dengue = (
                exportacao
                .solicitar_exportacao_dengue()
            )
            numero_dengue = str(
                resultado_dengue[
                    "numero_solicitacao"
                ]
            )

            if lote_id is None:
                lote_id = (
                    self.registro_service.criar_lote(
                        data_referencia=data_referencia
                    )
                )

            self.registro_service.salvar_solicitacao(
                lote_id=lote_id,
                agravo=(
                    ExportacaoDbfService.AGRAVO_DENGUE
                ),
                numero_solicitacao=numero_dengue
            )

            novas_solicitacoes.append(
                ExportacaoDbfService.AGRAVO_DENGUE
            )

            self._emitir(
                ao_evento=ao_evento,
                etapa=self.ETAPA_SOLICITACOES,
                estado=self.ESTADO_EM_ANDAMENTO,
                mensagem=(
                    "Solicitação de Dengue criada e salva."
                ),
                dados={
                    "numero_solicitacao":
                        numero_dengue,
                    "lote_id": lote_id
                }
            )

        else:
            self._emitir(
                ao_evento=ao_evento,
                etapa=self.ETAPA_SOLICITACOES,
                estado=self.ESTADO_IGNORADA,
                mensagem=(
                    "A solicitação de Dengue já estava salva. "
                    "Ela não foi criada novamente."
                ),
                dados={
                    "numero_solicitacao":
                        numero_dengue
                }
            )

        if chikungunya_existente is None:
            self._verificar_cancelamento(
                cancelado
            )

            self._emitir(
                ao_evento=ao_evento,
                etapa=self.ETAPA_SOLICITACOES,
                estado=self.ESTADO_EM_ANDAMENTO,
                mensagem=(
                    "Preparando o formulário de Chikungunya."
                )
            )

            preparacao_chikungunya = (
                exportacao
                .preparar_exportacao_chikungunya(
                    data_referencia=data_referencia
                )
            )

            if not preparacao_chikungunya[
                "checkpoint_marcado"
            ]:
                raise RuntimeError(
                    "O checkbox de identificação do paciente "
                    "não permaneceu marcado para Chikungunya."
                )

            self._verificar_cancelamento(
                cancelado
            )

            resultado_chikungunya = (
                exportacao
                .solicitar_exportacao_chikungunya(
                    numero_solicitacao_dengue=(
                        numero_dengue
                    )
                )
            )
            numero_chikungunya = str(
                resultado_chikungunya[
                    "numero_solicitacao"
                ]
            )

            if lote_id is None:
                lote_id = (
                    self.registro_service.criar_lote(
                        data_referencia=data_referencia
                    )
                )

            self.registro_service.salvar_solicitacao(
                lote_id=lote_id,
                agravo=(
                    ExportacaoDbfService
                    .AGRAVO_CHIKUNGUNYA
                ),
                numero_solicitacao=(
                    numero_chikungunya
                )
            )

            novas_solicitacoes.append(
                ExportacaoDbfService
                .AGRAVO_CHIKUNGUNYA
            )

            self._emitir(
                ao_evento=ao_evento,
                etapa=self.ETAPA_SOLICITACOES,
                estado=self.ESTADO_EM_ANDAMENTO,
                mensagem=(
                    "Solicitação de Chikungunya criada e salva."
                ),
                dados={
                    "numero_solicitacao":
                        numero_chikungunya,
                    "lote_id": lote_id
                }
            )

        else:
            numero_chikungunya = str(
                chikungunya_existente[
                    "numero_solicitacao"
                ]
            )

            self._emitir(
                ao_evento=ao_evento,
                etapa=self.ETAPA_SOLICITACOES,
                estado=self.ESTADO_IGNORADA,
                mensagem=(
                    "A solicitação de Chikungunya já estava "
                    "salva. Ela não foi criada novamente."
                ),
                dados={
                    "numero_solicitacao":
                        numero_chikungunya
                }
            )

        lote_completo = (
            self.registro_service
            .obter_lote_completo_do_dia(
                data_referencia=data_referencia
            )
        )

        if lote_completo is None:
            raise RuntimeError(
                "As solicitações foram processadas, mas o lote "
                "completo do dia não pôde ser recuperado."
            )

        self._emitir(
            ao_evento=ao_evento,
            etapa=self.ETAPA_SOLICITACOES,
            estado=self.ESTADO_CONCLUIDA,
            mensagem=(
                "O par diário de solicitações está completo."
            ),
            dados={
                "numero_dengue":
                    lote_completo[
                        "dengue"
                    ]["numero_solicitacao"],
                "numero_chikungunya":
                    lote_completo[
                        "chikungunya"
                    ]["numero_solicitacao"],
                "novas_solicitacoes":
                    tuple(novas_solicitacoes)
            }
        )

        return {
            "lote": lote_completo,
            "reutilizado": False,
            "retomado_parcial":
                lote_parcial is not None,
            "novas_solicitacoes":
                novas_solicitacoes
        }

    def executar_rotina_completa(
        self,
        exportacao: ExportacaoBasesDbf | None = None,
        data_referencia: date | None = None,
        solicitacoes_autorizadas: bool = False,
        usar_historico_existente: bool = True,
        substituir_historico: bool = False,
        atualizar_pastas_teste: bool = True,
        atualizar_bancos_atuais: bool = True,
        intervalo_consulta_segundos: float = 15,
        tempo_limite_segundos: float = 1200,
        aviso_inicial_segundos: float = 60,
        aviso_lento_segundos: float = 300,
        aviso_reforcado_segundos: float = 600,
        ao_evento: CallbackEvento | None = None,
        cancelado: CallbackCancelamento | None = None,
        modo_manual_ativo: CallbackCancelamento | None = None
    ) -> dict[str, object]:
        """
        Executa solicitações e processamento em uma única rotina.

        Por padrão, solicitações completas e ZIPs válidos do dia
        são reutilizados. Isso torna a operação retomável e evita
        duplicação acidental.
        """

        data_referencia = (
            data_referencia
            or date.today()
        )

        self.arquivos_service.validar_destinos_operacionais(
            incluir_historico=True,
            incluir_pastas_teste=atualizar_pastas_teste,
            incluir_bancos_atuais=atualizar_bancos_atuais
        )

        self._validar_tempos_acompanhamento(
            intervalo_consulta_segundos=(
                intervalo_consulta_segundos
            ),
            aviso_inicial_segundos=(
                aviso_inicial_segundos
            ),
            aviso_lento_segundos=(
                aviso_lento_segundos
            ),
            aviso_reforcado_segundos=(
                aviso_reforcado_segundos
            ),
            tempo_limite_segundos=(
                tempo_limite_segundos
            )
        )

        resultado_solicitacoes = (
            self.garantir_solicitacoes_do_dia(
                exportacao=exportacao,
                data_referencia=data_referencia,
                solicitacoes_autorizadas=(
                    solicitacoes_autorizadas
                ),
                ao_evento=ao_evento,
                cancelado=cancelado
            )
        )

        resultado_pos = self.executar_pos_solicitacao(
            exportacao=exportacao,
            data_referencia=data_referencia,
            usar_historico_existente=(
                usar_historico_existente
            ),
            substituir_historico=(
                substituir_historico
            ),
            atualizar_pastas_teste=(
                atualizar_pastas_teste
            ),
            atualizar_bancos_atuais=(
                atualizar_bancos_atuais
            ),
            intervalo_consulta_segundos=(
                intervalo_consulta_segundos
            ),
            tempo_limite_segundos=(
                tempo_limite_segundos
            ),
            aviso_inicial_segundos=(
                aviso_inicial_segundos
            ),
            aviso_lento_segundos=(
                aviso_lento_segundos
            ),
            aviso_reforcado_segundos=(
                aviso_reforcado_segundos
            ),
            ao_evento=ao_evento,
            cancelado=cancelado,
            modo_manual_ativo=modo_manual_ativo
        )

        resultado_pos["solicitacoes"] = (
            resultado_solicitacoes
        )

        return resultado_pos

    def executar_pos_solicitacao(
        self,
        exportacao: ExportacaoBasesDbf | None = None,
        data_referencia: date | None = None,
        usar_historico_existente: bool = True,
        substituir_historico: bool = False,
        atualizar_pastas_teste: bool = True,
        atualizar_bancos_atuais: bool = True,
        intervalo_consulta_segundos: float = 15,
        tempo_limite_segundos: float = 1200,
        aviso_inicial_segundos: float = 60,
        aviso_lento_segundos: float = 300,
        aviso_reforcado_segundos: float = 600,
        ao_evento: CallbackEvento | None = None,
        cancelado: CallbackCancelamento | None = None,
        modo_manual_ativo: CallbackCancelamento | None = None
    ) -> dict[str, object]:
        """
        Executa todo o fluxo posterior à criação das solicitações.

        ``exportacao`` pode ser ``None`` quando os dois ZIPs do dia
        já estão no histórico e foram validados. Se for necessário
        acompanhar ou baixar arquivos, uma instância conectada à
        página autenticada do SINAN é obrigatória.
        """

        data_referencia = (
            data_referencia
            or date.today()
        )

        self.arquivos_service.validar_destinos_operacionais(
            incluir_historico=True,
            incluir_pastas_teste=atualizar_pastas_teste,
            incluir_bancos_atuais=atualizar_bancos_atuais
        )

        self._validar_tempos_acompanhamento(
            intervalo_consulta_segundos=(
                intervalo_consulta_segundos
            ),
            aviso_inicial_segundos=(
                aviso_inicial_segundos
            ),
            aviso_lento_segundos=(
                aviso_lento_segundos
            ),
            aviso_reforcado_segundos=(
                aviso_reforcado_segundos
            ),
            tempo_limite_segundos=(
                tempo_limite_segundos
            )
        )

        self._verificar_cancelamento(
            cancelado
        )

        self._emitir(
            ao_evento=ao_evento,
            etapa=self.ETAPA_LOTE,
            estado=self.ESTADO_INICIADA,
            mensagem=(
                "Localizando as solicitações de Dengue e "
                "Chikungunya do dia."
            )
        )

        lote = (
            self.registro_service
            .obter_lote_completo_do_dia(
                data_referencia=data_referencia
            )
        )

        if lote is None:
            raise RuntimeError(
                "Nenhum lote completo de Dengue e "
                "Chikungunya foi encontrado para "
                f"{data_referencia.strftime('%d/%m/%Y')}."
            )

        numero_dengue = str(
            lote["dengue"]["numero_solicitacao"]
        )
        numero_chikungunya = str(
            lote["chikungunya"]["numero_solicitacao"]
        )

        self._emitir(
            ao_evento=ao_evento,
            etapa=self.ETAPA_LOTE,
            estado=self.ESTADO_CONCLUIDA,
            mensagem=(
                "Solicitações do dia localizadas."
            ),
            dados={
                "lote_id": lote["lote_id"],
                "data_referencia":
                    lote["data_referencia"],
                "numero_dengue": numero_dengue,
                "numero_chikungunya":
                    numero_chikungunya
            }
        )

        self._verificar_cancelamento(
            cancelado
        )

        caminhos_historico = {
            "dengue":
                self.arquivos_service.caminho_historico(
                    agravo=(
                        ArquivosExportacaoDbfService
                        .AGRAVO_DENGUE
                    ),
                    data_referencia=data_referencia
                ),
            "chikungunya":
                self.arquivos_service.caminho_historico(
                    agravo=(
                        ArquivosExportacaoDbfService
                        .AGRAVO_CHIKUNGUNYA
                    ),
                    data_referencia=data_referencia
                )
        }

        historico_completo = all(
            caminho.exists()
            for caminho in caminhos_historico.values()
        )

        resultado_historico: dict[str, object]

        if (
            usar_historico_existente
            and historico_completo
        ):
            self._emitir(
                ao_evento=ao_evento,
                etapa=self.ETAPA_HISTORICO,
                estado=self.ESTADO_EM_ANDAMENTO,
                mensagem=(
                    "Os dois ZIPs do dia já existem no "
                    "histórico. Validando antes de reutilizar."
                ),
                dados={
                    "dengue":
                        caminhos_historico["dengue"],
                    "chikungunya":
                        caminhos_historico[
                            "chikungunya"
                        ]
                }
            )

            validacao_historico = (
                self.arquivos_service
                .validar_extracao_historico(
                    data_referencia=data_referencia
                )
            )

            resultado_historico = {
                "reutilizado": True,
                "download_realizado": False,
                "dengue":
                    caminhos_historico["dengue"],
                "chikungunya":
                    caminhos_historico[
                        "chikungunya"
                    ],
                "validacao": validacao_historico
            }

            self._emitir(
                ao_evento=ao_evento,
                etapa=self.ETAPA_DOWNLOAD,
                estado=self.ESTADO_IGNORADA,
                mensagem=(
                    "Download ignorado porque a dupla histórica "
                    "do dia já está válida."
                )
            )

            self._emitir(
                ao_evento=ao_evento,
                etapa=self.ETAPA_HISTORICO,
                estado=self.ESTADO_CONCLUIDA,
                mensagem=(
                    "Dupla histórica validada e reutilizada."
                )
            )

        else:
            if exportacao is None:
                faltantes = [
                    str(caminho)
                    for caminho in caminhos_historico.values()
                    if not caminho.exists()
                ]

                detalhe = (
                    "\n".join(faltantes)
                    if faltantes
                    else (
                        "Foi solicitado um novo download, mas "
                        "não há navegador autenticado."
                    )
                )

                raise RuntimeError(
                    "É necessário abrir o SINAN para acompanhar "
                    "e baixar as exportações.\n"
                    f"{detalhe}"
                )

            self._verificar_cancelamento(cancelado)

            self._emitir(
                ao_evento=ao_evento,
                etapa=self.ETAPA_PROCESSAMENTO,
                estado=self.ESTADO_INICIADA,
                mensagem=(
                    "Abrindo a consulta das exportações DBF."
                )
            )

            exportacao.abrir_consulta_exportacoes_dbf()

            pasta_lote = self.arquivos_service.criar_pasta_lote(
                lote_id=lote["lote_id"],
                data_referencia=data_referencia
            )
            agravos_processados: set[str] = set()
            alertas_emitidos: set[object] = set()
            inicio_processamento = monotonic()

            configuracao_agravos = {
                "dengue": {
                    "agravo_arquivo": (
                        ArquivosExportacaoDbfService.AGRAVO_DENGUE
                    ),
                    "agravo_registro": ExportacaoDbfService.AGRAVO_DENGUE,
                    "rotulo": "Dengue",
                    "numero": numero_dengue
                },
                "chikungunya": {
                    "agravo_arquivo": (
                        ArquivosExportacaoDbfService.AGRAVO_CHIKUNGUNYA
                    ),
                    "agravo_registro": (
                        ExportacaoDbfService.AGRAVO_CHIKUNGUNYA
                    ),
                    "rotulo": "Chikungunya",
                    "numero": numero_chikungunya
                }
            }

            # Uma execução anterior pode ter concluído apenas um
            # agravo. Nesse caso, o arquivo histórico é validado e
            # reaproveitado sem novo download.
            for chave, configuracao in configuracao_agravos.items():
                if caminhos_historico[chave].exists():
                    self._finalizar_agravo_historico(
                        agravo=configuracao["agravo_arquivo"],
                        rotulo=configuracao["rotulo"],
                        data_referencia=data_referencia,
                        atualizar_pastas_teste=atualizar_pastas_teste,
                        atualizar_bancos_atuais=atualizar_bancos_atuais,
                        ao_evento=ao_evento,
                        reutilizado=True
                    )
                    agravos_processados.add(chave)

            def ao_atualizar(
                tentativa: int,
                resultados: dict[str, dict[str, object]]
            ):
                self.registro_service.atualizar_resultado_consulta(
                    lote_id=lote["lote_id"],
                    agravo=ExportacaoDbfService.AGRAVO_DENGUE,
                    resultado=resultados["dengue"]
                )
                self.registro_service.atualizar_resultado_consulta(
                    lote_id=lote["lote_id"],
                    agravo=ExportacaoDbfService.AGRAVO_CHIKUNGUNYA,
                    resultado=resultados["chikungunya"]
                )

                for chave, configuracao in configuracao_agravos.items():
                    if chave in agravos_processados:
                        continue

                    if self._resultado_exportacao_pronto(
                        resultados[chave]
                    ):
                        self._baixar_e_distribuir_agravo(
                            exportacao=exportacao,
                            numero_solicitacao=configuracao["numero"],
                            agravo=configuracao["agravo_arquivo"],
                            rotulo=configuracao["rotulo"],
                            pasta_lote=pasta_lote,
                            data_referencia=data_referencia,
                            atualizar_pastas_teste=atualizar_pastas_teste,
                            atualizar_bancos_atuais=atualizar_bancos_atuais,
                            ao_evento=ao_evento,
                            cancelado=cancelado
                        )
                        agravos_processados.add(chave)

                pendentes = [
                    configuracao_agravos[chave]["rotulo"]
                    for chave in configuracao_agravos
                    if chave not in agravos_processados
                ]
                concluidos = [
                    configuracao_agravos[chave]["rotulo"]
                    for chave in configuracao_agravos
                    if chave in agravos_processados
                ]

                if concluidos and pendentes:
                    mensagem = (
                        f"{', '.join(concluidos)} já foi validado e "
                        "distribuído. "
                        f"{', '.join(pendentes)} continua em "
                        "processamento no SINAN."
                    )
                else:
                    mensagem = (
                        f"Consulta {tentativa}: acompanhando o "
                        "processamento das exportações."
                    )

                tempo_decorrido = monotonic() - inicio_processamento

                self._emitir(
                    ao_evento=ao_evento,
                    etapa=self.ETAPA_PROCESSAMENTO,
                    estado=self.ESTADO_EM_ANDAMENTO,
                    mensagem=mensagem,
                    dados={
                        "tentativa": tentativa,
                        "tempo_decorrido_segundos": round(
                            tempo_decorrido,
                            1
                        ),
                        "agravos_processados": tuple(concluidos),
                        "agravos_pendentes": tuple(pendentes),
                        "dengue": {
                            "status": resultados["dengue"]["status"],
                            "link_disponivel": resultados["dengue"][
                                "link_disponivel"
                            ],
                            "processado": "dengue" in agravos_processados
                        },
                        "chikungunya": {
                            "status": resultados["chikungunya"]["status"],
                            "link_disponivel": resultados["chikungunya"][
                                "link_disponivel"
                            ],
                            "processado": (
                                "chikungunya" in agravos_processados
                            )
                        }
                    }
                )

                if (
                    tentativa >= 2
                    and 0 not in alertas_emitidos
                ):
                    alertas_emitidos.add(0)
                    self._emitir(
                        ao_evento=ao_evento,
                        etapa=self.ETAPA_PROCESSAMENTO,
                        estado=self.ESTADO_EM_ANDAMENTO,
                        mensagem=(
                            "O SINAN ainda está processando as "
                            "exportações."
                        ),
                        dados={
                            "alerta_processamento": True,
                            "marco_minutos": 0,
                            "nivel": "informacao",
                            "titulo": (
                                "Processamento iniciado no SINAN"
                            ),
                            "texto": (
                                "A disponibilização dos arquivos pode "
                                "levar alguns minutos devido ao tempo "
                                "de resposta do SINAN. O ArboHub "
                                "continuará acompanhando automaticamente "
                                "e você pode seguir usando o computador."
                            ),
                            "permitir_modo_manual": False,
                            "agravos_processados": tuple(concluidos),
                            "agravos_pendentes": tuple(pendentes)
                        }
                    )

                limite_formatado = (
                    self._formatar_duracao(
                        tempo_limite_segundos
                    )
                )

                marcos = (
                    (
                        aviso_inicial_segundos,
                        "aviso_inicial",
                        "informacao",
                        "O processamento pode demorar um pouco",
                        (
                            "As exportações continuam sendo preparadas "
                            "pelo SINAN. O acompanhamento permanece "
                            "automático e você pode continuar suas "
                            "atividades normalmente."
                        ),
                        False
                    ),
                    (
                        aviso_lento_segundos,
                        "aviso_lento",
                        "aviso",
                        "Processamento mais lento que o normal",
                        (
                            "Uma ou mais exportações ainda não estão "
                            "disponíveis. O ArboHub continua verificando "
                            "e processará imediatamente qualquer arquivo "
                            "que ficar pronto."
                        ),
                        False
                    ),
                    (
                        aviso_reforcado_segundos,
                        "aviso_reforcado",
                        "aviso",
                        "A exportação continua pendente",
                        (
                            "O tempo de resposta do SINAN está acima do "
                            "habitual. O acompanhamento continuará até "
                            f"o limite configurado de {limite_formatado}."
                        ),
                        False
                    )
                )

                for (
                    segundos,
                    chave_alerta,
                    nivel,
                    titulo,
                    texto,
                    permitir_manual
                ) in marcos:
                    if (
                        tempo_decorrido >= segundos
                        and chave_alerta not in alertas_emitidos
                    ):
                        alertas_emitidos.add(chave_alerta)
                        self._emitir(
                            ao_evento=ao_evento,
                            etapa=self.ETAPA_PROCESSAMENTO,
                            estado=self.ESTADO_EM_ANDAMENTO,
                            mensagem=titulo,
                            dados={
                                "alerta_processamento": True,
                                "marco_minutos": (
                                    int(segundos // 60)
                                    if segundos % 60 == 0
                                    else round(
                                        segundos / 60,
                                        1
                                    )
                                ),
                                "nivel": nivel,
                                "titulo": titulo,
                                "texto": texto,
                                "permitir_modo_manual": permitir_manual,
                                "agravos_processados": tuple(concluidos),
                                "agravos_pendentes": tuple(pendentes)
                            }
                        )

            processamento = exportacao.aguardar_solicitacoes_prontas(
                numero_dengue=numero_dengue,
                numero_chikungunya=numero_chikungunya,
                intervalo_segundos=intervalo_consulta_segundos,
                tempo_limite_segundos=tempo_limite_segundos,
                ao_atualizar=ao_atualizar,
                cancelado=cancelado,
                modo_manual_ativo=modo_manual_ativo
            )

            if not processamento["ambas_prontas"]:
                try:
                    self.arquivos_service.excluir_pasta_lote(
                        pasta_lote
                    )
                except Exception:
                    pass

                pendentes = [
                    configuracao_agravos[chave]["rotulo"]
                    for chave in configuracao_agravos
                    if chave not in agravos_processados
                ]
                concluidos = [
                    configuracao_agravos[chave]["rotulo"]
                    for chave in configuracao_agravos
                    if chave in agravos_processados
                ]

                limite_formatado = (
                    self._formatar_duracao(
                        tempo_limite_segundos
                    )
                )

                raise ProcessamentoBasesPendente(
                    (
                        "O acompanhamento automático chegou ao limite "
                        f"configurado de {limite_formatado}. Informe "
                        "sua supervisora sobre a exportação que continua "
                        "indisponível e use a correção manual quando o "
                        "arquivo for obtido."
                    ),
                    dados={
                        "tempo_decorrido_segundos": processamento[
                            "tempo_decorrido_segundos"
                        ],
                        "tempo_limite_segundos":
                            tempo_limite_segundos,
                        "agravos_processados": tuple(concluidos),
                        "agravos_pendentes": tuple(pendentes),
                        "numero_dengue": numero_dengue,
                        "numero_chikungunya": numero_chikungunya,
                        "dengue": processamento["dengue"],
                        "chikungunya": processamento["chikungunya"],
                        "correcao_manual_disponivel": bool(pendentes),
                        "data_referencia": data_referencia.isoformat()
                    }
                )

            # A última consulta pode indicar os dois links prontos.
            # Garante o processamento de algum agravo que ainda não
            # tenha sido tratado dentro do callback.
            for chave, configuracao in configuracao_agravos.items():
                if chave in agravos_processados:
                    continue
                self._baixar_e_distribuir_agravo(
                    exportacao=exportacao,
                    numero_solicitacao=configuracao["numero"],
                    agravo=configuracao["agravo_arquivo"],
                    rotulo=configuracao["rotulo"],
                    pasta_lote=pasta_lote,
                    data_referencia=data_referencia,
                    atualizar_pastas_teste=atualizar_pastas_teste,
                    atualizar_bancos_atuais=atualizar_bancos_atuais,
                    ao_evento=ao_evento,
                    cancelado=cancelado
                )
                agravos_processados.add(chave)

            try:
                self.arquivos_service.excluir_pasta_lote(
                    pasta_lote
                )
            except Exception:
                pass

            self._emitir(
                ao_evento=ao_evento,
                etapa=self.ETAPA_PROCESSAMENTO,
                estado=self.ESTADO_CONCLUIDA,
                mensagem="As duas exportações estão prontas e processadas.",
                dados={
                    "tentativas": processamento["tentativas"],
                    "tempo_decorrido_segundos": processamento[
                        "tempo_decorrido_segundos"
                    ]
                }
            )

            self._emitir(
                ao_evento=ao_evento,
                etapa=self.ETAPA_DOWNLOAD,
                estado=self.ESTADO_CONCLUIDA,
                mensagem=(
                    "Os dois ZIPs foram baixados, identificados e "
                    "validados."
                )
            )

            resultado_historico = {
                "reutilizado": False,
                "download_realizado": True,
                "dengue": {
                    "caminho": caminhos_historico["dengue"]
                },
                "chikungunya": {
                    "caminho": caminhos_historico["chikungunya"]
                }
            }

            self._emitir(
                ao_evento=ao_evento,
                etapa=self.ETAPA_HISTORICO,
                estado=self.ESTADO_CONCLUIDA,
                mensagem=(
                    "Os ZIPs de Dengue e Chikungunya estão nas "
                    "respectivas pastas do histórico."
                ),
                dados={
                    "dengue": caminhos_historico["dengue"],
                    "chikungunya": caminhos_historico["chikungunya"]
                }
            )

        self._verificar_cancelamento(
            cancelado
        )

        self._emitir(
            ao_evento=ao_evento,
            etapa=self.ETAPA_EXTRACAO,
            estado=self.ESTADO_INICIADA,
            mensagem=(
                "Validando a extração dos dois DBFs."
            )
        )

        resultado_extracao = (
            self.arquivos_service
            .validar_extracao_historico(
                data_referencia=data_referencia
            )
        )

        self._emitir(
            ao_evento=ao_evento,
            etapa=self.ETAPA_EXTRACAO,
            estado=self.ESTADO_CONCLUIDA,
            mensagem=(
                "Extração validada sem interpretar registros."
            ),
            dados={
                "dengue":
                    resultado_extracao[
                        "dengue"
                    ]["nome_interno"],
                "chikungunya":
                    resultado_extracao[
                        "chikungunya"
                    ]["nome_interno"]
            }
        )

        resultado_testes = None

        if atualizar_pastas_teste:
            self._verificar_cancelamento(
                cancelado
            )

            self._emitir(
                ao_evento=ao_evento,
                etapa=self.ETAPA_PASTAS_TESTE,
                estado=self.ESTADO_INICIADA,
                mensagem=(
                    "Atualizando os destinos configurados de "
                    "Dengue e Chikungunya."
                )
            )

            resultado_testes = (
                self.arquivos_service
                .instalar_dbfs_pastas_teste(
                    data_referencia=data_referencia
                )
            )

            self._emitir(
                ao_evento=ao_evento,
                etapa=self.ETAPA_PASTAS_TESTE,
                estado=self.ESTADO_CONCLUIDA,
                mensagem=(
                    "Pastas de teste atualizadas com backup "
                    "e validação SHA-256."
                ),
                dados={
                    "dengue":
                        resultado_testes[
                            "dengue"
                        ]["destino"],
                    "chikungunya":
                        resultado_testes[
                            "chikungunya"
                        ]["destino"]
                }
            )

        else:
            self._emitir(
                ao_evento=ao_evento,
                etapa=self.ETAPA_PASTAS_TESTE,
                estado=self.ESTADO_IGNORADA,
                mensagem=(
                    "Atualização das pastas de teste ignorada."
                )
            )

        resultado_bancos_atuais = None

        if atualizar_bancos_atuais:
            self._verificar_cancelamento(
                cancelado
            )

            self._emitir(
                ao_evento=ao_evento,
                etapa=self.ETAPA_BANCOS_ATUAIS,
                estado=self.ESTADO_INICIADA,
                mensagem=(
                    "Atualizando Documents\\SINAN\\"
                    "Bancos_Atuais."
                )
            )

            resultado_bancos_atuais = (
                self.arquivos_service
                .instalar_dbfs_bancos_atuais(
                    data_referencia=data_referencia
                )
            )

            self._emitir(
                ao_evento=ao_evento,
                etapa=self.ETAPA_BANCOS_ATUAIS,
                estado=self.ESTADO_CONCLUIDA,
                mensagem=(
                    "Bancos_Atuais atualizado com backup "
                    "e validação SHA-256."
                ),
                dados={
                    "dengue":
                        resultado_bancos_atuais[
                            "dengue"
                        ]["destino"],
                    "chikungunya":
                        resultado_bancos_atuais[
                            "chikungunya"
                        ]["destino"]
                }
            )

        else:
            self._emitir(
                ao_evento=ao_evento,
                etapa=self.ETAPA_BANCOS_ATUAIS,
                estado=self.ESTADO_IGNORADA,
                mensagem=(
                    "Atualização de Bancos_Atuais ignorada."
                )
            )

        resultado_final = {
            "data_referencia":
                data_referencia.isoformat(),
            "lote": lote,
            "historico": resultado_historico,
            "extracao": resultado_extracao,
            "pastas_teste": resultado_testes,
            "bancos_atuais":
                resultado_bancos_atuais,
            "dados_de_pacientes_lidos": False,
            "concluida": True
        }

        self._emitir(
            ao_evento=ao_evento,
            etapa=self.ETAPA_FINALIZACAO,
            estado=self.ESTADO_CONCLUIDA,
            mensagem=(
                "Rotina posterior às solicitações concluída."
            ),
            dados={
                "historico_reutilizado":
                    bool(
                        resultado_historico.get(
                            "reutilizado",
                            False
                        )
                    ),
                "atualizou_pastas_teste":
                    atualizar_pastas_teste,
                "atualizou_bancos_atuais":
                    atualizar_bancos_atuais
            }
        )

        return resultado_final

    def processar_correcao_manual(
        self,
        caminho_zip: str | Path,
        agravos_pendentes: tuple[str, ...] | list[str],
        data_referencia: date | None = None,
        atualizar_pastas_teste: bool = True,
        atualizar_bancos_atuais: bool = True,
        ao_evento: CallbackEvento | None = None,
        cancelado: CallbackCancelamento | None = None
    ) -> dict[str, object]:
        """
        Valida e instala um ZIP obtido manualmente para resolver
        uma pendência de processamento do SINAN.

        O arquivo não é aceito apenas pela extensão. O conteúdo do
        ZIP é validado e o agravo é identificado por DENGON ou
        CHIKON antes de qualquer cópia ou substituição.
        """

        data_referencia = (
            data_referencia
            or date.today()
        )
        self._verificar_cancelamento(
            cancelado
        )

        identificacao = (
            self.arquivos_service
            .identificar_agravo_zip(
                caminho_zip
            )
        )
        agravo = str(
            identificacao["agravo"]
        )

        rotulos = {
            ArquivosExportacaoDbfService.AGRAVO_DENGUE:
                "Dengue",
            ArquivosExportacaoDbfService.AGRAVO_CHIKUNGUNYA:
                "Chikungunya"
        }

        pendentes_normalizados: set[str] = set()

        for item in agravos_pendentes:
            valor = str(item).strip().casefold()

            if valor == "dengue":
                pendentes_normalizados.add(
                    ArquivosExportacaoDbfService
                    .AGRAVO_DENGUE
                )
            elif valor in {
                "chikungunya",
                "chiku"
            }:
                pendentes_normalizados.add(
                    ArquivosExportacaoDbfService
                    .AGRAVO_CHIKUNGUNYA
                )

        if not pendentes_normalizados:
            raise RuntimeError(
                "Não há um agravo pendente registrado para "
                "receber a correção manual."
            )

        if agravo not in pendentes_normalizados:
            esperado = ", ".join(
                rotulos[item]
                for item in sorted(
                    pendentes_normalizados
                )
            )
            raise RuntimeError(
                "O ZIP selecionado pertence a "
                f"{rotulos[agravo]}, mas a pendência atual é: "
                f"{esperado}."
            )

        rotulo = rotulos[agravo]

        self._emitir(
            ao_evento=ao_evento,
            etapa=self.ETAPA_PROCESSAMENTO,
            estado=self.ESTADO_EM_ANDAMENTO,
            mensagem=(
                f"Validando a correção manual de {rotulo}."
            ),
            dados={
                "correcao_manual": True,
                "agravo": agravo,
                "rotulo": rotulo
            }
        )

        historico = (
            self.arquivos_service
            .arquivar_agravo(
                caminho_zip=caminho_zip,
                agravo=agravo,
                data_referencia=data_referencia,
                substituir_existente=False
            )
        )

        self._finalizar_agravo_historico(
            agravo=agravo,
            rotulo=rotulo,
            data_referencia=data_referencia,
            atualizar_pastas_teste=(
                atualizar_pastas_teste
            ),
            atualizar_bancos_atuais=(
                atualizar_bancos_atuais
            ),
            ao_evento=ao_evento,
            reutilizado=bool(
                historico["reutilizado"]
            )
        )

        caminhos = {
            ArquivosExportacaoDbfService.AGRAVO_DENGUE:
                self.arquivos_service.caminho_historico(
                    agravo=(
                        ArquivosExportacaoDbfService
                        .AGRAVO_DENGUE
                    ),
                    data_referencia=data_referencia
                ),
            ArquivosExportacaoDbfService.AGRAVO_CHIKUNGUNYA:
                self.arquivos_service.caminho_historico(
                    agravo=(
                        ArquivosExportacaoDbfService
                        .AGRAVO_CHIKUNGUNYA
                    ),
                    data_referencia=data_referencia
                )
        }

        ainda_pendentes = [
            item
            for item, caminho in caminhos.items()
            if not caminho.exists()
        ]

        if ainda_pendentes:
            self._emitir(
                ao_evento=ao_evento,
                etapa=self.ETAPA_PROCESSAMENTO,
                estado=self.ESTADO_EM_ANDAMENTO,
                mensagem=(
                    f"A correção manual de {rotulo} foi validada. "
                    "Ainda existe outra exportação pendente."
                ),
                dados={
                    "arquivo_processado": True,
                    "correcao_manual": True,
                    "agravo": agravo,
                    "rotulo": rotulo,
                    "agravos_pendentes": tuple(
                        rotulos[item]
                        for item in ainda_pendentes
                    )
                }
            )

            return {
                "concluida": False,
                "agravo_corrigido": agravo,
                "rotulo_corrigido": rotulo,
                "agravos_pendentes": tuple(
                    rotulos[item]
                    for item in ainda_pendentes
                ),
                "dados_de_pacientes_lidos": False
            }

        validacao_final = (
            self.arquivos_service
            .validar_extracao_historico(
                data_referencia=data_referencia
            )
        )

        self._emitir(
            ao_evento=ao_evento,
            etapa=self.ETAPA_PROCESSAMENTO,
            estado=self.ESTADO_CONCLUIDA,
            mensagem=(
                f"A correção manual de {rotulo} foi validada e "
                "a dupla diária está completa."
            ),
            dados={
                "arquivo_processado": True,
                "correcao_manual": True,
                "agravo": agravo,
                "rotulo": rotulo
            }
        )

        return {
            "concluida": True,
            "agravo_corrigido": agravo,
            "rotulo_corrigido": rotulo,
            "validacao": validacao_final,
            "agravos_pendentes": (),
            "dados_de_pacientes_lidos": False
        }

    def _resultado_exportacao_pronto(
        self,
        resultado: dict[str, object]
    ) -> bool:
        return (
            bool(resultado.get("encontrada"))
            and bool(resultado.get("processamento_concluido"))
            and bool(resultado.get("link_disponivel"))
        )

    def _baixar_e_distribuir_agravo(
        self,
        exportacao: ExportacaoBasesDbf,
        numero_solicitacao: str,
        agravo: str,
        rotulo: str,
        pasta_lote: Path,
        data_referencia: date,
        atualizar_pastas_teste: bool,
        atualizar_bancos_atuais: bool,
        ao_evento: CallbackEvento | None,
        cancelado: CallbackCancelamento | None
    ):
        """
        Processa imediatamente um agravo disponível, mesmo quando
        a outra exportação ainda está em processamento.
        """

        self._verificar_cancelamento(cancelado)
        temporario = self.arquivos_service.caminho_temporario(
            pasta_lote=pasta_lote,
            agravo=agravo
        )

        self._emitir(
            ao_evento=ao_evento,
            etapa=self.ETAPA_PROCESSAMENTO,
            estado=self.ESTADO_EM_ANDAMENTO,
            mensagem=(
                f"{rotulo} ficou disponível. Baixando e "
                "validando o arquivo agora."
            ),
            dados={
                "arquivo_disponivel": True,
                "agravo": agravo,
                "rotulo": rotulo
            }
        )

        exportacao.baixar_exportacao_dbf(
            numero_solicitacao=numero_solicitacao,
            caminho_destino=temporario
        )
        validado = self.arquivos_service.validar_e_finalizar(
            caminho_temporario=temporario,
            pasta_lote=pasta_lote,
            agravo=agravo,
            data_referencia=data_referencia
        )
        historico = self.arquivos_service.arquivar_agravo(
            caminho_zip=validado["caminho"],
            agravo=agravo,
            data_referencia=data_referencia,
            substituir_existente=False
        )

        self._finalizar_agravo_historico(
            agravo=agravo,
            rotulo=rotulo,
            data_referencia=data_referencia,
            atualizar_pastas_teste=atualizar_pastas_teste,
            atualizar_bancos_atuais=atualizar_bancos_atuais,
            ao_evento=ao_evento,
            reutilizado=bool(historico["reutilizado"])
        )

    def _finalizar_agravo_historico(
        self,
        agravo: str,
        rotulo: str,
        data_referencia: date,
        atualizar_pastas_teste: bool,
        atualizar_bancos_atuais: bool,
        ao_evento: CallbackEvento | None,
        reutilizado: bool
    ):
        validacao = (
            self.arquivos_service
            .validar_extracao_agravo_historico(
                agravo=agravo,
                data_referencia=data_referencia
            )
        )
        resultado_teste = None
        resultado_atual = None

        if atualizar_pastas_teste:
            resultado_teste = (
                self.arquivos_service
                .instalar_dbf_agravo_pasta_teste(
                    agravo=agravo,
                    data_referencia=data_referencia
                )
            )

        if atualizar_bancos_atuais:
            resultado_atual = (
                self.arquivos_service
                .instalar_dbf_agravo_bancos_atuais(
                    agravo=agravo,
                    data_referencia=data_referencia
                )
            )

        self._emitir(
            ao_evento=ao_evento,
            etapa=self.ETAPA_PROCESSAMENTO,
            estado=self.ESTADO_EM_ANDAMENTO,
            mensagem=(
                f"{rotulo} foi identificado, validado e colocado "
                "nas pastas correspondentes. A outra exportação "
                "continuará sendo acompanhada."
            ),
            dados={
                "arquivo_processado": True,
                "agravo": agravo,
                "rotulo": rotulo,
                "historico_reutilizado": reutilizado,
                "nome_dbf": validacao["nome_interno"],
                "destino_teste": (
                    resultado_teste["destino"]
                    if resultado_teste is not None
                    else None
                ),
                "destino_bancos_atuais": (
                    resultado_atual["destino"]
                    if resultado_atual is not None
                    else None
                )
            }
        )

    def _validar_tempos_acompanhamento(
        self,
        intervalo_consulta_segundos: float,
        aviso_inicial_segundos: float,
        aviso_lento_segundos: float,
        aviso_reforcado_segundos: float,
        tempo_limite_segundos: float
    ):
        valores = (
            intervalo_consulta_segundos,
            aviso_inicial_segundos,
            aviso_lento_segundos,
            aviso_reforcado_segundos,
            tempo_limite_segundos
        )

        if any(
            valor <= 0
            for valor in valores
        ):
            raise ValueError(
                "Os tempos de acompanhamento precisam ser maiores "
                "que zero."
            )

        if not (
            aviso_inicial_segundos
            < aviso_lento_segundos
            < aviso_reforcado_segundos
            < tempo_limite_segundos
        ):
            raise ValueError(
                "Os avisos da exportação precisam estar em ordem "
                "crescente e ocorrer antes do tempo máximo."
            )

    def _formatar_duracao(
        self,
        segundos: float
    ) -> str:
        if segundos % 60 == 0:
            minutos = int(
                segundos // 60
            )
            unidade = (
                "minuto"
                if minutos == 1
                else "minutos"
            )
            return f"{minutos} {unidade}"

        return f"{segundos:g} segundos"

    def _verificar_cancelamento(
        self,
        cancelado: CallbackCancelamento | None
    ):
        if (
            cancelado is not None
            and cancelado()
        ):
            raise RotinaBasesCancelada(
                "A rotina de bases foi cancelada."
            )

    def _emitir(
        self,
        ao_evento: CallbackEvento | None,
        etapa: str,
        estado: str,
        mensagem: str,
        dados: dict[str, object] | None = None
    ):
        if ao_evento is None:
            return

        ao_evento(
            EventoRotinaBases(
                etapa=etapa,
                estado=estado,
                mensagem=mensagem,
                dados=dados or {}
            )
        )
