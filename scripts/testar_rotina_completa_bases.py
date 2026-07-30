from app.automation.sinan.exportacao_bases import (
    ExportacaoBasesDbf
)
from app.automation.sinan.navegador_sinan import (
    NavegadorSinan
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

    if evento.dados:
        if "numero_solicitacao" in evento.dados:
            print(
                "    Número:",
                evento.dados[
                    "numero_solicitacao"
                ]
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
    navegador = None
    exportacao = None

    try:
        estado = rotina.avaliar_estado_do_dia()

        print("Rotina diária completa das bases")
        print()
        print(
            "Data:",
            estado["data_referencia"]
        )

        lote_completo = estado["lote_completo"]
        lote_parcial = estado["lote_parcial"]

        if lote_completo is not None:
            print()
            print(
                "O par de solicitações de hoje já está completo."
            )
            print(
                "Dengue:",
                lote_completo[
                    "dengue"
                ]["numero_solicitacao"]
            )
            print(
                "Chikungunya:",
                lote_completo[
                    "chikungunya"
                ]["numero_solicitacao"]
            )
            print(
                "Nenhuma nova solicitação será criada."
            )

        elif lote_parcial is not None:
            print()
            print(
                "Foi encontrado um lote parcial de hoje."
            )

            if lote_parcial["dengue"] is not None:
                print(
                    "Dengue já salva:",
                    lote_parcial[
                        "dengue"
                    ]["numero_solicitacao"]
                )

            if (
                lote_parcial["chikungunya"]
                is not None
            ):
                print(
                    "Chikungunya já salva:",
                    lote_parcial[
                        "chikungunya"
                    ]["numero_solicitacao"]
                )

            print(
                "Será criada somente a solicitação faltante:"
            )
            print(
                ", ".join(
                    estado[
                        "solicitacoes_faltantes"
                    ]
                )
            )

        else:
            print()
            print(
                "Ainda não existem solicitações para hoje."
            )
            print(
                "Serão criadas solicitações REAIS de Dengue "
                "e Chikungunya."
            )

        print()
        print(
            "Histórico completo de hoje:",
            estado["historico_completo"]
        )
        print(
            "Navegador necessário:",
            estado["requer_navegador"]
        )

        print()
        print(
            "Ao final, a rotina atualizará com backup:"
        )
        print(
            "  • Histórico dos ZIPs"
        )
        print(
            "  • Teste AB1 e Teste AB2"
        )
        print(
            "  • Documents\\SINAN\\Bancos_Atuais"
        )

        solicitacoes_autorizadas = False

        if estado["requer_novas_solicitacoes"]:
            confirmacao = input(
                "\nDigite SOLICITAR E EXECUTAR para autorizar "
                "as solicitações reais e continuar: "
            ).strip()

            if confirmacao != "SOLICITAR E EXECUTAR":
                print()
                print(
                    "Operação cancelada. Nenhuma nova "
                    "solicitação foi criada."
                )
                return

            solicitacoes_autorizadas = True

        else:
            confirmacao = input(
                "\nDigite EXECUTAR ROTINA para continuar: "
            ).strip()

            if confirmacao != "EXECUTAR ROTINA":
                print()
                print("Operação cancelada.")
                return

        if estado["requer_navegador"]:
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
            print()

            navegador.aguardar_login_manual(
                tempo_limite_segundos=600
            )

            print("Login detectado com sucesso.")
            print()

            exportacao = ExportacaoBasesDbf(
                pagina
            )

        print("Iniciando a rotina completa...")
        print()

        resultado = rotina.executar_rotina_completa(
            exportacao=exportacao,
            solicitacoes_autorizadas=(
                solicitacoes_autorizadas
            ),
            usar_historico_existente=True,
            substituir_historico=False,
            atualizar_pastas_teste=True,
            atualizar_bancos_atuais=True,
            intervalo_consulta_segundos=15,
            tempo_limite_segundos=1800,
            ao_evento=exibir_evento
        )

        solicitacoes = resultado["solicitacoes"]

        print()
        print("Rotina completa concluída com sucesso.")
        print(
            "Solicitações reutilizadas:",
            solicitacoes["reutilizado"]
        )
        print(
            "Lote parcial retomado:",
            solicitacoes["retomado_parcial"]
        )
        print(
            "Novas solicitações criadas:",
            (
                ", ".join(
                    solicitacoes[
                        "novas_solicitacoes"
                    ]
                )
                or "nenhuma"
            )
        )
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

    except KeyboardInterrupt:
        print()
        print("Rotina interrompida pelo usuário.")

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