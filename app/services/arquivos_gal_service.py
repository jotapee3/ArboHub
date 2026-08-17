from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import zipfile
from datetime import date, timedelta
from pathlib import Path


class ArquivosGalService:
    """Organiza o relatorio do GAL sem ler seu conteudo clinico."""

    CSV_VAZIO_SHA256 = (
        "86e7b2f96c2dde2e8ff1589da12a55d5"
        "536af1e722128842fc28e3f6d23a042f"
    )

    MESES = (
        "Janeiro",
        "Fevereiro",
        "Março",
        "Abril",
        "Maio",
        "Junho",
        "Julho",
        "Agosto",
        "Setembro",
        "Outubro",
        "Novembro",
        "Dezembro"
    )

    EXTENSOES_RELATORIO = {
        ".csv",
        ".xlsx",
        ".xls",
        ".txt",
        ".dbf"
    }

    def __init__(
        self,
        pasta_historico: str | Path | None = None,
        pasta_banco_atual: str | Path | None = None,
        pasta_teste_soro: str | Path | None = None
    ):
        self.pasta_historico = Path(
            pasta_historico
            or (
                Path.home()
                / "Documents"
                / "GAL"
                / "Historico"
            )
        )
        self.pasta_banco_atual = Path(
            pasta_banco_atual
            or (
                Path.home()
                / "Documents"
                / "GAL"
                / "Banco_Atual"
            )
        )
        self.pasta_teste_soro = Path(
            pasta_teste_soro
            or r"F:\Antropozoonoses\TesteSORO"
        )

    def intervalo_semanal(
        self,
        data_referencia: date | None = None
    ) -> tuple[date, date]:
        data_referencia = data_referencia or date.today()
        segunda_atual = (
            data_referencia
            - timedelta(days=data_referencia.weekday())
        )
        segunda_anterior = segunda_atual - timedelta(days=7)
        return segunda_anterior, segunda_atual

    def pasta_historico_mes(
        self,
        data_referencia: date | None = None
    ) -> Path:
        data_referencia = data_referencia or date.today()
        nome_mes = self.MESES[data_referencia.month - 1]

        return (
            self.pasta_historico
            / str(data_referencia.year)
            / f"{data_referencia.month:02d}_{nome_mes}"
        )

    def validar_destinos(
        self,
        data_referencia: date | None = None
    ) -> dict[str, Path]:
        _data_inicio, data_fim = self.intervalo_semanal(
            data_referencia
        )
        pasta_mes = self.pasta_historico_mes(data_fim)
        pasta_mes.mkdir(parents=True, exist_ok=True)
        self.pasta_banco_atual.mkdir(parents=True, exist_ok=True)

        self._validar_pasta_gravavel(
            pasta_mes,
            "histórico mensal do GAL"
        )
        self._validar_pasta_gravavel(
            self.pasta_banco_atual,
            "Banco_Atual do GAL"
        )

        if not self.pasta_teste_soro.exists():
            raise FileNotFoundError(
                "A pasta de destino do GAL não foi encontrada: "
                f"{self.pasta_teste_soro}. Confirme se a unidade F: "
                "está conectada."
            )

        if not self.pasta_teste_soro.is_dir():
            raise NotADirectoryError(
                "O destino TesteSORO não é uma pasta: "
                f"{self.pasta_teste_soro}"
            )

        self._validar_pasta_gravavel(
            self.pasta_teste_soro,
            "TesteSORO"
        )

        return {
            "historico": pasta_mes,
            "banco_atual": self.pasta_banco_atual,
            "teste_soro": self.pasta_teste_soro
        }

    def processar_download(
        self,
        caminho_arquivo: str | Path,
        data_referencia: date | None = None,
        data_inicio: date | None = None
    ) -> dict[str, object]:
        """
        Normaliza o relatório e substitui os três destinos do GAL.

        Quando o GAL entrega um ZIP, somente um arquivo de relatorio
        compativel e extraido. Nomes internos nunca sao usados como
        caminho, evitando saida da pasta temporaria.
        """

        data_referencia = data_referencia or date.today()
        origem = Path(caminho_arquivo)

        if not origem.is_file():
            raise FileNotFoundError(
                f"O arquivo do GAL não foi encontrado: {origem}"
            )

        if origem.stat().st_size <= 0:
            raise ValueError("O arquivo do GAL está vazio.")

        data_inicio_padrao, data_fim = self.intervalo_semanal(
            data_referencia
        )
        data_inicio = data_inicio or data_inicio_padrao

        if self.corresponde_ao_csv_vazio(origem):
            raise ValueError(
                "O arquivo do GAL corresponde ao modelo de CSV vazio."
            )

        destinos = self.validar_destinos(data_referencia)
        with tempfile.TemporaryDirectory(
            prefix="arbohub_gal_conteudo_"
        ) as pasta_temporaria:
            arquivo_relatorio = self._obter_relatorio(
                origem=origem,
                pasta_temporaria=Path(pasta_temporaria)
            )
            extensao = arquivo_relatorio.suffix.casefold()
            if extensao != ".csv":
                raise ValueError(
                    "O relatório semanal do GAL precisa ser um CSV "
                    "para atualizar o histórico e os bancos."
                )

            nome_base_historico = f"gal_{data_fim.isoformat()}"
            arquivo_historico = (
                destinos["historico"]
                / f"{nome_base_historico}.zip"
            )
            arquivo_banco_atual = (
                destinos["banco_atual"]
                / "gal_sorotipo.csv"
            )
            arquivo_teste = (
                destinos["teste_soro"]
                / "gal_sorotipo-TESTE.csv"
            )

            self._criar_zip_historico_atomico(
                origem=arquivo_relatorio,
                destino=arquivo_historico,
                nome_csv=f"{nome_base_historico}.csv"
            )
            self._copiar_atomico(
                origem=arquivo_relatorio,
                destino=arquivo_banco_atual
            )
            self._copiar_atomico(
                origem=arquivo_relatorio,
                destino=arquivo_teste
            )
            self._remover_historicos_soltos(
                pasta=destinos["historico"],
                nome_base=nome_base_historico
            )

        return {
            "arquivo_original": origem,
            "arquivo_historico": arquivo_historico,
            "arquivo_banco_atual": arquivo_banco_atual,
            "arquivo_teste": arquivo_teste,
            "pasta_historico": destinos["historico"],
            "pasta_banco_atual": destinos["banco_atual"],
            "pasta_teste_soro": destinos["teste_soro"],
            "data_inicio": data_inicio,
            "data_fim": data_fim
        }

    def corresponde_ao_csv_vazio(
        self,
        caminho_arquivo: str | Path
    ) -> bool:
        """
        Compara somente os bytes do CSV com a assinatura de referencia.

        Nenhuma linha, coluna ou dado do relatorio e interpretado. Quando
        o GAL entrega um ZIP, o CSV e apenas extraido para que sua
        assinatura binaria seja calculada.
        """

        origem = Path(caminho_arquivo)

        if not origem.is_file():
            raise FileNotFoundError(
                f"O arquivo do GAL não foi encontrado: {origem}"
            )

        with tempfile.TemporaryDirectory(
            prefix="arbohub_gal_assinatura_"
        ) as pasta_temporaria:
            arquivo_relatorio = self._obter_relatorio(
                origem=origem,
                pasta_temporaria=Path(pasta_temporaria)
            )

            if arquivo_relatorio.suffix.casefold() != ".csv":
                return False

            return (
                self._calcular_sha256(arquivo_relatorio)
                == self.CSV_VAZIO_SHA256
            )

    @staticmethod
    def _calcular_sha256(caminho_arquivo: Path) -> str:
        assinatura = hashlib.sha256()

        with caminho_arquivo.open("rb") as arquivo:
            for bloco in iter(
                lambda: arquivo.read(1024 * 1024),
                b""
            ):
                assinatura.update(bloco)

        return assinatura.hexdigest()

    def _obter_relatorio(
        self,
        origem: Path,
        pasta_temporaria: Path
    ) -> Path:
        # XLSX tambem e um contêiner ZIP internamente. Quando a extensao
        # ja identifica uma planilha, ela deve ser preservada como o
        # proprio relatorio em vez de ser tratada como pacote do GAL.
        if origem.suffix.casefold() in self.EXTENSOES_RELATORIO:
            return origem

        if not zipfile.is_zipfile(origem):
            raise ValueError(
                "Formato de relatório do GAL não reconhecido. "
                "Use ZIP, CSV, XLSX, XLS, TXT ou DBF."
            )

        with zipfile.ZipFile(origem) as arquivo_zip:
            candidatos = [
                item
                for item in arquivo_zip.infolist()
                if (
                    not item.is_dir()
                    and Path(item.filename).suffix.casefold()
                    in self.EXTENSOES_RELATORIO
                    and not Path(item.filename).name.startswith(".")
                )
            ]

            if not candidatos:
                raise ValueError(
                    "O ZIP do GAL não contém CSV, XLSX, XLS, TXT "
                    "ou DBF."
                )

            candidatos.sort(
                key=lambda item: item.file_size,
                reverse=True
            )
            selecionado = candidatos[0]
            nome_seguro = Path(selecionado.filename).name
            destino = pasta_temporaria / nome_seguro

            with (
                arquivo_zip.open(selecionado) as origem_zip,
                destino.open("wb") as arquivo_destino
            ):
                shutil.copyfileobj(origem_zip, arquivo_destino)

        if not destino.is_file() or destino.stat().st_size <= 0:
            raise ValueError(
                "O relatório dentro do ZIP do GAL está vazio."
            )

        return destino

    def _criar_zip_historico_atomico(
        self,
        origem: Path,
        destino: Path,
        nome_csv: str
    ):
        temporario = destino.with_name(
            f".{destino.name}.arbohub_{os.getpid()}.tmp"
        )

        try:
            with zipfile.ZipFile(
                temporario,
                mode="w",
                compression=zipfile.ZIP_DEFLATED
            ) as arquivo_zip:
                arquivo_zip.write(origem, arcname=nome_csv)

            with zipfile.ZipFile(temporario) as arquivo_zip:
                membros = arquivo_zip.infolist()
                if len(membros) != 1 or membros[0].filename != nome_csv:
                    raise OSError(
                        "O ZIP semanal do GAL foi criado com uma "
                        "estrutura inesperada."
                    )
                if membros[0].file_size != origem.stat().st_size:
                    raise OSError(
                        "O CSV dentro do ZIP semanal ficou incompleto."
                    )
                if arquivo_zip.testzip() is not None:
                    raise OSError(
                        "O ZIP semanal do GAL falhou na validação."
                    )

            os.replace(temporario, destino)
        finally:
            try:
                if temporario.exists():
                    temporario.unlink()
            except OSError:
                pass

    def _remover_historicos_soltos(
        self,
        pasta: Path,
        nome_base: str
    ):
        for extensao in self.EXTENSOES_RELATORIO:
            legado = pasta / f"{nome_base}{extensao}"
            if legado.is_file():
                legado.unlink()

    def _copiar_atomico(self, origem: Path, destino: Path):
        temporario = destino.with_name(
            f".{destino.name}.arbohub_{os.getpid()}.tmp"
        )

        try:
            shutil.copy2(origem, temporario)

            if temporario.stat().st_size != origem.stat().st_size:
                raise OSError(
                    "A cópia do arquivo do GAL ficou incompleta."
                )

            os.replace(temporario, destino)
        finally:
            try:
                if temporario.exists():
                    temporario.unlink()
            except OSError:
                pass

    def _validar_pasta_gravavel(
        self,
        pasta: Path,
        rotulo: str
    ):
        if not os.access(pasta, os.R_OK | os.W_OK):
            raise PermissionError(
                f"Sem permissão de leitura e gravação em {rotulo}: "
                f"{pasta}"
            )
