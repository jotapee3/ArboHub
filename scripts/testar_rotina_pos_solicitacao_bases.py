from app.automation.sinan.exportacao_bases import (
    ExportacaoBasesDbf
)
from app.automation.sinan.navegador_sinan import (
    NavegadorSinan
)
from app.services.arquivos_exportacao_dbf_service import (
    ArquivosExportacaoDbfService
)
from app.services.rotina_bases_service import (
    EventoRotinaBases,
    RotinaBasesService
)


def exibir_evento(
    evento: EventoRotinaBases
):
    marcador = {
        "iniciada": "→",
        "em_andamento": "…",
        "concluida": "✓",
        "ignorada": "○"
    }.get(
        evento.estado,
        "-"
    )

    print(
        f"{marcador} "
        f"[{evento.etapa}] "
        f"{evento.mensagem}"
    )

    if evento.etapa == "processamento":
        dengue = evento.dados.get("dengue")
        chikungunya = evento.dados.get(
            "chikungunya"
        )

        if dengue and chikungunya:
            print(
                "    Dengue:",
                dengue["status"],
                "- link:",
                dengue["link_disponivel"]
            )
            print(
                "    Chikungunya:",
                chikungunya["status"],
                "- link:",
                chikungunya["link_disponivel"]
            )


def main():
    rotina = RotinaBasesService()
    arquivos = ArquivosExportacaoDbfService()

    navegador = None
    exportacao = None

    try:
        lote = (
            rotina.registro_service
            .obter_lote_completo_do_dia()
        )

        if lote is None:
            raise RuntimeError(
                "Nenhum lote completo foi encontrado para hoje. "
                "Execute primeiro as solicitações de Dengue e "
                "Chikungunya."
            )

        caminhos_historico = {
            "dengue": arquivos.caminho_historico(
                agravo=(
                    ArquivosExportacaoDbfService
                    .AGRAVO_DENGUE
                )
            ),
            "chikungunya": arquivos.caminho_historico(
                agravo=(
                    ArquivosExportacaoDbfService
                    .AGRAVO_CHIKUNGUNYA
                )
            )
        }

        historico_completo = all(
            caminho.exists()
            for caminho in caminhos_historico.values()
        )

        print("Rotina unificada pós-solicitação")
        print()
        print(
            "Dengue:",
            lote["dengue"]["numero_solicitacao"]
        )
        print(
            "Chikungunya:",
            lote["chikungunya"][
                "numero_solicitacao"
            ]
        )

        print()
        print("Histórico de hoje:")
        print(
            "  Dengue:",
            caminhos_historico["dengue"]
        )
        print(
            "  Chikungunya:",
            caminhos_historico[
                "chikungunya"
            ]
        )

        if historico_completo:
            print()
            print(
                "Os dois ZIPs já existem. O navegador e os "
                "downloads serão ignorados após a validação."
            )
        else:
            print()
            print(
                "A dupla histórica ainda não está completa. "
                "Será necessário abrir o SINAN e baixar os ZIPs."
            )

        print()
        print(
            "A execução atualizará, com backup e validação:"
        )
        print(
            "  • Teste AB1 e Teste AB2"
        )
        print(
            "  • Documents\\SINAN\\Bancos_Atuais"
        )

        confirmacao = input(
            "\nDigite EXECUTAR ROTINA para continuar: "
        ).strip()

        if confirmacao != "EXECUTAR ROTINA":
            print()
            print("Operação cancelada.")
            return

        if not historico_completo:
            navegador = NavegadorSinan(
                permitir_downloads=True
            )

            print()
            print("Abrindo o SINAN...")
            pagina = navegador.abrir()

            print()
            print(
                "Faça o login manualmente no navegador."
            )
            print(
                "Nenhuma credencial será registrada."
            )

            navegador.aguardar_login_manual(
                tempo_limite_segundos=600
            )

            exportacao = ExportacaoBasesDbf(
                pagina
            )

        print()
        print("Iniciando rotina...")
        print()

        resultado = rotina.executar_pos_solicitacao(
            exportacao=exportacao,
            usar_historico_existente=True,
            substituir_historico=False,
            atualizar_pastas_teste=True,
            atualizar_bancos_atuais=True,
            intervalo_consulta_segundos=15,
            tempo_limite_segundos=1800,
            ao_evento=exibir_evento
        )

        print()
        print("Rotina concluída com sucesso.")
        print(
            "Histórico reutilizado:",
            resultado["historico"].get(
                "reutilizado",
                False
            )
        )
        print(
            "Pastas de teste atualizadas:",
            resultado["pastas_teste"] is not None
        )
        print(
            "Bancos_Atuais atualizado:",
            resultado["bancos_atuais"] is not None
        )
        print(
            "Dados de pacientes lidos:",
            resultado[
                "dados_de_pacientes_lidos"
            ]
        )

    except Exception as erro:
        print()
        print("Não foi possível concluir a rotina.")
        print(f"Detalhes técnicos: {erro}")

    finally:
        if navegador is not None:
            navegador.fechar()
            print("Navegador fechado.")


if __name__ == "__main__":
    main()