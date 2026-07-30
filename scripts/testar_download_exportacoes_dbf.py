from datetime import date

from app.automation.sinan.exportacao_bases import (
    ExportacaoBasesDbf
)
from app.automation.sinan.navegador_sinan import (
    NavegadorSinan
)
from app.services.arquivos_exportacao_dbf_service import (
    ArquivosExportacaoDbfService
)
from app.services.exportacao_dbf_service import (
    ExportacaoDbfService
)


def main():
    navegador = NavegadorSinan(
        permitir_downloads=True
    )
    registro_service = ExportacaoDbfService()
    arquivos_service = (
        ArquivosExportacaoDbfService()
    )

    temporarios = []
    pasta_lote = None

    try:
        lote = (
            registro_service.obter_lote_completo_do_dia()
        )

        if lote is None:
            raise RuntimeError(
                "Nenhum lote completo de Dengue e "
                "Chikungunya foi encontrado para hoje."
            )

        data_referencia = date.fromisoformat(
            lote["data_referencia"]
        )

        numero_dengue = (
            lote["dengue"]["numero_solicitacao"]
        )
        numero_chikungunya = (
            lote["chikungunya"]["numero_solicitacao"]
        )

        print("Lote de hoje localizado.")
        print(
            "DENGUE:",
            numero_dengue
        )
        print(
            "CHIKUNGUNYA:",
            numero_chikungunya
        )

        print()
        print("Abrindo o SINAN...")
        pagina = navegador.abrir()

        print()
        print("Faça o login manualmente no navegador.")
        print("Nenhuma credencial será registrada.")
        print()

        navegador.aguardar_login_manual(
            tempo_limite_segundos=600
        )

        exportacao = ExportacaoBasesDbf(
            pagina
        )

        print(
            "Abrindo Exportação → "
            "Consultar Exportações DBF..."
        )
        exportacao.abrir_consulta_exportacoes_dbf()

        print()
        print(
            "Confirmando que as duas exportações "
            "estão disponíveis..."
        )

        resultado_pronto = (
            exportacao.aguardar_solicitacoes_prontas(
                numero_dengue=numero_dengue,
                numero_chikungunya=(
                    numero_chikungunya
                ),
                intervalo_segundos=15,
                tempo_limite_segundos=1800
            )
        )

        print(
            "Ambas prontas:",
            resultado_pronto["ambas_prontas"]
        )

        pasta_lote = (
            arquivos_service.criar_pasta_lote(
                lote_id=lote["lote_id"],
                data_referencia=data_referencia
            )
        )

        destino_dengue = (
            arquivos_service.caminho_historico(
                agravo=(
                    ArquivosExportacaoDbfService
                    .AGRAVO_DENGUE
                ),
                data_referencia=data_referencia
            )
        )
        destino_chikungunya = (
            arquivos_service.caminho_historico(
                agravo=(
                    ArquivosExportacaoDbfService
                    .AGRAVO_CHIKUNGUNYA
                ),
                data_referencia=data_referencia
            )
        )

        print()
        print(
            "Os downloads serão validados em uma pasta "
            "temporária privada:"
        )
        print(pasta_lote)

        print()
        print("Depois serão arquivados em:")
        print("DENGUE:", destino_dengue)
        print(
            "CHIKUNGUNYA:",
            destino_chikungunya
        )

        print()
        print(
            "A pasta temporária será excluída somente depois "
            "que os dois ZIPs chegarem corretamente ao histórico."
        )
        print(
            "Nenhum DBF será extraído ou substituído nesta etapa."
        )

        confirmacao = input(
            "\nDigite BAIXAR para iniciar: "
        ).strip()

        if confirmacao != "BAIXAR":
            print()
            print(
                "Downloads cancelados pelo usuário."
            )
            return

        # ------------------------------------------------------
        # Dengue
        # ------------------------------------------------------

        temporario_dengue = (
            arquivos_service.caminho_temporario(
                pasta_lote=pasta_lote,
                agravo=(
                    ArquivosExportacaoDbfService
                    .AGRAVO_DENGUE
                )
            )
        )
        temporarios.append(
            temporario_dengue
        )

        print()
        print("Baixando DENGUE...")

        exportacao.baixar_exportacao_dbf(
            numero_solicitacao=numero_dengue,
            caminho_destino=temporario_dengue
        )

        dengue = (
            arquivos_service.validar_e_finalizar(
                caminho_temporario=temporario_dengue,
                pasta_lote=pasta_lote,
                agravo=(
                    ArquivosExportacaoDbfService
                    .AGRAVO_DENGUE
                ),
                data_referencia=data_referencia
            )
        )

        # ------------------------------------------------------
        # Chikungunya
        # ------------------------------------------------------

        temporario_chiku = (
            arquivos_service.caminho_temporario(
                pasta_lote=pasta_lote,
                agravo=(
                    ArquivosExportacaoDbfService
                    .AGRAVO_CHIKUNGUNYA
                )
            )
        )
        temporarios.append(
            temporario_chiku
        )

        print("Baixando CHIKUNGUNYA...")

        exportacao.baixar_exportacao_dbf(
            numero_solicitacao=(
                numero_chikungunya
            ),
            caminho_destino=temporario_chiku
        )

        chikungunya = (
            arquivos_service.validar_e_finalizar(
                caminho_temporario=temporario_chiku,
                pasta_lote=pasta_lote,
                agravo=(
                    ArquivosExportacaoDbfService
                    .AGRAVO_CHIKUNGUNYA
                ),
                data_referencia=data_referencia
            )
        )

        print()
        print("Os dois ZIPs foram baixados e validados.")

        substituir = False

        if (
            destino_dengue.exists()
            or destino_chikungunya.exists()
        ):
            print()
            print(
                "Já existe arquivo histórico para esta data."
            )
            print(
                "Nenhum arquivo será substituído sem "
                "confirmação explícita."
            )

            confirmacao_substituir = input(
                "\nDigite SUBSTITUIR para trocar a dupla "
                "existente: "
            ).strip()

            if confirmacao_substituir != "SUBSTITUIR":
                print()
                print(
                    "Arquivamento cancelado. "
                    "Os ZIPs validados permanecerão no staging:"
                )
                print(pasta_lote)
                return

            substituir = True

        resultado_arquivo = (
            arquivos_service.arquivar_lote(
                caminho_dengue=dengue["caminho"],
                caminho_chikungunya=(
                    chikungunya["caminho"]
                ),
                pasta_lote=pasta_lote,
                data_referencia=data_referencia,
                substituir_existentes=substituir
            )
        )

        print()
        print("Histórico atualizado com sucesso.")

        print()
        print("DENGUE")
        print(
            "  Arquivo:",
            resultado_arquivo[
                "dengue"
            ]["caminho"]
        )
        print(
            "  Prefixo confirmado:",
            resultado_arquivo[
                "dengue"
            ]["prefixo_confirmado"]
        )

        print()
        print("CHIKUNGUNYA")
        print(
            "  Arquivo:",
            resultado_arquivo[
                "chikungunya"
            ]["caminho"]
        )
        print(
            "  Prefixo confirmado:",
            resultado_arquivo[
                "chikungunya"
            ]["prefixo_confirmado"]
        )

        print()
        print(
            "Pasta temporária excluída:",
            resultado_arquivo[
                "pasta_temporaria_excluida"
            ]
        )
        print(
            "Arquivos extraídos:",
            False
        )
        print(
            "Bancos existentes substituídos:",
            False
        )
        print(
            "DBFs copiados para F:",
            False
        )

        input(
            "\nPressione Enter para fechar o navegador..."
        )

    except KeyboardInterrupt:
        print()
        print("Teste interrompido pelo usuário.")

    except Exception as erro:
        print()
        print("Não foi possível concluir o teste.")
        print(f"Detalhes técnicos: {erro}")

        if pasta_lote is not None:
            print()
            print(
                "Por segurança, a pasta temporária foi mantida:"
            )
            print(pasta_lote)

        input(
            "\nPressione Enter para fechar o navegador..."
        )

    finally:
        # Remove apenas downloads incompletos.
        # ZIPs validados são mantidos caso o arquivamento falhe.
        for temporario in temporarios:
            try:
                arquivos_service.limpar_temporario(
                    temporario
                )
            except Exception:
                pass

        navegador.fechar()
        print("Navegador fechado.")


if __name__ == "__main__":
    main()