"""Corpus sintético de contratos e perturbações, não um holdout de qualidade.

Os rótulos do simulador são receitas sintéticas; os casos dirigidos não recebem
rótulo de satisfação. O manifesto registra expectativas do modelo canônico,
nunca probabilidades ou resultados fabricados de um motor.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

from fraus.ingest.simulador import FRASES_POR_ROTULO, gerar_lote
from fraus.modelos import Conversa, Mensagem
from scripts.analise_motores.comum import (
    RAIZ, SEMENTE, parser_base, preparar_workspace, resultado, salvar_resultado,
)

INICIO_DIRIGIDAS = datetime(2026, 10, 16, 12, tzinfo=timezone.utc)
ARQUIVOS = ("conversas.jsonl", "manifesto.json")


def _registro(conversa: Conversa, grupo: str, par_id: str | None, rotulo: int | None) -> dict:
    return {"id": conversa.id, "grupo": grupo, "par_id": par_id,
            "rotulo_sintetico": rotulo, "conversa": conversa.model_dump(mode="json")}


def _adicionar_par(registros: list[dict], grupo: str, indice: int,
                   variantes: tuple[list[tuple[str, str, int]], list[tuple[str, str, int]]],
                   *, escalacoes: tuple[bool, bool] = (False, False),
                   encerradas: tuple[bool, bool] = (True, True)) -> None:
    """Offsets em segundos preservam o mesmo relógio nas duas variantes do par."""
    par_id = f"ouro-{grupo}-{indice:02d}"
    for variante, falas, escalou, encerrada in zip(("a", "b"), variantes, escalacoes, encerradas, strict=True):
        mensagens = [Mensagem(autor=autor, texto=texto,
                             enviada_em=INICIO_DIRIGIDAS + timedelta(seconds=segundos))
                     for autor, texto, segundos in falas]
        conversa = Conversa(id=f"{par_id}-{variante}", canal="ouro_sintetico",
                            iniciada_em=INICIO_DIRIGIDAS,
                            encerrada_em=mensagens[-1].enviada_em if encerrada else None,
                            escalou_para_humano=escalou, mensagens=mensagens)
        registros.append(_registro(conversa, grupo, par_id, None))


def _par_de_textos(registros: list[dict], grupo: str, indice: int, a: str, b: str) -> None:
    _adicionar_par(registros, grupo, indice,
                   ([('cliente', a, 0), ('bot', 'Recebi sua mensagem.', 12)],
                    [('cliente', b, 0), ('bot', 'Recebi sua mensagem.', 12)]))


def gerar_registros() -> list[dict]:
    """Gera 120 conversas do simulador e 40 pares autorais válidos e fixos."""
    registros = [_registro(c, "simulador", None, rotulo)
                 for c, rotulo in gerar_lote(FRASES_POR_ROTULO, quantidade=120, semente=SEMENTE)]

    for indice, (a, b) in enumerate((
        ("Olá, posso ajudar?", "Seu protocolo foi aberto."),
        ("Aguarde um instante.", "Continuamos aguardando."),
        ("Pedido enviado.", "Pedido entregue."),
        ("Transferindo o atendimento.", "Atendimento recebido."),
        ("Não houve resposta.", "Encerramos o protocolo."),
    ), 1):
        _adicionar_par(registros, "sem_cliente", indice,
                       ([("bot", a, 0)], [("bot", a, 0), ("humano", b, 12)]),
                       escalacoes=(False, True))

    for indice, (a, b) in enumerate((
        ("", " "), ("\t", "\n"), ("\u200b", "\u200d"),
        ("\u00a0", "\u2060"), ("\ufeff", " \t\n"),
    ), 1):
        _par_de_textos(registros, "cliente_vazio", indice, a, b)

    for indice, (a, b) in enumerate((
        ("vlw", "blz"), ("ok, obrigado", "OK, OBRIGADO!"),
        ("valeu", "muito obrigada"), ("entendi", "certo"),
        ("obg", "só isso mesmo, valeu"),
    ), 1):
        _par_de_textos(registros, "cortesia", indice, a, b)

    for indice, (a, b) in enumerate((
        ("O problema foi resolvido.", "O problema não foi resolvido."),
        ("Estou satisfeito com a solução.", "Não estou satisfeito com a solução."),
        ("O serviço é bom.", "O serviço não é bom."),
        ("Não tive nenhum problema.", "Tive um problema grave."),
        ("A cobrança está correta.", "A cobrança está incorreta."),
    ), 1):
        _par_de_textos(registros, "valencia_negacao", indice, a, b)

    for indice, (a, b) in enumerate((
        ("que atendimento maravilhoso, resolveu em segundos", "que atendimento maravilhoso, so esperei 3 horas"),
        ("ótimo serviço, resolveram rápido", "ótimo serviço, só esperei 3 horas"),
        ("parabéns, meu pedido chegou certo", "parabéns, perderam meu pedido de novo"),
        ("adorei receber a solução", "adorei repetir meu problema dez vezes"),
        ("perfeito, a cobrança foi corrigida", "perfeito, me cobraram duas vezes"),
    ), 1):
        _par_de_textos(registros, "ironia", indice, a, b)

    for indice, (a, b) in enumerate((
        ("Resolveram meu problema 🙂", "Resolveram meu problema 😡"),
        ("Ainda estou esperando 🙏", "Ainda estou esperando 👩\u200d💻"),
        ("Meu pedido chegou 👍", "Meu pedido chegou 👍🏽"),
        ("Atendimento encerrado ❤️", "Atendimento encerrado 💔"),
        ("Conseguimos resolver 👨\u200d👩\u200d👧\u200d👦", "Conseguimos resolver 🏳️\u200d🌈"),
    ), 1):
        _par_de_textos(registros, "emoji", indice, a, b)

    for indice, (a, b) in enumerate((
        ("Vocês resolveram meu problema, obrigado.", "vcs resolveram meu problema, vlw"),
        ("O atendimento foi péssimo.", "o atendimneto foi pessimo"),
        ("Não resolveram nada.", "NÃO RESOLVERAM NADA!!!"),
        ("Foi muito bom.", "foi muuuuito boooom!!!"),
        ("O café chegou frio, número ①.", "O cafe\u0301 chegou frio, número ①. 漢字 𝄞"),
    ), 1):
        _par_de_textos(registros, "estilo", indice, a, b)

    _adicionar_par(registros, "estrutura_tempo_longo", 1,
                   ([("cliente", "Meu pedido não chegou.", 0), ("bot", "Vou verificar.", 12)],
                    [("cliente", "Meu pedido não chegou.", 0), ("bot", "Vou verificar.", 60 * 60 * 24 * 365)]))
    _adicionar_par(registros, "estrutura_tempo_longo", 2,
                   ([("cliente", "Preciso cancelar a cobrança.", 0), ("bot", "Vou verificar.", 12)],
                    [("cliente", "Preciso cancelar a cobrança.", 0), ("humano", "Vou verificar.", 12)]),
                   escalacoes=(False, True))
    _adicionar_par(registros, "estrutura_tempo_longo", 3,
                   ([("cliente", "Continuo sem acesso.", 0), ("bot", "Aguarde.", 12)],
                    [("cliente", "Continuo sem acesso.", 0), ("bot", "Aguarde.", 12)]),
                   encerradas=(True, False))
    _adicionar_par(registros, "estrutura_tempo_longo", 4,
                   ([("cliente", "O aplicativo falha.", 0), ("bot", "Reinicie.", 12),
                     ("cliente", "Continua falhando.", 24)],
                    [("bot", "O aplicativo falha.", 0), ("cliente", "Reinicie.", 12),
                     ("cliente", "Continua falhando.", 24)]))
    contexto = " ".join(["Detalhe do histórico do atendimento e do protocolo informado."] * 80)
    _par_de_textos(registros, "estrutura_tempo_longo", 5,
                   "Não resolveram meu problema. " + contexto,
                   contexto + " Não resolveram meu problema.")
    return registros


def _tem_symlink(caminho: Path) -> bool:
    # Inspecionar antes de resolve: um alias que aponta para dentro também é recusado.
    return any(p.is_symlink() for p in (caminho, *caminho.parents))


def _destino_autorizado(caminho: str | Path, workspace: Path) -> Path:
    alvo = Path(caminho).expanduser().absolute()
    if _tem_symlink(alvo):
        raise ValueError("symlink recusado")
    alvo = alvo.resolve()
    permitido = (RAIZ / "tests/golden/analise_motores").resolve()
    if not alvo.is_relative_to(workspace) and alvo != permitido:
        raise ValueError("destino nao autorizado")
    if any(_tem_symlink(alvo / nome) for nome in ARQUIVOS):
        raise ValueError("symlink recusado")
    return alvo


def _json(dados: object) -> str:
    return json.dumps(dados, ensure_ascii=False, sort_keys=True, allow_nan=False)


def main(argv: list[str] | None = None) -> int:
    parser = parser_base("Gerar corpus sintético determinístico de contratos e paridade.")
    parser.add_argument("--saida", default=str(RAIZ / "tests/golden/analise_motores"))
    opcoes = parser.parse_args(argv)
    workspace = None
    try:
        bruto = Path(opcoes.workspace).expanduser().absolute()
        if _tem_symlink(bruto):
            raise ValueError("symlink recusado")
        # Recusar aliases dos arquivos de resultado antes de qualquer gravação comum.
        for sufixo in (".gitignore", "home", "cache", "tmp", "experimentos/resultados/ouro.json"):
            if _tem_symlink(bruto / sufixo):
                raise ValueError("symlink recusado")
        workspace = preparar_workspace(bruto)
        destino = _destino_autorizado(opcoes.saida, workspace)
        registros = gerar_registros()
        texto = "".join(_json(r) + "\n" for r in registros)
        digest = hashlib.sha256(texto.encode("utf-8")).hexdigest()
        expectativas = {}
        for registro in registros:
            conversa = Conversa.model_validate(registro["conversa"])
            expectativas[registro["id"]] = {
                "tem_sinal_cliente": conversa.tem_sinal_cliente,
                "motivo_sem_sinal": conversa.motivo_sem_sinal,
                "score_nota_categoria_nulos": not conversa.tem_sinal_cliente,
            }
        manifesto = {
            "schema_version": 1, "semente": SEMENTE, "quantidade": len(registros),
            "sha256_conversas": digest,
            "grupos": dict(sorted(Counter(r["grupo"] for r in registros).items())),
            "origem": "120 gerar_lote(FRASES_POR_ROTULO); 80 casos dirigidos autorais",
            "rotulos_sao_ground_truth": False,
            "uso_rotulos": "Rótulos sintéticos do simulador não são ground truth para F1; dirigidas sem rótulo de satisfação.",
            "uso_pares": "Pares diagnósticos; emoji, negação, ironia e estrutura podem alterar o sentido, sem promessa de invariância.",
            "expectativas": expectativas,
        }
        destino.mkdir(parents=True, exist_ok=True)
        (destino / "conversas.jsonl").write_bytes(texto.encode("utf-8"))
        (destino / "manifesto.json").write_bytes((_json(manifesto) + "\n").encode("utf-8"))
        dados = resultado("ouro", condicoes={"n": len(registros), "semente": SEMENTE,
                          "operacao": "geracao_corpus_sintetico", "hashes": {"conversas.jsonl": digest}},
                          artefatos=[{"caminho": str(destino / nome),
                                      "sha256": hashlib.sha256((destino / nome).read_bytes()).hexdigest()}
                                     for nome in ARQUIVOS],
                          medicoes={"quantidade": len(registros), "grupos": manifesto["grupos"]})
        dados["comando"] += ["--workspace", str(workspace), "--saida", str(destino)]
        salvar_resultado(workspace, dados)
        return 0
    except (ValueError, OSError):
        if workspace is not None:
            salvar_resultado(workspace, resultado("ouro", "nao_verificado", "destino_inseguro_ou_indisponivel"))
        else:
            print(_json({"fase": "ouro", "status": "nao_verificado", "motivo": "workspace_inseguro_ou_indisponivel"}))
        return 2
    except Exception:
        if workspace is not None:
            salvar_resultado(workspace, resultado("ouro", "erro", "falha_geracao_corpus"))
        else:
            print(_json({"fase": "ouro", "status": "erro", "motivo": "falha_geracao_corpus"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
