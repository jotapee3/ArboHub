from app.services.arquivos_exportacao_dbf_service import (
    ArquivosExportacaoDbfService
)


def main():
    service = ArquivosExportacaoDbfService()

    try:
        print(
            "Validando a extração dos ZIPs históricos de hoje..."
        )
        print()
        print(
            "Nenhum arquivo será copiado para F: e nenhum "
            "Banco_Atual será substituído."
        )

        resultado = (
            service.validar_extracao_historico()
        )

        print()
        print("Extração temporária validada com sucesso.")

        print()
        print("DENGUE")
        print(
            "  ZIP:",
            resultado["dengue"]["zip_origem"]
        )
        print(
            "  Nome interno:",
            resultado["dengue"]["nome_interno"]
        )
        print(
            "  Nome preparado:",
            resultado["dengue"]["nome_preparado"]
        )
        print(
            "  Tamanho:",
            resultado["dengue"]["tamanho_bytes"],
            "bytes"
        )
        print(
            "  Prefixo confirmado:",
            resultado["dengue"]["prefixo_confirmado"]
        )

        print()
        print("CHIKUNGUNYA")
        print(
            "  ZIP:",
            resultado["chikungunya"]["zip_origem"]
        )
        print(
            "  Nome interno:",
            resultado["chikungunya"]["nome_interno"]
        )
        print(
            "  Nome preparado:",
            resultado[
                "chikungunya"
            ]["nome_preparado"]
        )
        print(
            "  Tamanho:",
            resultado[
                "chikungunya"
            ]["tamanho_bytes"],
            "bytes"
        )
        print(
            "  Prefixo confirmado:",
            resultado[
                "chikungunya"
            ]["prefixo_confirmado"]
        )

        print()
        print(
            "Pasta temporária excluída:",
            resultado["pasta_temporaria_excluida"]
        )
        print(
            "Registros internos lidos:",
            resultado["registros_lidos"]
        )
        print(
            "Copiado para F:",
            resultado["copiado_para_f"]
        )
        print(
            "Bancos_Atuais substituídos:",
            resultado[
                "bancos_atuais_substituidos"
            ]
        )

    except Exception as erro:
        print()
        print("Não foi possível validar a extração.")
        print(f"Detalhes técnicos: {erro}")


if __name__ == "__main__":
    main()