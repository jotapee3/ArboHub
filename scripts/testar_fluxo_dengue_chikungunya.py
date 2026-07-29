from app.automation.sinan.navegador_sinan import (
    NavegadorSinan
)
from app.automation.sinan.verificacao_obitos import (
    VerificacaoObitos
)


def aguardar_confirmacao_zero(
    agravo: str,
    mensagem_continuacao: str
):
    print()
    print(
        f"Confira visualmente os resultados de {agravo} "
        "no navegador."
    )
    print(
        "O ArboHub não leu nem registrou o conteúdo "
        "das linhas apresentadas."
    )
    print()

    while True:
        resposta = input(
            f"Pressione 0 para {mensagem_continuacao}: "
        ).strip()

        if resposta == "0":
            return

        print(
            "Comando inválido. Digite somente 0 "
            "e pressione Enter."
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

        print()
        print("Executando a consulta de Dengue...")

        resultado_dengue = (
            verificacao.executar_consulta_por_agravo(
                agravo="Dengue"
            )
        )

        print("Consulta de Dengue concluída.")
        exibir_resultado_tecnico(
            resultado_dengue
        )

        aguardar_confirmacao_zero(
            agravo="Dengue",
            mensagem_continuacao=(
                "confirmar Dengue e iniciar Chikungunya"
            )
        )

        # ------------------------------------------------------
        # Limpeza e Chikungunya
        # ------------------------------------------------------

        print()
        print(
            "Limpando a consulta anterior e preparando "
            "Chikungunya..."
        )

        verificacao.limpar_consulta()

        print("Consulta anterior limpa com sucesso.")
        print()
        print("Executando a consulta de Chikungunya...")

        resultado_chikungunya = (
            verificacao.executar_consulta_por_agravo(
                agravo="Chikungunya"
            )
        )

        print("Consulta de Chikungunya concluída.")
        exibir_resultado_tecnico(
            resultado_chikungunya
        )

        aguardar_confirmacao_zero(
            agravo="Chikungunya",
            mensagem_continuacao=(
                "confirmar Chikungunya e finalizar a rotina"
            )
        )

        print()
        print(
            "Rotina de Dengue e Chikungunya "
            "concluída com sucesso."
        )
        print(
            "Nenhuma credencial ou informação pessoal "
            "foi impressa ou salva."
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