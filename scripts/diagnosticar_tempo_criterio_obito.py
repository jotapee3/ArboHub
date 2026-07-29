from __future__ import annotations

from functools import wraps
from time import perf_counter

from app.automation.sinan.navegador_sinan import (
    NavegadorSinan
)
from app.automation.sinan.verificacao_obitos import (
    VerificacaoObitos
)


METRICAS: dict[str, dict[str, float | int]] = {}

METODOS_MONITORADOS = [
    "abrir_notificacao_individual",
    "_abrir_menu_consulta",
    "_aguardar_formulario_consulta",
    "preencher_periodo_e_datas",
    "_garantir_periodo_e_datas",
    "preencher_agravo_e_residencia",
    "_selecionar_agravo_combo",
    "_agravo_esta_selecionado",
    "_selecionar_notificacao_ou_residencia",
    "_localizacao_esta_selecionada",
    "_sincronizar_processamento_relevante",
    "_aguardar_fim_processamento",
    "_processamento_sinan_visivel",
    "_confirmar_rapido",
    "preencher_criterio_obito",
    "_garantir_filtros_basicos_rapido",
    "_selecionar_campo_evolucao",
    "_evolucao_esta_selecionada",
    "_aguardar_opcao_em_select",
    "_selecionar_criterio_obito_por_agravo",
    "_criterio_obito_esta_selecionado",
    "_estado_final_esta_correto",
    "_localizar_contexto_formulario",
    "_select_tem_opcao_selecionada",
    "_texto_existe_no_contexto",
]


def _registrar_tempo(
    nome: str,
    duracao: float
):
    metrica = METRICAS.setdefault(
        nome,
        {
            "chamadas": 0,
            "total": 0.0,
            "maximo": 0.0
        }
    )

    metrica["chamadas"] = int(
        metrica["chamadas"]
    ) + 1

    metrica["total"] = float(
        metrica["total"]
    ) + duracao

    metrica["maximo"] = max(
        float(metrica["maximo"]),
        duracao
    )


def _criar_wrapper(
    nome: str,
    metodo_original
):
    @wraps(metodo_original)
    def wrapper(self, *args, **kwargs):
        inicio = perf_counter()

        try:
            return metodo_original(
                self,
                *args,
                **kwargs
            )

        finally:
            duracao = perf_counter() - inicio

            _registrar_tempo(
                nome=nome,
                duracao=duracao
            )

            # Mostra imediatamente qualquer chamada lenta.
            if duracao >= 1.0:
                print(
                    f"[TEMPO] {nome}: "
                    f"{duracao:.2f} s"
                )

    return wrapper


def _instalar_medidores():
    for nome in METODOS_MONITORADOS:
        metodo = getattr(
            VerificacaoObitos,
            nome,
            None
        )

        if metodo is None:
            continue

        setattr(
            VerificacaoObitos,
            nome,
            _criar_wrapper(
                nome=nome,
                metodo_original=metodo
            )
        )


def _mostrar_resumo(
    tempo_total_fluxo: float
):
    print()
    print("=" * 68)
    print("RESUMO DE TEMPO DA AUTOMAÇÃO")
    print("=" * 68)
    print(
        f"Tempo total na página do SINAN: "
        f"{tempo_total_fluxo:.2f} s"
    )
    print()
    print(
        f"{'Método':42} "
        f"{'Chamadas':>8} "
        f"{'Total':>8} "
        f"{'Máximo':>8}"
    )
    print("-" * 68)

    ordenadas = sorted(
        METRICAS.items(),
        key=lambda item: float(
            item[1]["total"]
        ),
        reverse=True
    )

    for nome, metrica in ordenadas:
        total = float(metrica["total"])

        # Ignora métodos praticamente instantâneos.
        if total < 0.10:
            continue

        chamadas = int(
            metrica["chamadas"]
        )

        maximo = float(
            metrica["maximo"]
        )

        print(
            f"{nome[:42]:42} "
            f"{chamadas:8d} "
            f"{total:7.2f}s "
            f"{maximo:7.2f}s"
        )

    print("=" * 68)
    print(
        "O relatório contém somente nomes de métodos e tempos."
    )
    print(
        "Nenhuma credencial ou dado de notificação é registrado."
    )


def main():
    _instalar_medidores()

    navegador = NavegadorSinan()
    inicio_fluxo: float | None = None

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

        inicio_fluxo = perf_counter()

        print(
            "Abrindo Consulta → "
            "Notificação Individual..."
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

        tempo_total = perf_counter() - inicio_fluxo

        print()
        print("Fluxo concluído com sucesso.")

        _mostrar_resumo(
            tempo_total_fluxo=tempo_total
        )

        input(
            "\nConfira os campos e pressione "
            "Enter para fechar..."
        )

    except KeyboardInterrupt:
        print()
        print("Diagnóstico interrompido pelo usuário.")

    except Exception as erro:
        print()
        print("O fluxo não foi concluído.")
        print(f"Detalhes técnicos: {erro}")

        if inicio_fluxo is not None:
            tempo_total = (
                perf_counter() - inicio_fluxo
            )

            _mostrar_resumo(
                tempo_total_fluxo=tempo_total
            )

        input(
            "\nPressione Enter para fechar "
            "o navegador..."
        )

    finally:
        navegador.fechar()
        print("Navegador fechado.")


if __name__ == "__main__":
    main()