from app.automation.sinan.navegador_sinan import (
    NavegadorSinan
)
from app.automation.sinan.verificacao_obitos import (
    VerificacaoObitos
)
from app.services.checkpoint_service import (
    CheckpointService
)


def exibir_resultado_tecnico(resultado: dict):
    print(
        "Confirmação técnica:",
        resultado["confirmacao"]
    )
    print(
        "Conteúdo das linhas lido:",
        resultado["dados_lidos"]
    )


def main():
    navegador = NavegadorSinan()
    checkpoints = CheckpointService()

    try:
        print("Abrindo o SINAN...")
        pagina = navegador.abrir()

        print()
        print("Faça o login manualmente no navegador.")
        print("Nenhuma credencial será registrada.")
        print()

        navegador.aguardar_login_manual(
            tempo_limite_segundos=600
        )

        print("Login detectado com sucesso.")
        print()

        verificacao = VerificacaoObitos(
            pagina
        )

        print(
            "Abrindo Consulta → Notificação Individual..."
        )
        verificacao.abrir_notificacao_individual()

        # ------------------------------------------------------
        # Dengue
        # ------------------------------------------------------

        checkpoints.marcar_obito_iniciado(
            CheckpointService.AGRAVO_DENGUE
        )

        print()
        print("Executando a consulta de Dengue...")

        resultado_dengue = (
            verificacao.executar_consulta_por_agravo(
                agravo="Dengue"
            )
        )

        checkpoints.marcar_obito_aguardando_conferencia(
            CheckpointService.AGRAVO_DENGUE
        )

        print("Consulta de Dengue concluída.")
        exibir_resultado_tecnico(
            resultado_dengue
        )
        print(
            "Aguardando confirmação na janela "
            "exibida sobre o SINAN..."
        )

        confirmacao_dengue = (
            verificacao.solicitar_confirmacao_conferencia(
                agravo="Dengue",
                acao_seguinte="consultar Chikungunya"
            )
        )

        checkpoints.marcar_obito_concluido(
            agravo=CheckpointService.AGRAVO_DENGUE,
            resultado_comparacao=(
                confirmacao_dengue[
                    "resultado_comparacao"
                ]
            ),
            observacao=confirmacao_dengue["observacao"]
        )

        print("Dengue confirmada pelo usuário.")
        print(
            "Resultado registrado:",
            confirmacao_dengue[
                "resultado_comparacao"
            ]
        )

        # ------------------------------------------------------
        # Chikungunya: reutiliza o critério já adicionado
        # ------------------------------------------------------

        checkpoints.marcar_obito_iniciado(
            CheckpointService.AGRAVO_CHIKUNGUNYA
        )

        print()
        print(
            "Alterando somente o agravo para Chikungunya..."
        )
        print(
            "O critério de óbito já adicionado será reutilizado."
        )

        resultado_chikungunya = (
            verificacao.trocar_agravo_e_pesquisar(
                agravo="Chikungunya"
            )
        )

        checkpoints.marcar_obito_aguardando_conferencia(
            CheckpointService.AGRAVO_CHIKUNGUNYA
        )

        print("Consulta de Chikungunya concluída.")
        print(
            "Critério reutilizado:",
            resultado_chikungunya[
                "criterio_reutilizado"
            ]
        )
        exibir_resultado_tecnico(
            resultado_chikungunya
        )
        print(
            "Aguardando confirmação na janela "
            "exibida sobre o SINAN..."
        )

        confirmacao_chikungunya = (
            verificacao.solicitar_confirmacao_conferencia(
                agravo="Chikungunya",
                acao_seguinte="finalizar"
            )
        )

        checkpoints.marcar_obito_concluido(
            agravo=(
                CheckpointService.AGRAVO_CHIKUNGUNYA
            ),
            resultado_comparacao=(
                confirmacao_chikungunya[
                    "resultado_comparacao"
                ]
            ),
            observacao=(
                confirmacao_chikungunya["observacao"]
            )
        )

        print()
        print("Chikungunya confirmada pelo usuário.")
        print(
            "Resultado registrado:",
            confirmacao_chikungunya[
                "resultado_comparacao"
            ]
        )
        print()
        print(
            "Rotina de Dengue e Chikungunya "
            "concluída com sucesso."
        )
        print(
            "As observações foram registradas no banco local "
            "do ArboHub para o relatório futuro."
        )
        print(
            "Nenhum conteúdo das linhas do SINAN foi "
            "lido ou salvo pela automação."
        )

    except KeyboardInterrupt:
        print()
        print("Teste interrompido pelo usuário.")

    except Exception as erro:
        print()
        print("Não foi possível concluir o teste.")
        print(f"Detalhes técnicos: {erro}")

        input(
            "\nPressione Enter para fechar o navegador..."
        )

    finally:
        navegador.fechar()
        print("Navegador fechado.")


if __name__ == "__main__":
    main()