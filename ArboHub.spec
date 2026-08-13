from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files


RAIZ_PROJETO = Path(SPECPATH).resolve()
PASTA_NAVEGADORES = (
    RAIZ_PROJETO
    / ".build-cache"
    / "playwright-browsers"
)

if not PASTA_NAVEGADORES.is_dir():
    raise SystemExit(
        "Chromium de build não encontrado em "
        f"{PASTA_NAVEGADORES}"
    )

dados_playwright, binarios_playwright, ocultos_playwright = (
    collect_all("playwright")
)
dados_customtkinter = collect_data_files("customtkinter")

dados = [
    (
        str(RAIZ_PROJETO / "app" / "gui" / "assets"),
        "app/gui/assets",
    ),
    (
        str(RAIZ_PROJETO / "assets" / "sistemas"),
        "assets/sistemas",
    ),
    (
        str(PASTA_NAVEGADORES),
        "ms-playwright",
    ),
    *dados_playwright,
    *dados_customtkinter,
]


a = Analysis(
    [str(RAIZ_PROJETO / "main.py")],
    pathex=[str(RAIZ_PROJETO)],
    binaries=binarios_playwright,
    datas=dados,
    hiddenimports=ocultos_playwright,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["watchfiles"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ArboHub",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(
        RAIZ_PROJETO
        / "app"
        / "gui"
        / "assets"
        / "arbohub.ico"
    ),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ArboHub",
)
