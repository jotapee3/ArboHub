from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
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
    - atualiza Teste AB1 e Teste AB2;
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
        tempo_limite_segundos: float = 1800,
        ao_evento: CallbackEvento | None = None,
        cancelado: CallbackCancelamento | None = None
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
            ao_evento=ao_evento,
            cancelado=cancelado
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
        tempo_limite_segundos: float = 1800,
        ao_evento: CallbackEvento | None = None,
        cancelado: CallbackCancelamento | None = None
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

            self._verificar_cancelamento(
                cancelado
            )

            self._emitir(
                ao_evento=ao_evento,
                etapa=self.ETAPA_PROCESSAMENTO,
                estado=self.ESTADO_INICIADA,
                mensagem=(
                    "Abrindo a consulta das exportações DBF."
                )
            )

            exportacao.abrir_consulta_exportacoes_dbf()

            def ao_atualizar(
                tentativa: int,
                resultados: dict[
                    str,
                    dict[str, object]
                ]
            ):
                self.registro_service.atualizar_resultado_consulta(
                    lote_id=lote["lote_id"],
                    agravo=(
                        ExportacaoDbfService
                        .AGRAVO_DENGUE
                    ),
                    resultado=resultados["dengue"]
                )
                self.registro_service.atualizar_resultado_consulta(
                    lote_id=lote["lote_id"],
                    agravo=(
                        ExportacaoDbfService
                        .AGRAVO_CHIKUNGUNYA
                    ),
                    resultado=resultados[
                        "chikungunya"
                    ]
                )

                self._emitir(
                    ao_evento=ao_evento,
                    etapa=self.ETAPA_PROCESSAMENTO,
                    estado=self.ESTADO_EM_ANDAMENTO,
                    mensagem=(
                        f"Consulta {tentativa}: "
                        "acompanhando o processamento."
                    ),
                    dados={
                        "tentativa": tentativa,
                        "dengue": {
                            "status":
                                resultados[
                                    "dengue"
                                ]["status"],
                            "link_disponivel":
                                resultados[
                                    "dengue"
                                ]["link_disponivel"]
                        },
                        "chikungunya": {
                            "status":
                                resultados[
                                    "chikungunya"
                                ]["status"],
                            "link_disponivel":
                                resultados[
                                    "chikungunya"
                                ]["link_disponivel"]
                        }
                    }
                )

            processamento = (
                exportacao.aguardar_solicitacoes_prontas(
                    numero_dengue=numero_dengue,
                    numero_chikungunya=(
                        numero_chikungunya
                    ),
                    intervalo_segundos=(
                        intervalo_consulta_segundos
                    ),
                    tempo_limite_segundos=(
                        tempo_limite_segundos
                    ),
                    ao_atualizar=ao_atualizar,
                    cancelado=cancelado
                )
            )

            self._emitir(
                ao_evento=ao_evento,
                etapa=self.ETAPA_PROCESSAMENTO,
                estado=self.ESTADO_CONCLUIDA,
                mensagem=(
                    "As duas exportações estão prontas."
                ),
                dados={
                    "tentativas":
                        processamento["tentativas"],
                    "tempo_decorrido_segundos":
                        processamento[
                            "tempo_decorrido_segundos"
                        ]
                }
            )

            self._verificar_cancelamento(
                cancelado
            )

            pasta_lote = (
                self.arquivos_service.criar_pasta_lote(
                    lote_id=lote["lote_id"],
                    data_referencia=data_referencia
                )
            )

            self._emitir(
                ao_evento=ao_evento,
                etapa=self.ETAPA_DOWNLOAD,
                estado=self.ESTADO_INICIADA,
                mensagem=(
                    "Baixando e validando os dois ZIPs."
                ),
                dados={
                    "pasta_temporaria": pasta_lote
                }
            )

            temporario_dengue = (
                self.arquivos_service.caminho_temporario(
                    pasta_lote=pasta_lote,
                    agravo=(
                        ArquivosExportacaoDbfService
                        .AGRAVO_DENGUE
                    )
                )
            )

            exportacao.baixar_exportacao_dbf(
                numero_solicitacao=numero_dengue,
                caminho_destino=temporario_dengue
            )

            dengue = (
                self.arquivos_service.validar_e_finalizar(
                    caminho_temporario=temporario_dengue,
                    pasta_lote=pasta_lote,
                    agravo=(
                        ArquivosExportacaoDbfService
                        .AGRAVO_DENGUE
                    ),
                    data_referencia=data_referencia
                )
            )

            self._verificar_cancelamento(
                cancelado
            )

            temporario_chikungunya = (
                self.arquivos_service.caminho_temporario(
                    pasta_lote=pasta_lote,
                    agravo=(
                        ArquivosExportacaoDbfService
                        .AGRAVO_CHIKUNGUNYA
                    )
                )
            )

            exportacao.baixar_exportacao_dbf(
                numero_solicitacao=numero_chikungunya,
                caminho_destino=temporario_chikungunya
            )

            chikungunya = (
                self.arquivos_service.validar_e_finalizar(
                    caminho_temporario=temporario_chikungunya,
                    pasta_lote=pasta_lote,
                    agravo=(
                        ArquivosExportacaoDbfService
                        .AGRAVO_CHIKUNGUNYA
                    ),
                    data_referencia=data_referencia
                )
            )

            self._emitir(
                ao_evento=ao_evento,
                etapa=self.ETAPA_DOWNLOAD,
                estado=self.ESTADO_CONCLUIDA,
                mensagem=(
                    "Os dois ZIPs foram baixados e validados."
                ),
                dados={
                    "dengue": dengue["nome"],
                    "chikungunya":
                        chikungunya["nome"]
                }
            )

            self._verificar_cancelamento(
                cancelado
            )

            self._emitir(
                ao_evento=ao_evento,
                etapa=self.ETAPA_HISTORICO,
                estado=self.ESTADO_INICIADA,
                mensagem=(
                    "Arquivando a dupla no histórico."
                )
            )

            resultado_historico = (
                self.arquivos_service.arquivar_lote(
                    caminho_dengue=dengue["caminho"],
                    caminho_chikungunya=(
                        chikungunya["caminho"]
                    ),
                    pasta_lote=pasta_lote,
                    data_referencia=data_referencia,
                    substituir_existentes=(
                        substituir_historico
                    )
                )
            )

            resultado_historico[
                "reutilizado"
            ] = False
            resultado_historico[
                "download_realizado"
            ] = True

            self._emitir(
                ao_evento=ao_evento,
                etapa=self.ETAPA_HISTORICO,
                estado=self.ESTADO_CONCLUIDA,
                mensagem=(
                    "Os ZIPs foram arquivados e o staging "
                    "de download foi removido."
                ),
                dados={
                    "dengue":
                        resultado_historico[
                            "dengue"
                        ]["caminho"],
                    "chikungunya":
                        resultado_historico[
                            "chikungunya"
                        ]["caminho"]
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
                    "Atualizando Teste AB1 e Teste AB2."
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