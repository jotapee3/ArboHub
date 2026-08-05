from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from dataclasses import dataclass


@dataclass(frozen=True, slots=True, repr=False)
class CredencialSinan:
    """
    Credencial recuperada apenas durante o uso.

    O ``repr`` é desativado para evitar que a senha apareça por
    acidente em mensagens de diagnóstico ou no console.
    """

    usuario: str
    senha: str


class CredenciaisService:
    """
    Armazena a credencial do SINAN no Gerenciador de Credenciais
    do Windows.

    A senha não é escrita no JSON de configurações, no banco SQLite,
    em arquivos do projeto ou em logs. O registro fica associado à
    conta do Windows que executou o ArboHub.
    """

    ALVO = "ArboHub/SINAN"
    COMENTARIO = "Credencial do SINAN usada pelo ArboHub"

    CRED_TYPE_GENERIC = 1
    CRED_PERSIST_LOCAL_MACHINE = 2
    ERROR_NOT_FOUND = 1168
    TAMANHO_MAXIMO_BLOB = 5 * 512

    class _CREDENTIALW(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            (
                "CredentialBlob",
                ctypes.POINTER(ctypes.c_ubyte)
            ),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", wintypes.LPVOID),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR)
        ]

    def __init__(self):
        self._advapi32 = None

    def disponivel(self) -> bool:
        return sys.platform == "win32"

    def salvar(
        self,
        usuario: str,
        senha: str
    ) -> None:
        usuario_limpo = str(usuario).strip()
        senha_texto = str(senha)

        if not usuario_limpo:
            raise ValueError(
                "Informe o usuário do SINAN."
            )

        if not senha_texto:
            raise ValueError(
                "Informe a senha do SINAN."
            )

        senha_bytes = senha_texto.encode(
            "utf-16-le"
        )

        if len(senha_bytes) > self.TAMANHO_MAXIMO_BLOB:
            raise ValueError(
                "A senha excede o limite aceito pelo "
                "Gerenciador de Credenciais do Windows."
            )

        api = self._obter_api()
        buffer_senha = ctypes.create_string_buffer(
            senha_bytes,
            len(senha_bytes)
        )

        credencial = self._CREDENTIALW()
        credencial.Flags = 0
        credencial.Type = self.CRED_TYPE_GENERIC
        credencial.TargetName = self.ALVO
        credencial.Comment = self.COMENTARIO
        credencial.CredentialBlobSize = len(
            senha_bytes
        )
        credencial.CredentialBlob = ctypes.cast(
            buffer_senha,
            ctypes.POINTER(ctypes.c_ubyte)
        )
        credencial.Persist = (
            self.CRED_PERSIST_LOCAL_MACHINE
        )
        credencial.AttributeCount = 0
        credencial.Attributes = None
        credencial.TargetAlias = None
        credencial.UserName = usuario_limpo

        try:
            sucesso = api.CredWriteW(
                ctypes.byref(credencial),
                0
            )

            if not sucesso:
                self._levantar_erro_windows(
                    "Não foi possível salvar a credencial do SINAN"
                )
        finally:
            ctypes.memset(
                ctypes.addressof(buffer_senha),
                0,
                len(buffer_senha)
            )

    def obter(self) -> CredencialSinan | None:
        api = self._obter_api()
        ponteiro = ctypes.POINTER(
            self._CREDENTIALW
        )()

        sucesso = api.CredReadW(
            self.ALVO,
            self.CRED_TYPE_GENERIC,
            0,
            ctypes.byref(ponteiro)
        )

        if not sucesso:
            codigo = ctypes.get_last_error()

            if codigo == self.ERROR_NOT_FOUND:
                return None

            self._levantar_erro_windows(
                "Não foi possível ler a credencial do SINAN",
                codigo
            )

        try:
            credencial = ponteiro.contents
            usuario = str(
                credencial.UserName or ""
            ).strip()

            if credencial.CredentialBlobSize:
                senha_bytes = ctypes.string_at(
                    credencial.CredentialBlob,
                    credencial.CredentialBlobSize
                )
                senha = senha_bytes.decode(
                    "utf-16-le"
                )
            else:
                senha = ""

            if not usuario or not senha:
                return None

            return CredencialSinan(
                usuario=usuario,
                senha=senha
            )
        finally:
            api.CredFree(ponteiro)

    def obter_usuario(self) -> str | None:
        """
        Recupera somente o nome de usuário para exibição na interface.

        O blob da senha não é convertido em texto por este método.
        """

        api = self._obter_api()
        ponteiro = ctypes.POINTER(
            self._CREDENTIALW
        )()

        sucesso = api.CredReadW(
            self.ALVO,
            self.CRED_TYPE_GENERIC,
            0,
            ctypes.byref(ponteiro)
        )

        if not sucesso:
            codigo = ctypes.get_last_error()

            if codigo == self.ERROR_NOT_FOUND:
                return None

            self._levantar_erro_windows(
                "Não foi possível consultar a credencial do SINAN",
                codigo
            )

        try:
            usuario = str(
                ponteiro.contents.UserName or ""
            ).strip()
            return usuario or None
        finally:
            api.CredFree(ponteiro)

    def existe(self) -> bool:
        return self.obter_usuario() is not None

    def remover(self) -> bool:
        api = self._obter_api()

        sucesso = api.CredDeleteW(
            self.ALVO,
            self.CRED_TYPE_GENERIC,
            0
        )

        if sucesso:
            return True

        codigo = ctypes.get_last_error()

        if codigo == self.ERROR_NOT_FOUND:
            return False

        self._levantar_erro_windows(
            "Não foi possível remover a credencial do SINAN",
            codigo
        )
        return False

    def _obter_api(self):
        if not self.disponivel():
            raise RuntimeError(
                "O armazenamento seguro de credenciais está "
                "disponível apenas no Windows."
            )

        if self._advapi32 is not None:
            return self._advapi32

        api = ctypes.WinDLL(
            "Advapi32.dll",
            use_last_error=True
        )

        api.CredWriteW.argtypes = [
            ctypes.POINTER(self._CREDENTIALW),
            wintypes.DWORD
        ]
        api.CredWriteW.restype = wintypes.BOOL

        api.CredReadW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(
                ctypes.POINTER(self._CREDENTIALW)
            )
        ]
        api.CredReadW.restype = wintypes.BOOL

        api.CredDeleteW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD
        ]
        api.CredDeleteW.restype = wintypes.BOOL

        api.CredFree.argtypes = [
            wintypes.LPVOID
        ]
        api.CredFree.restype = None

        self._advapi32 = api
        return api

    def _levantar_erro_windows(
        self,
        mensagem: str,
        codigo: int | None = None
    ) -> None:
        if codigo is None:
            codigo = ctypes.get_last_error()

        detalhe = ctypes.FormatError(
            codigo
        ).strip()

        raise OSError(
            codigo,
            f"{mensagem}. {detalhe}"
        )
