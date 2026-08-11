from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path


class ArquivosGalService:
    """Organiza o relatorio do GAL sem ler seu conteudo clinico."""

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
        pasta_mes = self.pasta_historico_mes(data_referencia)
        pasta_mes.mkdir(parents=True, exist_ok=True)

        self._validar_pasta_gravavel(
            pasta_mes,
            "histórico mensal do GAL"
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
            "teste_soro": self.pasta_teste_soro
        }

    def processar_download(
        self,
        caminho_arquivo: str | Path,
        data_referencia: date | None = None
    ) -> dict[str, object]:
        """
        Preserva o arquivo original e atualiza o banco de teste.

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

        destinos = self.validar_destinos(data_referencia)
        with tempfile.TemporaryDirectory(
            prefix="arbohub_gal_conteudo_"
        ) as pasta_temporaria:
            arquivo_relatorio = self._obter_relatorio(
                origem=origem,
                pasta_temporaria=Path(pasta_temporaria)
            )
            arquivo_historico = self._copiar_para_historico(
                origem=origem,
                pasta_historico=destinos["historico"]
            )
            extensao = arquivo_relatorio.suffix.casefold()
            nome_final = f"gal_sorotipo-TESTE{extensao}"
            arquivo_teste = destinos["teste_soro"] / nome_final

            self._copiar_atomico(
                origem=arquivo_relatorio,
                destino=arquivo_teste
            )

        data_inicio, data_fim = self.intervalo_semanal(
            data_referencia
        )

        return {
            "arquivo_original": origem,
            "arquivo_historico": arquivo_historico,
            "arquivo_teste": arquivo_teste,
            "pasta_historico": destinos["historico"],
            "pasta_teste_soro": destinos["teste_soro"],
            "data_inicio": data_inicio,
            "data_fim": data_fim
        }

    def _copiar_para_historico(
        self,
        origem: Path,
        pasta_historico: Path
    ) -> Path:
        nome = origem.name or "relatorio_gal"
        destino = pasta_historico / nome

        if destino.exists():
            momento = datetime.now().strftime("%Y%m%d_%H%M%S")
            destino = pasta_historico / (
                f"{Path(nome).stem}_{momento}{Path(nome).suffix}"
            )

            contador = 2

            while destino.exists():
                destino = pasta_historico / (
                    f"{Path(nome).stem}_{momento}_{contador}"
                    f"{Path(nome).suffix}"
                )
                contador += 1

        self._copiar_atomico(origem, destino)
        return destino

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
