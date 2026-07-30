from app.services.exportacao_dbf_service import (
    ExportacaoDbfService
)


def main():
    service = ExportacaoDbfService()

    print(
        "Este registro é necessário apenas para solicitações "
        "criadas antes do salvamento automático."
    )
    print()

    numero_dengue = input(
        "Número da solicitação de DENGUE: "
    ).strip()

    numero_chikungunya = input(
        "Número da solicitação de CHIKUNGUNYA: "
    ).strip()

    if numero_dengue == numero_chikungunya:
        raise ValueError(
            "Os dois números precisam ser diferentes."
        )

    lote_id = service.criar_lote()

    service.salvar_solicitacao(
        lote_id=lote_id,
        agravo=ExportacaoDbfService.AGRAVO_DENGUE,
        numero_solicitacao=numero_dengue
    )
    service.salvar_solicitacao(
        lote_id=lote_id,
        agravo=(
            ExportacaoDbfService.AGRAVO_CHIKUNGUNYA
        ),
        numero_solicitacao=numero_chikungunya
    )

    print()
    print("Solicitações registradas com sucesso.")
    print("Lote local:", lote_id)
    print("DENGUE:", numero_dengue)
    print("CHIKUNGUNYA:", numero_chikungunya)
    print()
    print(
        "As próximas consultas poderão recuperar os números "
        "automaticamente do banco local do ArboHub."
    )


if __name__ == "__main__":
    main()