from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SelecaoDestinosBases:
    """Define os destinos que participarão de uma execução."""

    AGRAVO_DENGUE = "dengue"
    AGRAVO_CHIKUNGUNYA = "chikungunya"
    AGRAVOS_VALIDOS = frozenset({
        AGRAVO_DENGUE,
        AGRAVO_CHIKUNGUNYA
    })

    atualizar_historico: bool = True
    agravos_bases_dbf: frozenset[str] = field(
        default_factory=lambda: frozenset({
            SelecaoDestinosBases.AGRAVO_DENGUE,
            SelecaoDestinosBases.AGRAVO_CHIKUNGUNYA
        })
    )
    atualizar_bancos_atuais: bool = True

    def __post_init__(self):
        agravos = frozenset(
            str(agravo).strip().casefold()
            for agravo in self.agravos_bases_dbf
        )
        invalidos = agravos - self.AGRAVOS_VALIDOS

        if invalidos:
            raise ValueError(
                "Agravo inválido na seleção de Bases DBF: "
                + ", ".join(sorted(invalidos))
            )

        object.__setattr__(
            self,
            "agravos_bases_dbf",
            agravos
        )

        if not self.possui_destino:
            raise ValueError(
                "Selecione pelo menos um destino para a atualização."
            )

    @classmethod
    def completa(cls) -> "SelecaoDestinosBases":
        return cls()

    @classmethod
    def de_dict(
        cls,
        dados: dict[str, object] | None
    ) -> "SelecaoDestinosBases":
        if not dados:
            return cls.completa()

        return cls(
            atualizar_historico=bool(
                dados.get("atualizar_historico", True)
            ),
            agravos_bases_dbf=frozenset(
                dados.get(
                    "agravos_bases_dbf",
                    cls.AGRAVOS_VALIDOS
                )
            ),
            atualizar_bancos_atuais=bool(
                dados.get("atualizar_bancos_atuais", True)
            )
        )

    @property
    def possui_destino(self) -> bool:
        return bool(
            self.atualizar_historico
            or self.agravos_bases_dbf
            or self.atualizar_bancos_atuais
        )

    @property
    def esta_completa(self) -> bool:
        return bool(
            self.atualizar_historico
            and self.agravos_bases_dbf == self.AGRAVOS_VALIDOS
            and self.atualizar_bancos_atuais
        )

    @property
    def agravos_necessarios(self) -> frozenset[str]:
        if (
            self.atualizar_historico
            or self.atualizar_bancos_atuais
        ):
            return self.AGRAVOS_VALIDOS

        return self.agravos_bases_dbf

    def inclui_base_dbf(self, agravo: str) -> bool:
        return (
            str(agravo).strip().casefold()
            in self.agravos_bases_dbf
        )

    def para_dict(self) -> dict[str, object]:
        return {
            "atualizar_historico": self.atualizar_historico,
            "agravos_bases_dbf": tuple(
                sorted(self.agravos_bases_dbf)
            ),
            "atualizar_bancos_atuais": (
                self.atualizar_bancos_atuais
            )
        }

    def rotulos_resumo(self) -> tuple[str, ...]:
        itens: list[str] = []

        if self.atualizar_historico:
            itens.append("Histórico")

        if self.AGRAVO_DENGUE in self.agravos_bases_dbf:
            itens.append("Dengue DBF")

        if self.AGRAVO_CHIKUNGUNYA in self.agravos_bases_dbf:
            itens.append("Chikungunya DBF")

        if self.atualizar_bancos_atuais:
            itens.append("Bancos atuais")

        return tuple(itens)

    def resumo(self) -> str:
        return " + ".join(self.rotulos_resumo())
