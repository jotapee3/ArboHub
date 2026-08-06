class Colors:
    """
    Paleta semântica do ArboHub.

    Os componentes continuam usando os mesmos nomes de cor. Apenas a
    paleta ativa muda entre o tema escuro e o claro, preservando a
    identidade visual e evitando cores soltas nas páginas.
    """

    PALETAS = {
        "escuro": {
            # Fundos principais
            "BACKGROUND": "#0D1117",
            "SIDEBAR": "#010409",
            "TITLEBAR": "#010409",

            # Superfícies
            "SURFACE": "#161B22",
            "SURFACE_SECONDARY": "#21262D",
            "SURFACE_HOVER": "#262C36",
            "SURFACE_SELECTED": "#1F2A3A",

            # Bordas
            "BORDER": "#30363D",
            "BORDER_MUTED": "#21262D",

            # Textos
            "TEXT_PRIMARY": "#F0F6FC",
            "TEXT_SECONDARY": "#8B949E",
            "TEXT_MUTED": "#6E7681",
            "TEXT_DISABLED": "#484F58",
            "TEXT_ON_PRIMARY": "#FFFFFF",

            # Cor principal
            "PRIMARY": "#2F81F7",
            "PRIMARY_HOVER": "#388BFD",
            "PRIMARY_PRESSED": "#1F6FEB",

            # Estados
            "SUCCESS": "#3FB950",
            "SUCCESS_HOVER": "#2EA043",
            "WARNING": "#D29922",
            "WARNING_HOVER": "#B7811C",
            "ERROR": "#F85149",
            "ERROR_HOVER": "#DA3633",
            "INFO": "#58A6FF",

            # Botões e controles
            "BUTTON": "#21262D",
            "BUTTON_HOVER": "#30363D",
            "BUTTON_BORDER": "#363B42",
            "CONTROL_KNOB": "#F0F6FC",

            # Campos
            "INPUT": "#0D1117",
            "INPUT_BORDER": "#30363D",
            "INPUT_FOCUS": "#2F81F7",

            # Abas
            "TAB_SELECTED": "#1F6FEB",
            "TAB_SELECTED_HOVER": "#2F81F7",
            "TAB_TEXT": "#F0F6FC",

            # Calendário
            "CALENDAR_EMPTY": "#21262D",
            "CALENDAR_BORDER": "#30363D",
            "CALENDAR_LEVEL_0": "#21262D",
            "CALENDAR_LEVEL_1": "#263A2D",
            "CALENDAR_LEVEL_2": "#2F6F44",
            "CALENDAR_LEVEL_3": "#3FB950",
            "CALENDAR_LEVEL_4": "#56D364",

            # Elementos auxiliares
            "DIVIDER": "#21262D",
            "TRANSPARENT": "transparent"
        },
        "claro": {
            # Fundos principais
            "BACKGROUND": "#F6F8FA",
            "SIDEBAR": "#FFFFFF",
            "TITLEBAR": "#FFFFFF",

            # Superfícies
            "SURFACE": "#FFFFFF",
            "SURFACE_SECONDARY": "#F6F8FA",
            "SURFACE_HOVER": "#EAEEF2",
            "SURFACE_SELECTED": "#DDF4FF",

            # Bordas
            "BORDER": "#D0D7DE",
            "BORDER_MUTED": "#D8DEE4",

            # Textos
            "TEXT_PRIMARY": "#1F2328",
            "TEXT_SECONDARY": "#57606A",
            "TEXT_MUTED": "#6E7781",
            "TEXT_DISABLED": "#8C959F",
            "TEXT_ON_PRIMARY": "#FFFFFF",

            # Cor principal
            "PRIMARY": "#0969DA",
            "PRIMARY_HOVER": "#0860CA",
            "PRIMARY_PRESSED": "#0550AE",

            # Estados
            "SUCCESS": "#1A7F37",
            "SUCCESS_HOVER": "#2DA44E",
            "WARNING": "#9A6700",
            "WARNING_HOVER": "#7D4E00",
            "ERROR": "#CF222E",
            "ERROR_HOVER": "#A40E26",
            "INFO": "#0969DA",

            # Botões e controles
            "BUTTON": "#F6F8FA",
            "BUTTON_HOVER": "#EAEEF2",
            "BUTTON_BORDER": "#D0D7DE",
            "CONTROL_KNOB": "#FFFFFF",

            # Campos
            "INPUT": "#FFFFFF",
            "INPUT_BORDER": "#D0D7DE",
            "INPUT_FOCUS": "#0969DA",

            # Abas
            "TAB_SELECTED": "#DDF4FF",
            "TAB_SELECTED_HOVER": "#B6E3FF",
            "TAB_TEXT": "#0969DA",

            # Calendário
            "CALENDAR_EMPTY": "#EBEDF0",
            "CALENDAR_BORDER": "#D0D7DE",
            "CALENDAR_LEVEL_0": "#EBEDF0",
            "CALENDAR_LEVEL_1": "#9BE9A8",
            "CALENDAR_LEVEL_2": "#40C463",
            "CALENDAR_LEVEL_3": "#30A14E",
            "CALENDAR_LEVEL_4": "#216E39",

            # Elementos auxiliares
            "DIVIDER": "#D8DEE4",
            "TRANSPARENT": "transparent"
        }
    }

    TEMA_ATUAL = "escuro"

    @classmethod
    def aplicar_tema(cls, tema: str) -> str:
        tema_normalizado = str(tema).strip().casefold()

        if tema_normalizado not in cls.PALETAS:
            tema_normalizado = "escuro"

        for nome, valor in cls.PALETAS[tema_normalizado].items():
            setattr(cls, nome, valor)

        cls.TEMA_ATUAL = tema_normalizado
        return tema_normalizado


# Mantém o comportamento histórico caso este módulo seja importado fora
# do fluxo normal de inicialização.
Colors.aplicar_tema("escuro")
