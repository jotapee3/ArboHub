from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class SemanaEpidemiologica:
    """Intervalo oficial de uma semana epidemiológica."""

    ano: int
    numero: int
    data_inicial: date
    data_final: date


class CalendarioEpidemiologico:
    """
    Calcula semanas epidemiológicas sem depender de acesso à internet.

    A semana começa no domingo e termina no sábado. A semana 1 é aquela
    que contém a maior quantidade de dias de janeiro, equivalendo à
    semana que contém 4 de janeiro.
    """

    @staticmethod
    def inicio_do_ano(ano: int) -> date:
        ano = CalendarioEpidemiologico._validar_ano(ano)
        quatro_de_janeiro = date(ano, 1, 4)
        dias_desde_domingo = (
            quatro_de_janeiro.weekday() + 1
        ) % 7
        return quatro_de_janeiro - timedelta(
            days=dias_desde_domingo
        )

    @classmethod
    def quantidade_de_semanas(cls, ano: int) -> int:
        ano = cls._validar_ano(ano)
        inicio_atual = cls.inicio_do_ano(ano)
        inicio_seguinte = cls.inicio_do_ano(ano + 1)
        return (inicio_seguinte - inicio_atual).days // 7

    @classmethod
    def obter_semana(
        cls,
        ano: int,
        numero: int,
    ) -> SemanaEpidemiologica:
        ano = cls._validar_ano(ano)
        try:
            numero = int(numero)
        except (TypeError, ValueError) as erro:
            raise ValueError(
                "O número da semana epidemiológica é inválido."
            ) from erro

        quantidade = cls.quantidade_de_semanas(ano)
        if numero < 1 or numero > quantidade:
            raise ValueError(
                f"O ano epidemiológico de {ano} possui "
                f"{quantidade} semanas."
            )

        data_inicial = cls.inicio_do_ano(ano) + timedelta(
            weeks=numero - 1
        )
        return SemanaEpidemiologica(
            ano=ano,
            numero=numero,
            data_inicial=data_inicial,
            data_final=data_inicial + timedelta(days=6),
        )

    @staticmethod
    def _validar_ano(ano: int) -> int:
        try:
            ano = int(ano)
        except (TypeError, ValueError) as erro:
            raise ValueError(
                "O ano epidemiológico é inválido."
            ) from erro

        if ano < 2 or ano > 9998:
            raise ValueError(
                "O ano epidemiológico deve estar entre 2 e 9998."
            )
        return ano
