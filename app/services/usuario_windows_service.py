from __future__ import annotations

import ctypes
import getpass
import os
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class IdentidadeWindows:
    """Identidade pública da conta que está executando o ArboHub."""

    nome_exibicao: str
    conta: str


class UsuarioWindowsService:
    """Obtém a identidade da sessão atual diretamente do Windows."""

    FORMATO_NOME_EXIBICAO = 3
    FORMATO_UPN = 8

    def obter_identidade(self) -> IdentidadeWindows:
        usuario = self._obter_usuario_basico()

        nome_exibicao = (
            self._obter_nome_estendido(
                self.FORMATO_NOME_EXIBICAO
            )
            or usuario
            or "Usuário do Windows"
        )

        conta = (
            self._obter_nome_estendido(
                self.FORMATO_UPN
            )
            or self._montar_conta_fallback(usuario)
            or nome_exibicao
        )

        return IdentidadeWindows(
            nome_exibicao=nome_exibicao,
            conta=conta
        )

    @staticmethod
    def _obter_usuario_basico() -> str:
        try:
            usuario = str(
                getpass.getuser()
            ).strip()
        except Exception:
            usuario = ""

        return (
            usuario
            or str(
                os.environ.get(
                    "USERNAME",
                    ""
                )
            ).strip()
        )

    def _obter_nome_estendido(
        self,
        formato: int
    ) -> str | None:
        if sys.platform != "win32":
            return None

        try:
            secur32 = ctypes.WinDLL(
                "secur32",
                use_last_error=True
            )
            obter_nome = secur32.GetUserNameExW
            obter_nome.argtypes = [
                ctypes.c_int,
                ctypes.c_wchar_p,
                ctypes.POINTER(ctypes.c_ulong)
            ]
            obter_nome.restype = ctypes.c_bool

            tamanho = ctypes.c_ulong(0)
            obter_nome(
                formato,
                None,
                ctypes.byref(tamanho)
            )

            if tamanho.value <= 1:
                return None

            buffer = ctypes.create_unicode_buffer(
                tamanho.value
            )
            sucesso = obter_nome(
                formato,
                buffer,
                ctypes.byref(tamanho)
            )

            if not sucesso:
                return None

            valor = buffer.value.strip()
            return valor or None

        except (AttributeError, OSError, ValueError):
            return None

    @staticmethod
    def _montar_conta_fallback(
        usuario: str
    ) -> str:
        if not usuario:
            return ""

        dominio_dns = str(
            os.environ.get(
                "USERDNSDOMAIN",
                ""
            )
        ).strip()

        if dominio_dns:
            return f"{usuario}@{dominio_dns}"

        return usuario
