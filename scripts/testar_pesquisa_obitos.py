from app.automation.sinan.navegador_sinan import (
    NavegadorSinan
)
from app.automation.sinan.verificacao_obitos import (
    VerificacaoObitos
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

        print("Preenchendo período e datas...")
        verificacao.preencher_periodo_e_datas()

        print(
            "Selecionando Dengue e "
            "Notificação ou Residência..."
        )
        verificacao.preencher_agravo_e_residencia(
            agravo="Dengue"
        )

        print(
            "Selecionando Evolução e "
            "2 - Óbito por Agravo..."
        )
        verificacao.preencher_criterio_obito()

        print("Adicionando o critério...")
        verificacao.adicionar_criterio_obito()

        print("Executando a pesquisa...")
        resultado = verificacao.pesquisar_obitos()

        print()
        print("Pesquisa concluída com sucesso.")
        print(
            "Confirmação técnica:",
            resultado["confirmacao"]
        )
        print(
            "Conteúdo das linhas lido:",
            resultado["dados_lidos"]
        )
        print()
        print(
            "Nenhuma credencial ou informação pessoal "
            "foi impressa ou salva."
        )

        input(
            "\nConfira o resultado visualmente e pressione "
            "Enter para fechar..."
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