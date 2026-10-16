"""Inventario estatico e local: nunca executa modelos, pickle ou configuracoes.

A arvore local, um ZIP fornecido e um bundle publicado sao evidencias distintas.
Cabecalhos e fontes tem limites de leitura; os pesos so passam pelo SHA-256.
"""
from __future__ import annotations

import ast
from collections import defaultdict
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import time
import sys
import tomllib
import zipfile

from scripts.gerenciar_artefatos import sha256
from .comum import RAIZ, parser_base, preparar_workspace, resultado, salvar_resultado

DIRETORIOS_MODELOS = ("modelos", "modelos-onnx")
DIRETORIOS_CODIGO = ("fraus", "api", "scripts")
CONFIGURACOES = ("pyproject.toml", "uv.lock", "requirements.txt", "vercel.json", "Dockerfile")
LIMITE_CABECALHO = 8 * 1024 * 1024
LIMITE_TEXTO = 4 * 1024 * 1024
LIMITE_MEMBROS_ZIP = 100_000
DEPENDENCIAS = ("torch", "transformers", "tokenizers", "onnx", "onnxruntime", "safetensors", "laya", "scikit-learn", "joblib", "numpy", "fastapi", "uvicorn", "psycopg", "psycopg-pool", "pydantic")
NOME = re.compile(r"[A-Za-z0-9_.+/-]{1,512}\Z")
VARIAVEL = re.compile(r"[A-Z][A-Z0-9_]{0,127}\Z")
DEPENDENCIA = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9_.-]*)(?:\[([A-Za-z0-9_,.-]+)\])?\s*((?:(?:===|==|!=|~=|>=|<=|>|<)\s*[A-Za-z0-9.*+!-]+\s*,?\s*)*)")


def _nome(valor: object) -> str:
    return valor if isinstance(valor, str) and NOME.fullmatch(valor) else "[nome_omitido]"


def _nao_verificado(motivo: str) -> dict:
    return {"status": "nao_verificado", "motivo": motivo}


def _sem_symlink(caminho: Path) -> bool:
    return not any(parte.is_symlink() for parte in (caminho, *caminho.parents))


def _texto(caminho: Path) -> str:
    if caminho.stat().st_size > LIMITE_TEXTO:
        raise ValueError("limite_de_texto")
    with caminho.open("rb") as arquivo:
        conteudo = arquivo.read(LIMITE_TEXTO + 1)
    if len(conteudo) > LIMITE_TEXTO:
        raise ValueError("limite_de_texto")
    return conteudo.decode("utf-8")


def _percorrer(raiz: Path, relativa: str, recusas: list[dict]):
    """Nao entra em symlinks, nem em arquivos especiais, nem fora da raiz."""
    pasta = raiz / relativa
    if not pasta.exists() and not pasta.is_symlink():
        return
    if not _sem_symlink(pasta):
        recusas.append({"caminho": relativa, "motivo": "symlink_recusado"})
        return
    if not pasta.is_dir():
        recusas.append({"caminho": relativa, "motivo": "diretorio_esperado"})
        return
    pendentes = [pasta]
    while pendentes:
        atual = pendentes.pop()
        try:
            with os.scandir(atual) as entradas:
                itens = sorted(entradas, key=lambda item: item.name)
            for item in itens:
                caminho = Path(item.path)
                relativo = caminho.relative_to(raiz).as_posix()
                if item.name.startswith("."):
                    recusas.append({"caminho": _nome(relativo), "motivo": "arquivo_ou_diretorio_oculto_ignorado"})
                elif item.is_symlink():
                    recusas.append({"caminho": _nome(relativo), "motivo": "symlink_recusado"})
                elif item.is_dir(follow_symlinks=False):
                    pendentes.append(caminho)
                elif item.is_file(follow_symlinks=False):
                    yield caminho
                else:
                    recusas.append({"caminho": _nome(relativo), "motivo": "arquivo_especial_recusado"})
        except OSError:
            recusas.append({"caminho": _nome(atual.relative_to(raiz).as_posix()), "motivo": "leitura_indisponivel"})


def inspecionar_safetensors(caminho: Path) -> dict:
    """Le apenas o comprimento e JSON limitado; nao importa torch/safetensors."""
    try:
        tamanho = caminho.stat().st_size
        with caminho.open("rb") as arquivo:
            prefixo = arquivo.read(8)
            if len(prefixo) != 8:
                return _nao_verificado("cabecalho_incompleto")
            comprimento = struct.unpack("<Q", prefixo)[0]
            if comprimento < 2 or comprimento > LIMITE_CABECALHO or comprimento > tamanho - 8:
                return _nao_verificado("cabecalho_fora_do_limite")
            dados = json.loads(arquivo.read(comprimento), parse_constant=_recusar_constante)
        if not isinstance(dados, dict):
            return _nao_verificado("cabecalho_invalido")
        tensores = []
        intervalos = []
        for nome, tensor in sorted(dados.items()):
            if nome == "__metadata__":
                continue
            if not isinstance(tensor, dict):
                return _nao_verificado("tensor_invalido")
            forma, offsets, dtype = tensor.get("shape"), tensor.get("data_offsets"), tensor.get("dtype")
            if not isinstance(forma, list) or len(forma) > 64 or not all(type(n) is int and n >= 0 for n in forma):
                return _nao_verificado("dimensoes_invalidas")
            if not isinstance(offsets, list) or len(offsets) != 2 or not all(type(n) is int for n in offsets) or not 0 <= offsets[0] <= offsets[1] <= tamanho - 8 - comprimento:
                return _nao_verificado("offsets_invalidos")
            if dtype not in {"BOOL", "U8", "I8", "I16", "U16", "F16", "BF16", "I32", "U32", "F32", "F64", "I64", "U64", "F8_E4M3", "F8_E5M2", "F8_E8M0"}:
                return _nao_verificado("dtype_desconhecido")
            intervalos.append(offsets)
            tensores.append({"nome": _nome(nome), "dtype": dtype, "dimensoes": forma, "offsets": offsets})
        intervalos.sort()
        if any(a[1] > b[0] for a, b in zip(intervalos, intervalos[1:])):
            return _nao_verificado("offsets_sobrepostos")
        return {"status": "medido", "cabecalho_bytes": comprimento, "tensores": tensores, "metadados_livres": "omitidos", "validacao_numerica": None, "motivo": "somente_cabecalho_sem_carregar_tensores"}
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
        return _nao_verificado("cabecalho_ilegivel")


def _recusar_constante(_: str):
    raise ValueError("constante_json_nao_finita")


def _forma_onnx(valor) -> dict:
    tensor = valor.type.tensor_type
    dimensoes = []
    for dimensao in tensor.shape.dim:
        if dimensao.HasField("dim_value"):
            dimensoes.append(dimensao.dim_value)
        elif dimensao.HasField("dim_param"):
            dimensoes.append(_nome(dimensao.dim_param))
        else:
            dimensoes.append(None)
    return {"nome": _nome(valor.name), "tipo_elemento": tensor.elem_type, "dimensoes": dimensoes}


def _tensores_onnx(grafo):
    yield from grafo.initializer
    for esparso in getattr(grafo, "sparse_initializer", []):
        yield esparso.values
        yield esparso.indices
    for no in grafo.node:
        for atributo in no.attribute:
            if atributo.HasField("t"):
                yield atributo.t
            yield from atributo.tensors
            if atributo.HasField("g"):
                yield from _tensores_onnx(atributo.g)
            for filho in atributo.graphs:
                yield from _tensores_onnx(filho)


def inspecionar_onnx(caminho: Path, habilitado: bool) -> dict:
    if not habilitado:
        return _nao_verificado("inspecao_onnx_nao_solicitada")
    try:
        import onnx
    except ImportError:
        return _nao_verificado("dependencia_onnx_ausente")
    try:
        modelo = onnx.load(str(caminho), load_external_data=False)
        externos = []
        for tensor in _tensores_onnx(modelo.graph):
            campos = {e.key: e.value for e in tensor.external_data}
            if not campos:
                continue
            local = campos.get("location", "")
            partes = PurePosixPath(local)
            seguro = bool(local) and not partes.is_absolute() and ".." not in partes.parts and "\\" not in local and ":" not in local
            entrada = {"tensor": _nome(tensor.name), "location": _nome(local) if seguro else None, "caminho_seguro": seguro, "carregado": False}
            for chave in ("offset", "length"):
                valor = campos.get(chave)
                entrada[chave] = int(valor) if valor and valor.isdecimal() and len(valor) <= 20 else None
            externos.append(entrada)
        return {"status": "medido", "ir_version": modelo.ir_version, "opsets": [{"dominio": _nome(op.domain) if op.domain else "", "versao": op.version} for op in modelo.opset_import], "entradas": [_forma_onnx(v) for v in modelo.graph.input], "saidas": [_forma_onnx(v) for v in modelo.graph.output], "external_data": externos, "sessao_criada": False, "compatibilidade_runtime": None, "motivo": "estrutura_sem_sessao_ou_carregamento_externo"}
    except Exception:
        return _nao_verificado("inspecao_onnx_falhou")


def _papel(relativo: str, categoria: str) -> dict:
    if "bertimbau-ironia" in relativo:
        return {"inferencia": "perfil_bertimbau", "transitorio": "perfil_laya_pela_fabrica_atual", "validacao": "obrigatorio_no_bundle_onnx", "nao_usado": "vetor_do_fusor", "fonte": "fraus/api/main.py:299-325; scripts/preparar_modelos_vercel.py:66-102", "estado_producao": None}
    if "laya-ironia" in relativo:
        return {"inferencia": "somente_perfil_laya_onnx", "transitorio": False, "validacao": "condicional_ao_perfil", "nao_usado": "vetor_do_fusor", "estado_producao": None}
    if "multitarefa" in relativo:
        return {"inferencia": "somente_perfil_onnx_multitarefa", "estado_producao": None}
    if categoria in {"modelo", "tokenizador", "fusor"}:
        return {"inferencia": "condicional_ao_backend_e_caminho", "estado_producao": None}
    return {"inferencia": "nao_determinado_por_extensao", "estado_producao": None}


def _categoria(caminho: Path) -> str:
    nome = caminho.name.lower()
    if nome == "fusor.joblib":
        return "fusor"
    if nome.startswith(("tokenizer", "vocab", "merges", "special_tokens", "added_tokens", "sentencepiece")) or nome.endswith(".model"):
        return "tokenizador"
    if caminho.suffix.lower() in {".onnx", ".data", ".safetensors", ".bin", ".pt", ".pth", ".joblib"}:
        return "modelo"
    return "metadados" if caminho.suffix.lower() in {".json", ".txt", ".yaml", ".yml"} else "outros"


def _metadados_json(caminho: Path) -> dict:
    try:
        dados = json.loads(_texto(caminho), parse_constant=_recusar_constante)
        if not isinstance(dados, dict):
            return _nao_verificado("json_nao_e_objeto")
        seguros = {}
        for chave in ("vocab_size", "hidden_size", "num_hidden_layers", "num_attention_heads", "max_position_embeddings", "model_max_length", "num_labels", "max_length", "pad_token_id", "bos_token_id", "eos_token_id"):
            if type(dados.get(chave)) is int:
                seguros[chave] = dados[chave]
        for chave in ("model_type", "torch_dtype", "tokenizer_class", "transformers_version"):
            if chave in dados:
                seguros[chave] = _nome(dados[chave])
        return {"status": "medido", "campos_permitidos": seguros, "demais_valores": "omitidos"}
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
        return _nao_verificado("metadados_ilegíveis_ou_acima_do_limite")


def _arquivo_modelo(raiz: Path, caminho: Path, inspecionar: bool) -> dict:
    relativo = caminho.relative_to(raiz).as_posix()
    categoria = _categoria(caminho)
    item = {"caminho": _nome(relativo), "bytes": caminho.stat().st_size, "sha256": sha256(caminho), "categoria": categoria, "formato_declarado": caminho.suffix.lower().lstrip("."), "formato_observado": None, "uso": _papel(relativo, categoria)}
    if caminho.suffix == ".safetensors":
        item["inspecao"] = inspecionar_safetensors(caminho)
        if item["inspecao"]["status"] == "medido":
            item["formato_observado"] = "safetensors_cabecalho"
    elif caminho.suffix == ".onnx":
        item["inspecao"] = inspecionar_onnx(caminho, inspecionar)
        if item["inspecao"]["status"] == "medido":
            item["formato_observado"] = "onnx_protobuf"
    elif caminho.suffix == ".json":
        item["inspecao"] = _metadados_json(caminho)
        if item["inspecao"]["status"] == "medido":
            item["formato_observado"] = "json"
    elif caminho.suffix == ".joblib":
        item["inspecao"] = {**_nao_verificado("desserializacao_proibida_sem_procedencia_confiavel"), "_sklearn_version": None, "classes": None, "n_features": None}
    else:
        with caminho.open("rb") as arquivo:
            prefixo = arquivo.read(8)
        item["formato_observado"] = "zip_container_nao_desserializado" if prefixo.startswith(b"PK\x03\x04") else None
        item["inspecao"] = _nao_verificado("somente_bytes_e_hash_sem_inferir_formato_pela_extensao")
    item["motivo_formato_observado"] = None if item["formato_observado"] else "formato_nao_validado_sem_carregar_peso"
    return item


def _requisito(valor: object) -> dict | None:
    if not isinstance(valor, str):
        return None
    correspondencia = DEPENDENCIA.match(valor)
    if not correspondencia:
        return None
    nome, extras, versao = correspondencia.groups()
    return {"nome": nome.lower().replace("_", "-"), "extras": extras.split(",") if extras else [], "restricao": versao.strip() or None, "origem": "omitida" if "@" in valor or "://" in valor else "indice_nao_consultado"}


def _configuracao(caminho: Path, relativa: str) -> dict:
    item = {"caminho": relativa, "bytes": caminho.stat().st_size, "sha256": sha256(caminho), "status": "medido"}
    try:
        texto = _texto(caminho)
        if relativa == "pyproject.toml":
            dados = tomllib.loads(texto)
            projeto = dados.get("project", {})
            item["dados"] = {"nome": _nome(projeto.get("name")), "versao": _nome(projeto.get("version")), "dependencias": [r for valor in projeto.get("dependencies", []) if (r := _requisito(valor))], "extras": {_nome(grupo): [r for valor in valores if (r := _requisito(valor))] for grupo, valores in projeto.get("optional-dependencies", {}).items() if isinstance(valores, list)}}
        elif relativa == "uv.lock":
            dados = tomllib.loads(texto)
            item["dados"] = {"versao_lock": dados.get("version") if type(dados.get("version")) is int else None, "pacotes": [{"nome": _nome(p.get("name")), "versao": _nome(p.get("version"))} for p in dados.get("package", []) if isinstance(p, dict)]}
        elif relativa == "vercel.json":
            dados = json.loads(texto, parse_constant=_recusar_constante)
            funcoes = []
            for nome, funcao in dados.get("functions", {}).items():
                seguros = {"caminho": _nome(nome)}
                for chave in ("maxDuration", "memory"):
                    seguros[chave] = funcao[chave] if type(funcao.get(chave)) is int else None
                seguros["includeFiles_todos"] = funcao.get("includeFiles") == "**"
                funcoes.append(seguros)
            item["dados"] = {"funcoes": funcoes, "instalacao_declarada": isinstance(dados.get("installCommand"), str), "build_declarado": isinstance(dados.get("buildCommand"), str), "regiao_efetiva": None, "motivo_regiao_efetiva": "configuracao_local_nao_prova_deploy", "variaveis_declaradas": sorted(k for k in dados.get("env", {}) if VARIAVEL.fullmatch(k))}
        elif relativa == "requirements.txt":
            requisitos = []
            for linha in texto.splitlines():
                linha = linha.strip()
                if linha.startswith(".[") and re.fullmatch(r"\.\[[A-Za-z0-9_,.-]+\]", linha):
                    requisitos.append({"projeto_local_extras": linha[2:-1].split(",")})
                elif linha and not linha.startswith(("#", "-")) and (requisito := _requisito(linha)):
                    requisitos.append(requisito)
            item["dados"] = {"requisitos": requisitos}
        else:
            # Docker/YAML nao sao executados nem copiados: so estrutura e nomes.
            item["dados"] = {"linhas": len(texto.splitlines()), "variaveis_referidas": sorted(set(re.findall(r"\b(?:FRAUS|HF_HUB|TRANSFORMERS)_[A-Z0-9_]+\b", texto))), "conteudo_livre": "omitido", "executado": False}
    except (OSError, ValueError, TypeError, AttributeError, UnicodeError, RecursionError):
        item.update(_nao_verificado("configuracao_ilegivel_ou_formato_invalido"))
        item["dados"] = None
    return item


def _dependencias(nomes: set[str]) -> list[dict]:
    encontrados = []
    for nome in sorted(nomes):
        item = {"nome": nome, "versao": None, "bytes_instalados": None, "motivo": None, "bundle_publicado": None}
        try:
            distribuicao = importlib.metadata.distribution(nome)
            item["versao"] = _nome(distribuicao.version)
            arquivos = distribuicao.files
            if arquivos is None:
                item["motivo"] = "manifesto_de_arquivos_ausente"
            else:
                base = Path(distribuicao.locate_file("")).absolute()
                total = 0
                omitidos = 0
                vistos = set()
                for arquivo in arquivos:
                    relativo = Path(str(arquivo))
                    if relativo.is_absolute() or ".." in relativo.parts:
                        omitidos += 1
                        continue
                    caminho = base / relativo
                    if caminho in vistos:
                        continue
                    vistos.add(caminho)
                    if not _sem_symlink(caminho):
                        omitidos += 1
                        continue
                    try:
                        estado = caminho.stat()
                        if stat.S_ISREG(estado.st_mode):
                            total += estado.st_size
                        else:
                            omitidos += 1
                    except OSError:
                        omitidos += 1
                item["bytes_instalados"] = total if vistos else None
                item["arquivos_omitidos"] = omitidos
                item["motivo"] = "soma_logica_do_manifesto_local_nao_e_bundle; arquivos_omitidos_explicitos" if omitidos else "soma_logica_do_manifesto_local_nao_e_bundle"
        except importlib.metadata.PackageNotFoundError:
            item["motivo"] = "pacote_nao_instalado"
        except (OSError, ValueError, TypeError):
            item["motivo"] = "metadados_do_pacote_indisponiveis"
        encontrados.append(item)
    return encontrados


def _pacote(caminho: Path | None) -> dict:
    if caminho is None:
        return {"bytes": None, "sha256": None, "membros": None, "bytes_descompactados": None, "motivo": "pacote_nao_fornecido"}
    if not _sem_symlink(caminho) or not caminho.is_file():
        return {"bytes": None, "sha256": None, "membros": None, "bytes_descompactados": None, "motivo": "pacote_ausente_ou_symlink_recusado"}
    item = {"bytes": caminho.stat().st_size, "sha256": sha256(caminho), "extraido": False, "identidade_publicada": None, "motivo": "zip_local_nao_prova_bundle_publicado"}
    try:
        with zipfile.ZipFile(caminho) as arquivo:
            membros = arquivo.infolist()
            if len(membros) > LIMITE_MEMBROS_ZIP:
                raise ValueError("limite_membros_zip")
            linhas = []
            for membro in membros:
                partes = PurePosixPath(membro.filename)
                seguro = not partes.is_absolute() and ".." not in partes.parts and "\\" not in membro.filename and ":" not in membro.filename and not stat.S_ISLNK(membro.external_attr >> 16)
                linhas.append({"nome": _nome(membro.filename), "bytes": membro.file_size, "bytes_comprimidos": membro.compress_size, "caminho_seguro": seguro, "criptografado": bool(membro.flag_bits & 1)})
            item.update({"membros": linhas, "bytes_descompactados": sum(m.file_size for m in membros), "bytes_comprimidos_membros": sum(m.compress_size for m in membros)})
    except (OSError, ValueError, zipfile.BadZipFile, NotImplementedError):
        item.update({"membros": None, "bytes_descompactados": None, "motivo": "zip_invalido_ou_acima_do_limite"})
    return item


def _fontes(raiz: Path, recusas: list[dict]) -> tuple[list[dict], set[str]]:
    fontes = []
    variaveis = set()
    for diretorio in DIRETORIOS_CODIGO:
        for caminho in _percorrer(raiz, diretorio, recusas):
            if caminho.suffix != ".py":
                continue
            relativo = caminho.relative_to(raiz).as_posix()
            fontes.append({"caminho": _nome(relativo), "bytes": caminho.stat().st_size})
            try:
                arvore = ast.parse(_texto(caminho))
                for no in ast.walk(arvore):
                    if isinstance(no, ast.Call):
                        funcao = no.func
                        acesso = isinstance(funcao, ast.Attribute) and ((funcao.attr == "getenv" and isinstance(funcao.value, ast.Name) and funcao.value.id == "os") or (funcao.attr == "get" and isinstance(funcao.value, ast.Attribute) and isinstance(funcao.value.value, ast.Name) and funcao.value.value.id == "os" and funcao.value.attr == "environ"))
                        if acesso and no.args and isinstance(no.args[0], ast.Constant) and isinstance(no.args[0].value, str) and VARIAVEL.fullmatch(no.args[0].value):
                            variaveis.add(no.args[0].value)
                    if isinstance(no, ast.Subscript) and isinstance(no.value, ast.Attribute) and isinstance(no.value.value, ast.Name) and no.value.value.id == "os" and no.value.attr == "environ" and isinstance(no.slice, ast.Constant) and isinstance(no.slice.value, str) and VARIAVEL.fullmatch(no.slice.value):
                        variaveis.add(no.slice.value)
                    # artefato("FRAUS_...", default) declara um nome sem ler ambiente.
                    if isinstance(no, ast.Constant) and isinstance(no.value, str) and no.value.startswith("FRAUS_") and VARIAVEL.fullmatch(no.value):
                        variaveis.add(no.value)
            except (OSError, ValueError, SyntaxError, UnicodeError, RecursionError):
                recusas.append({"caminho": _nome(relativo), "motivo": "fonte_nao_analisada"})
    return fontes, variaveis


def coletar(raiz: Path, *, inspecionar_onnx: bool = False, pacote: Path | None = None) -> dict:
    recusas = []
    arquivos = []
    diretorios = []
    for relativo in DIRETORIOS_MODELOS:
        pasta = raiz / relativo
        estado = "recusado" if not _sem_symlink(pasta) else "presente" if pasta.is_dir() else "ausente"
        diretorios.append({"caminho": relativo, "status": estado, "motivo": "symlink_recusado" if estado == "recusado" else "diretorio_ausente" if estado == "ausente" else None})
        for caminho in _percorrer(raiz, relativo, recusas):
            try:
                arquivos.append(_arquivo_modelo(raiz, caminho, inspecionar_onnx))
            except (OSError, ValueError):
                recusas.append({"caminho": _nome(caminho.relative_to(raiz).as_posix()), "motivo": "artefato_nao_lido"})
    arquivos.sort(key=lambda a: a["caminho"])
    configuracoes = []
    caminhos = [raiz / c for c in CONFIGURACOES]
    caminhos.extend(c for c in _percorrer(raiz, ".github/workflows", recusas) if c.suffix in {".yml", ".yaml"})
    for caminho in caminhos:
        relativo = caminho.relative_to(raiz).as_posix()
        if not _sem_symlink(caminho):
            recusas.append({"caminho": _nome(relativo), "motivo": "symlink_recusado"})
        elif caminho.is_file():
            configuracoes.append(_configuracao(caminho, relativo))
        else:
            configuracoes.append({"caminho": relativo, "status": "nao_verificado", "motivo": "configuracao_ausente", "dados": None})
    fontes, variaveis = _fontes(raiz, recusas)
    nomes = set(DEPENDENCIAS)
    for configuracao in configuracoes:
        dados = configuracao.get("dados") or {}
        variaveis.update(dados.get("variaveis_referidas", []))
        variaveis.update(dados.get("variaveis_declaradas", []))
        for requisito in dados.get("dependencias", []) + dados.get("requisitos", []):
            if "nome" in requisito:
                nomes.add(requisito["nome"])
        for requisitos in dados.get("extras", {}).values():
            nomes.update(r["nome"] for r in requisitos)
    dependencias = _dependencias(nomes)
    hashes = defaultdict(list)
    categorias = defaultdict(int)
    for arquivo in arquivos:
        hashes[arquivo["sha256"]].append(arquivo["caminho"])
        categorias[arquivo["categoria"]] += arquivo["bytes"]
    total = sum(a["bytes"] for a in arquivos) if arquivos else None
    return {"arquivos": arquivos, "diretorios": diretorios, "recusas": recusas, "configuracoes": configuracoes, "dependencias": dependencias, "variaveis_ambiente": sorted(variaveis), "valores_ambiente_lidos": False, "duplicatas": [{"sha256": hash_, "caminhos": caminhos} for hash_, caminhos in sorted(hashes.items()) if len(caminhos) > 1], "bytes": {"modelos": total, "motivo_modelos": "nenhum_artefato_local_observado" if total is None else "soma_logica_dos_arquivos_locais_observados; nao_e_bundle", "por_categoria": dict(sorted(categorias.items())), "codigo_python": sum(f["bytes"] for f in fontes) if fontes else None, "motivo_codigo": "fontes_python_nos_diretorios_declarados; nao_e_bundle", "dependencias_instaladas": sum(d["bytes_instalados"] for d in dependencias if d["bytes_instalados"] is not None) if any(d["bytes_instalados"] is not None for d in dependencias) else None, "motivo_dependencias": "soma_logica_manifesta_local; nao_e_bundle_nem_total_transitivo"}, "pacote": _pacote(pacote), "bundle_publicado": {"bytes": None, "composicao": None, "motivo": "nenhum_bundle_publicado_fornecido; historico_nao_e_medicao_atual"}, "producao": {"regiao": None, "memoria": None, "build": None, "validade_par": None, "rotacao_par": None, "motivo": "somente_local_sem_sonda_ou_credencial"}, "limites": ["hash_atual_nao_prova_procedencia", "arquivo_mutado_concorrentemente_nao_e_snapshot_atomico", "symlinks_estaticos_recusados_sem_garantia_contra_troca_concorrente", "zip_apenas_diretorio_central_sem_extracao_ou_validacao_crc", "onnx_estrutura_nao_prova_compatibilidade_ou_integridade_numerica", "dependencias_instaladas_nao_representam_bundle_vercel", "configuracao_local_nao_prova_estado_publicado"]}


def main(argv: list[str] | None = None) -> int:
    parser = parser_base("Inventario estatico de motores e configuracoes locais")
    parser.add_argument("--raiz", type=Path, default=RAIZ)
    parser.add_argument("--inspecionar-onnx", action="store_true")
    parser.add_argument("--pacote", type=Path)
    args = parser.parse_args(argv)
    workspace = None
    try:
        raiz = args.raiz.absolute()
        if not _sem_symlink(raiz) or not raiz.is_dir():
            print("inventario: raiz_ausente_ou_symlink_recusado")
            return 2
        raiz = raiz.resolve()
        destino = Path(args.workspace).expanduser().resolve()
        if destino == raiz or destino.is_relative_to(raiz):
            raise ValueError("workspace_dentro_da_raiz")
        workspace = preparar_workspace(args.workspace)
        inicio = time.perf_counter()
        medicoes = coletar(raiz, inspecionar_onnx=args.inspecionar_onnx, pacote=args.pacote.absolute() if args.pacote else None)
        medicoes["endpoints"] = {
            "status": "observado_no_codigo",
            "referencia": "docs/motores/2026-10-16-rotas.md",
            "metodo": "mapa_estatico_das_rotas_reais_sem_importar_api",
            "custos_dinamicos": None,
            "motivo": "carga_passadas_e_latencia_nao_medidas_nesta_fase",
            "distincoes": {
                "pontuar": "satisfacao_emocao_fusor_sem_ironia",
                "atribuir": "satisfacao_emocao_ironia_decomposicao",
                "analisar": "atribuicao_e_oclusao_por_fala_ate_61_variantes_no_lote",
                "replay": "2c_lotes_unitarios_e_fusor_por_prefixo",
                "deriva": "satisfacao_emocao_e_z_scores",
                "grafo_modelo": "fusor_mas_podem_carregar_motor_inteiro",
                "saude": "aquecimento_de_carga_assincrono",
                "prontidao": "estado_sem_carga",
                "repontuar": "202_e_thread_ate_estado_terminal",
                "demais": "rotas_sem_motor_enumeradas_na_referencia",
            },
        }
        dados = resultado("inventario", condicoes={"operacao": "inventario_estatico_sem_inferencia", "backend": None, "motivo_backend": "nenhum_modelo_carregado", "onnx_estrutura_solicitada": args.inspecionar_onnx, "diretorios_modelos": list(DIRETORIOS_MODELOS), "cabecalho_safetensors_limite_bytes": LIMITE_CABECALHO, "texto_limite_bytes": LIMITE_TEXTO, "rede": False, "pickle": False, "variaveis_apenas_nomes": True}, medicoes=medicoes)
        dados["condicoes"]["duracao_s"] = time.perf_counter() - inicio
        dados["comando"].extend(["--raiz", str(raiz), "--workspace", str(workspace)])
        if args.inspecionar_onnx:
            dados["comando"].append("--inspecionar-onnx")
        if args.pacote:
            dados["comando"].extend(["--pacote", str(args.pacote.absolute())])
        dados["artefatos"] = [
            {chave: arquivo[chave] for chave in ("caminho", "sha256", "bytes")}
            for arquivo in medicoes["arquivos"]
        ]
        dados["condicoes"]["hashes"] = {
            arquivo["caminho"]: arquivo["sha256"] for arquivo in medicoes["arquivos"]
        }
        salvar_resultado(workspace, dados)
        print("inventario: concluido; ausencias e limites registrados")
        return 0
    except ValueError:
        print("inventario: entrada_ou_workspace_recusado")
        return 2
    except Exception:
        if workspace is not None:
            try:
                salvar_resultado(workspace, resultado("inventario", "erro", "falha_inesperada_sanitizada"))
            except Exception:
                pass
        print("inventario: falha_inesperada_sanitizada")
        return 1


if __name__ == "__main__":
    sys.exit(main())
