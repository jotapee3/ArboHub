from app.services.arquivos_exportacao_dbf_service import (
    ArquivosExportacaoDbfService
)


def main():
    service = ArquivosExportacaoDbfService()

    try:
        destinos = service.caminhos_bancos_atuais()

        print(
            "Esta etapa atualizará somente Bancos_Atuais."
        )
        print()
        print("DENGUE:")
        print(destinos["dengue"])
        print()
        print("CHIKUNGUNYA:")
        print(destinos["chikungunya"])

        print()
        print(
            "Os nomes usam automaticamente o ano atual."
        )
        print(
            "Versões anteriores no padrão dengue_AAAA ou "
            "chiku_AAAA serão protegidas por backup e removidas "
            "somente depois da validação da nova dupla."
        )
        print()
        print(
            "As pastas Teste AB1 e Teste AB2 não serão alteradas."
        )

        confirmacao = input(
            "\nDigite ATUALIZAR BANCOS ATUAIS para continuar: "
        ).strip()

        if confirmacao != "ATUALIZAR BANCOS ATUAIS":
            print()
            print("Operação cancelada.")
            return

        resultado = (
            service.instalar_dbfs_bancos_atuais()
        )

        print()
        print(
            "Bancos_Atuais atualizado com sucesso."
        )

        print()
        print("DENGUE")
        print(
            "  Destino:",
            resultado["dengue"]["destino"]
        )
        print(
            "  Nome interno do ZIP:",
            resultado["dengue"]["nome_interno"]
        )
        print(
            "  Prefixo confirmado:",
            resultado["dengue"][
                "prefixo_confirmado"
            ]
        )
        print(
            "  Arquivos anteriores removidos:",
            (
                ", ".join(
                    resultado["dengue"][
                        "arquivos_anteriores_removidos"
                    ]
                )
                or "nenhum"
            )
        )
        print(
            "  Tamanho:",
            resultado["dengue"]["tamanho_bytes"],
            "bytes"
        )

        print()
        print("CHIKUNGUNYA")
        print(
            "  Destino:",
            resultado["chikungunya"]["destino"]
        )
        print(
            "  Nome interno do ZIP:",
            resultado[
                "chikungunya"
            ]["nome_interno"]
        )
        print(
            "  Prefixo confirmado:",
            resultado[
                "chikungunya"
            ]["prefixo_confirmado"]
        )
        print(
            "  Arquivos anteriores removidos:",
            (
                ", ".join(
                    resultado["chikungunya"][
                        "arquivos_anteriores_removidos"
                    ]
                )
                or "nenhum"
            )
        )
        print(
            "  Tamanho:",
            resultado[
                "chikungunya"
            ]["tamanho_bytes"],
            "bytes"
        )

        print()
        print(
            "Ano aplicado:",
            resultado["ano"]
        )
        print(
            "Pasta temporária excluída:",
            resultado["pasta_temporaria_excluida"]
        )
        print(
            "Registros internos interpretados:",
            resultado["registros_lidos"]
        )
        print(
            "Pastas de teste alteradas:",
            resultado["pastas_teste_alteradas"]
        )

    except Exception as erro:
        print()
        print(
            "Não foi possível atualizar Bancos_Atuais."
        )
        print(f"Detalhes técnicos: {erro}")
        print()
        print(
            "Quando possível, os arquivos anteriores foram "
            "restaurados automaticamente."
        )


if __name__ == "__main__":
    main()