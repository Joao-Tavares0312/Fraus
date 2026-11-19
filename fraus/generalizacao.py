"""Auditoria de conjuntos, sem inferencia nem acesso a pesos serializados.

Indices referem-se a exemplos ACEITOS pelo leitor, nao a linhas do arquivo
bruto (GoEmotions e MultiPICo agregam votos antes de devolver exemplos).
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass

from fraus.corpora import Exemplos
from fraus.divisao import impressao_dos_textos
from fraus.receita_treino import normalizar_texto, preparar_divisao, remover_duplicatas


LADOS = ("treino", "validacao", "teste")


def hash_texto(texto: str) -> str:
    """Identidade normalizada, sem guardar o texto no manifesto privado."""
    return hashlib.sha256(normalizar_texto(texto).encode("utf-8")).hexdigest()


def identidade_grupo(exemplos: Exemplos, indice: int) -> str:
    """Grupo conhecido; sem identificador, a unica identidade e a textual."""
    grupo = exemplos.grupos[indice] if exemplos.grupos is not None else ""
    if isinstance(grupo, str) and grupo.strip():
        return "grupo:" + hashlib.sha256(grupo.strip().encode("utf-8")).hexdigest()
    return "texto:" + hash_texto(exemplos.textos[indice])


def fingerprint_exemplos(exemplos: Exemplos) -> str:
    """SHA-256 canonico de textos, rotulos, grupos efetivos e ordem das classes.

    Insensivel a ordem das linhas e a caixa/espacos/NFC do texto, mas preserva
    multiplicidade. Mudar rotulo, grupo ou semantica de uma classe muda o hash.
    Prefixos distintos impedem confundir identidade textual com um ID real.
    """
    if len(exemplos.textos) != len(exemplos.rotulos) or (
        exemplos.grupos is not None and len(exemplos.grupos) != len(exemplos.textos)
    ):
        raise ValueError("exemplos com tamanhos divergentes")
    registros = sorted(
        [hash_texto(texto), int(rotulo), identidade_grupo(exemplos, i)]
        for i, (texto, rotulo) in enumerate(zip(exemplos.textos, exemplos.rotulos))
    )
    dados = {"versao": 1, "nomes_classes": exemplos.nomes_classes, "registros": registros}
    return hashlib.sha256(json.dumps(
        dados, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


def recortar(exemplos: Exemplos, indices: list[int]) -> Exemplos:
    return Exemplos(
        textos=[exemplos.textos[i] for i in indices],
        rotulos=[exemplos.rotulos[i] for i in indices],
        grupos=None if exemplos.grupos is None else [exemplos.grupos[i] for i in indices],
        nomes_classes=list(exemplos.nomes_classes),
    )


@dataclass(frozen=True)
class IndiceSobreposicao:
    rotulos_por_texto: dict[str, set[int]]
    linhas_por_texto: Counter
    grupos: set[str]


def indexar_sobreposicao(exemplos: Exemplos) -> IndiceSobreposicao:
    """Calcula hashes uma vez para comparar o mesmo conjunto com varios outros."""
    rotulos: dict[str, set[int]] = {}
    linhas: Counter = Counter()
    for texto, rotulo in zip(exemplos.textos, exemplos.rotulos):
        chave = hash_texto(texto)
        rotulos.setdefault(chave, set()).add(int(rotulo))
        linhas[chave] += 1
    grupos = {identidade_grupo(exemplos, i) for i in range(len(exemplos.textos))}
    return IndiceSobreposicao(rotulos, linhas, grupos)


def sobreposicao(esquerda: Exemplos | IndiceSobreposicao,
                 direita: Exemplos | IndiceSobreposicao, *, comparar_rotulos: bool = True,
                 comparar_grupos: bool = True) -> dict:
    """Intersecoes normalizadas; grupos so fazem sentido no mesmo dominio."""
    a = esquerda if isinstance(esquerda, IndiceSobreposicao) else indexar_sobreposicao(esquerda)
    b = direita if isinstance(direita, IndiceSobreposicao) else indexar_sobreposicao(direita)
    comuns = a.rotulos_por_texto.keys() & b.rotulos_por_texto.keys()
    return {
        "textos_normalizados": len(comuns),
        "linhas_esquerda": sum(a.linhas_por_texto[t] for t in comuns),
        "linhas_direita": sum(b.linhas_por_texto[t] for t in comuns),
        "rotulos_comparaveis": comparar_rotulos,
        "textos_com_rotulos_conflitantes": (
            sum(len(a.rotulos_por_texto[t] | b.rotulos_por_texto[t]) > 1 for t in comuns)
            if comparar_rotulos else None
        ),
        "grupos_comparaveis": comparar_grupos,
        "grupos": len(a.grupos & b.grupos) if comparar_grupos else None,
    }


def conferir_holdout(validacao: Exemplos, teste: Exemplos, *, comparar_grupos: bool = True) -> None:
    """Nunca mover exemplos para reparar um holdout contaminado silenciosamente."""
    intersecao = sobreposicao(validacao, teste, comparar_grupos=comparar_grupos)
    if intersecao["textos_normalizados"] or intersecao["grupos"]:
        raise ValueError("colisao entre validacao e teste: novo treino bloqueado")


@dataclass(frozen=True)
class IsolamentoAuxiliar:
    exemplos: Exemplos
    indices: list[int]
    exclusoes: dict[str, int]


def isolar_treino_auxiliar(
    auxiliar: Exemplos, *, treino: Exemplos, validacao: Exemplos, teste: Exemplos,
    comparar_grupos: bool = True,
) -> IsolamentoAuxiliar:
    """Limpa SOMENTE o auxiliar; treino principal e holdouts ficam congelados.

    As quatro entradas devem usar o mesmo alvo e a mesma ordem de classes.
    `comparar_grupos=False` e necessario para dominios diferentes (por exemplo,
    produto B2W versus empresa ConsumerBR), nao para contornar colisao conhecida.
    Conflito textual entre fontes exclui o auxiliar mesmo se estiver no treino
    principal. Identidade de grupo desconhecida se reduz a identidade textual.
    As contagens sao exclusivas, com prioridade conflito > holdout > duplicata.
    """
    if any(ex.nomes_classes != auxiliar.nomes_classes for ex in (treino, validacao, teste)):
        raise ValueError("auxiliar e principal precisam do mesmo contrato de rotulos")
    conferir_holdout(validacao, teste)
    rotulos: dict[str, set[int]] = {}
    for ex in (treino, validacao, teste, auxiliar):
        for texto, rotulo in zip(ex.textos, ex.rotulos):
            rotulos.setdefault(hash_texto(texto), set()).add(int(rotulo))
    textos_holdout = {hash_texto(t) for ex in (validacao, teste) for t in ex.textos}
    textos_treino = {hash_texto(t) for t in treino.textos}
    grupos_holdout = {
        identidade_grupo(ex, i) for ex in (validacao, teste) for i in range(len(ex.textos))
    }
    unicos = remover_duplicatas(auxiliar.textos, auxiliar.rotulos)
    sobreviventes = set(unicos.indices)
    exclusoes = {"conflito_rotulo": 0, "texto_holdout": 0, "grupo_holdout": 0,
                 "duplicata_treino_principal": 0, "duplicata": 0}
    indices = []
    for i, texto in enumerate(auxiliar.textos):
        chave = hash_texto(texto)
        if len(rotulos[chave]) > 1:
            exclusoes["conflito_rotulo"] += 1
        elif chave in textos_holdout:
            exclusoes["texto_holdout"] += 1
        elif comparar_grupos and identidade_grupo(auxiliar, i) in grupos_holdout:
            exclusoes["grupo_holdout"] += 1
        elif chave in textos_treino:
            exclusoes["duplicata_treino_principal"] += 1
        elif i not in sobreviventes:
            exclusoes["duplicata"] += 1
        else:
            indices.append(i)
    return IsolamentoAuxiliar(recortar(auxiliar, indices), indices, exclusoes)


def resumo_conjunto(exemplos: Exemplos) -> dict:
    dedup = remover_duplicatas(exemplos.textos, exemplos.rotulos)
    grupos = Counter(identidade_grupo(exemplos, i) for i in range(len(exemplos.textos)))
    return {
        "aceitos": len(exemplos.textos),
        "apos_deduplicacao": len(dedup.indices),
        "duplicatas_excluidas": dedup.duplicatas,
        "linhas_conflitantes_excluidas": dedup.conflitos,
        "classes": {
            nome: exemplos.rotulos.count(i) for i, nome in enumerate(exemplos.nomes_classes)
        },
        "grupos": {
            "identidades": len(grupos),
            "sem_identificador": sum(g.startswith("texto:") for g in grupos.elements()),
            "distribuicao_tamanho": dict(sorted(Counter(grupos.values()).items())),
        },
        "fingerprint": fingerprint_exemplos(exemplos),
        "impressao_textos": impressao_dos_textos(exemplos.textos),
        "impressao_textos_normalizados": impressao_dos_textos(
            normalizar_texto(t) for t in exemplos.textos
        ),
    }


def dividir_auditavel(exemplos: Exemplos, *, agrupar: bool = True,
                     fracao_val: float = 0.10, fracao_teste: float = 0.15) -> tuple[dict, dict]:
    """Mesma receita, split 42; mapeia cada lado de volta ao indice do leitor.

    A receita remove conflitos antes do split. Grupos ausentes conservam a
    convencao da receita (grupo individual); apos deduplicar, equivale a uma
    identidade textual unica. Nao se reescreve a divisao para embelezar numeros.
    """
    lados = preparar_divisao(exemplos, agrupar=agrupar, fracao_val=fracao_val,
                             fracao_teste=fracao_teste, semente=42)
    indices_unicos = remover_duplicatas(exemplos.textos, exemplos.rotulos).indices
    indice_por_hash = {hash_texto(exemplos.textos[i]): i for i in indices_unicos}
    indices = {
        lado: [indice_por_hash[hash_texto(t)] for t in lados[lado].textos] for lado in LADOS
    }
    conferir_holdout(lados["validacao"], lados["teste"], comparar_grupos=agrupar)
    return lados, indices
