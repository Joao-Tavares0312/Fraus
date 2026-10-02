"""Visao de banco limitada aos canais permitidos, em toda leitura da API."""
import hashlib
from fastapi import HTTPException


class BancoComEscopo:
    def __init__(self, banco, canais):
        self._banco = banco
        self._canais = frozenset(canais)

    def __getattr__(self, nome):
        return getattr(self._banco, nome)

    def todas(self):
        return [(c, s) for c, s in self._banco.todas() if c.canal in self._canais]

    def buscar(self, identificador):
        achado = self._banco.buscar(identificador)
        return achado if achado and achado[0].canal in self._canais else None

    def listar(self):
        return [l for l in self._banco.listar() if l["canal"] in self._canais]

    def listar_com_conversa(self, de=None, ate=None, limite=None, deslocamento=0):
        linhas = [l for l in self._banco.listar_com_conversa(de, ate) if l[1].canal in self._canais]
        return linhas[deslocamento:deslocamento + limite] if limite is not None else linhas[deslocamento:]

    def regua_da_conversa(self, identificador):
        return self._banco.regua_da_conversa(identificador) if self.buscar(identificador) else None

    def listar_fontes(self):
        return [f for f in self._banco.listar_fontes() if f["canal"] in self._canais]

    def listar_importacoes(self):
        # Um lote global pode conter canais fora do escopo. Nao o expoe.
        return []

    def assinatura_conversas(self):
        registros = self.todas()
        digest = hashlib.sha256("".join(c.model_dump_json() + str(s) for c, s in registros).encode()).hexdigest()
        return len(registros), digest

    def contar_defasadas(self, regua_vigente=None):
        # A regra e a do Banco, restrita aos canais -- nunca uma copia dela.
        return self._banco.contar_defasadas(regua_vigente, canais=self._canais)

    def salvar_lote(self, registros, lexico_versao, regua):
        if any(c.canal not in self._canais for c, _, _ in registros):
            raise HTTPException(403, "o lote inclui um canal fora do seu escopo")
        return self._banco.salvar_lote(registros, lexico_versao, regua)
