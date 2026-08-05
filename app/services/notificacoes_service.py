from __future__ import annotations

import os
from datetime import date, datetime
from typing import Any

from app.services.configuracoes_service import (
    ConfiguracoesService
)


class NotificacoesService:
    """
    Notificações locais e resumos operacionais do ArboHub.

    O serviço:
    - usa somente sons nativos do Windows;
    - não adiciona arquivos de áudio ao projeto;
    - não envia mensagens, e-mails ou chamadas;
    - monta resumos sem dados de pacientes;
    - lê apenas preferências locais não sensíveis.
    """

    TIPO_CONCLUSAO = "conclusao"
    TIPO_ATENCAO = "atencao"
    TIPO_EXPORTACAO_DISPONIVEL = (
        "exportacao_disponivel"
    )

    def __init__(
        self,
        configuracoes_service:
            ConfiguracoesService | None = None
    ):
        self.configuracoes_service = (
            configuracoes_service
            or ConfiguracoesService()
        )

    def tocar_conclusao(self) -> bool:
        configuracoes = self._obter_notificacoes()

        if not configuracoes["som_conclusao"]:
            return False

        return self._tocar_som_nativo(
            self.TIPO_CONCLUSAO
        )

    def tocar_atencao(self) -> bool:
        configuracoes = self._obter_notificacoes()

        if not configuracoes["som_atencao"]:
            return False

        return self._tocar_som_nativo(
            self.TIPO_ATENCAO
        )

    def tocar_exportacao_disponivel(self) -> bool:
        configuracoes = self._obter_notificacoes()

        if not configuracoes[
            "som_exportacao_disponivel"
        ]:
            return False

        return self._tocar_som_nativo(
            self.TIPO_EXPORTACAO_DISPONIVEL
        )

    def testar_som(self, tipo: str) -> bool:
        """
        Reproduz o som escolhido mesmo quando sua preferência está
        desativada. O botão de teste não altera as configurações.
        """

        tipos_validos = {
            self.TIPO_CONCLUSAO,
            self.TIPO_ATENCAO,
            self.TIPO_EXPORTACAO_DISPONIVEL
        }

        if tipo not in tipos_validos:
            raise ValueError(
                "Tipo de notificação sonora desconhecido."
            )

        return self._tocar_som_nativo(
            tipo
        )

    def obter_supervisao(self) -> dict[str, str]:
        notificacoes = self._obter_notificacoes()
        supervisao = notificacoes[
            "supervisao"
        ]

        return {
            "nome": str(
                supervisao.get(
                    "nome",
                    ""
                )
            ).strip(),
            "telefone": str(
                supervisao.get(
                    "telefone",
                    ""
                )
            ).strip(),
            "email": str(
                supervisao.get(
                    "email",
                    ""
                )
            ).strip()
        }

    def montar_resumo_pendencia(
        self,
        dados: dict[str, Any]
    ) -> str:
        """
        Monta um texto operacional sem conteúdo de DBF e sem dados
        pessoais de pacientes.
        """

        supervisao = self.obter_supervisao()

        data_referencia = self._formatar_data(
            dados.get(
                "data_referencia"
            )
        )
        tempo = self._formatar_duracao(
            dados.get(
                "tempo_limite_segundos",
                dados.get(
                    "tempo_decorrido_segundos",
                    0
                )
            )
        )

        processados = {
            str(item).strip().casefold()
            for item in dados.get(
                "agravos_processados",
                ()
            )
        }
        pendentes = {
            str(item).strip().casefold()
            for item in dados.get(
                "agravos_pendentes",
                ()
            )
        }

        linhas = [
            "ArboHub — Pendência na exportação do SINAN",
            "",
            f"Data: {data_referencia}",
            f"Tempo de acompanhamento: {tempo}"
        ]

        if supervisao["nome"]:
            linhas.extend(
                (
                    "",
                    (
                        "Supervisão responsável: "
                        f"{supervisao['nome']}"
                    )
                )
            )

        linhas.extend(
            (
                "",
                "Dengue",
                (
                    "Solicitação: "
                    f"{dados.get('numero_dengue') or 'não informada'}"
                ),
                (
                    "Situação: "
                    + self._situacao_agravo(
                        "dengue",
                        processados,
                        pendentes
                    )
                ),
                "",
                "Chikungunya",
                (
                    "Solicitação: "
                    f"{dados.get('numero_chikungunya') or 'não informada'}"
                ),
                (
                    "Situação: "
                    + self._situacao_agravo(
                        "chikungunya",
                        processados,
                        pendentes
                    )
                ),
                "",
                (
                    "Os arquivos disponíveis já foram identificados "
                    "e validados. A rotina permanece pendente até que "
                    "os dois agravos estejam válidos."
                )
            )
        )

        return "\n".join(
            linhas
        )

    def _obter_notificacoes(self) -> dict[str, Any]:
        configuracoes = (
            self.configuracoes_service.carregar()
        )

        return configuracoes[
            "notificacoes"
        ]

    def _tocar_som_nativo(
        self,
        tipo: str
    ) -> bool:
        if os.name != "nt":
            return False

        try:
            import winsound
        except ImportError:
            return False

        configuracoes_som = {
            self.TIPO_CONCLUSAO:
                winsound.MB_ICONASTERISK,
            self.TIPO_ATENCAO:
                winsound.MB_ICONEXCLAMATION,
            self.TIPO_EXPORTACAO_DISPONIVEL:
                winsound.MB_OK
        }

        try:
            winsound.MessageBeep(
                configuracoes_som[
                    tipo
                ]
            )
            return True
        except RuntimeError:
            return False

    def _formatar_data(
        self,
        valor: Any
    ) -> str:
        if isinstance(
            valor,
            datetime
        ):
            return valor.strftime(
                "%d/%m/%Y"
            )

        if isinstance(
            valor,
            date
        ):
            return valor.strftime(
                "%d/%m/%Y"
            )

        texto = str(
            valor
            or ""
        ).strip()

        if not texto:
            return date.today().strftime(
                "%d/%m/%Y"
            )

        try:
            return date.fromisoformat(
                texto[:10]
            ).strftime(
                "%d/%m/%Y"
            )
        except ValueError:
            return texto

    def _formatar_duracao(
        self,
        valor: Any
    ) -> str:
        try:
            segundos = max(
                0,
                int(
                    float(valor)
                )
            )
        except (
            TypeError,
            ValueError
        ):
            segundos = 0

        if segundos >= 60 and segundos % 60 == 0:
            minutos = segundos // 60
            unidade = (
                "minuto"
                if minutos == 1
                else "minutos"
            )
            return f"{minutos} {unidade}"

        unidade = (
            "segundo"
            if segundos == 1
            else "segundos"
        )
        return f"{segundos} {unidade}"

    def _situacao_agravo(
        self,
        agravo: str,
        processados: set[str],
        pendentes: set[str]
    ) -> str:
        if agravo in processados:
            return "arquivo disponível e processado"

        if agravo in pendentes:
            return "processamento pendente no SINAN"

        return "situação não informada"
