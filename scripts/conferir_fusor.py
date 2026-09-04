"""Laudo do fusor vigente em `modelos/` -- conferencia que hoje mora na cabeca
de quem retreina, e nesta semana isso pegou dois defeitos reais:

1. O fusor de 40 features aprendeu `ironia_prob_media` com peso POSITIVO
   (+0,77) no eixo satisfeito-menos-insatisfeito -- mais ironia empurrando
   para SATISFEITO, o inverso do que o nome da feature promete. So apareceu
   porque alguem olhou o SINAL dos coeficientes, nao so a acuracia (ver
   `fraus/fusor.py`, comentario acima de `NOMES_FEATURES`).
2. Uma feature de `incongruencia_*` foi treinada com vazamento de rotulo e
   aprendeu a direcao errada -- pego olhando a distribuicao por rotulo, nao
   um numero agregado.

Os dois tem em comum o mesmo defeito de processo: acuracia alta nao denuncia
nem um nem outro (invariante 10). O que denuncia e olhar peso por familia,
ordem de classe e uma frase-sonda concreta -- coisas que uma pessoa cansada
depois de um retreino longo pula, e que este script automatiza para nao
depender de lembranca.

Segue o modelo de `scripts/medir_faixas.py`: instrumento, nao botao. Nao
escreve nada, nao toca no banco, nao ha caminho da API ate aqui -- so imprime
um laudo do artefato que ja esta em `modelos/`.

Como rodar:
    uv run python scripts/conferir_fusor.py
    uv run python scripts/conferir_fusor.py --sem-sonda   # pula as 3 frases,
                                                            # que exigem os
                                                            # tres BERTimbau
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from fraus.api.caminhos import (  # noqa: E402
    CAMINHO_FUSOR,
    CAMINHO_MODELO_EMOCAO,
    CAMINHO_MODELO_IRONIA,
    CAMINHO_MODELO_TEXTO,
    metricas_de,
)
from fraus.fusor import (  # noqa: E402
    NOMES_FEATURES,
    Fusor,
    FusorIncompativelError,
    montar_features,
)
from fraus.indicadores import nota_0_10  # noqa: E402
from fraus.modelos import Conversa, Mensagem  # noqa: E402
from fraus.sinais.emocao import ClassificadorEmocao  # noqa: E402
from fraus.sinais.ironia import ClassificadorIronia, features_ironia  # noqa: E402
from fraus.sinais.texto import ClassificadorTexto, ModeloAusenteError  # noqa: E402

CAMINHO_IMPORTANCIAS = RAIZ / "modelos" / "importancias.json"

# Limiar abaixo do qual um peso do eixo global e reportado como "perto de
# zero". Nao e limiar de significancia estatistica -- e so o corte que separa
# "a feature moveu alguma coisa" de "o treino nao teve o que aprender dela".
LIMIAR_PESO_ZERO = 0.02

# Familias e o sinal ESPERADO no eixo satisfeito-menos-insatisfeito. None
# significa "sem expectativa declarada" -- o laudo lista o peso mas nao
# sinaliza suspeita. So entram aqui as familias onde o significado da feature
# torna o sinal esperado obvio o bastante para automatizar a checagem; o
# resto fica para leitura humana.
SINAL_ESPERADO: dict[str, int] = {
    "incongruencia_polaridade": -1,
    "incongruencia_emoji_texto": -1,
    "incongruencia_marcador_contraste": -1,
    "incongruencia_hiperbole": -1,
    "incongruencia_aspas_ironicas": -1,
    "texto_prob_satisfeito_media": +1,
    "texto_prob_satisfeito_ultima": +1,
    "texto_prob_insatisfeito_media": -1,
    "texto_prob_insatisfeito_max": -1,
    "emoji_score_medio": +1,
    "emoji_frac_positivos": +1,
    "emoji_frac_negativos": -1,
}

# As tres frases-sonda. A ironica e a frase canonica do projeto -- foi ela
# que denunciou o peso invertido de `ironia_prob_media` (ver docstring do
# modulo e o comentario em `fraus/fusor.py`). Ela NAO pontua o fusor (a
# ironia saiu do vetor em 04/09/2026); o que se mede aqui e a cabeca de
# ironia isolada, ao lado do score do fusor sem ela.
FRASES_SONDA = [
    ("satisfeita", "resolveu rapido, muito obrigado! adorei o atendimento", "alta"),
    ("insatisfeita", "pessimo, ja e a terceira vez que explico e ninguem resolve", "baixa"),
    ("ironica", "que atendimento maravilhoso, so esperei 3 horas", "baixa (a ironia inverte o sentido literal)"),
]


def _linha(titulo: str) -> None:
    print(f"\n{'-' * 70}\n{titulo}\n{'-' * 70}")


def _conversa_de(texto: str) -> Conversa:
    agora = datetime.now(timezone.utc)
    return Conversa(
        id="sonda",
        canal="conferencia",
        iniciada_em=agora,
        mensagens=[Mensagem(autor="cliente", texto=texto, enviada_em=agora)],
    )


def conferir_contrato() -> tuple[bool, Fusor | None]:
    """Item 1: `n_features_in_` do scaler contra `len(NOMES_FEATURES)`.

    `Fusor.carregar` ja valida isso e levanta `FusorIncompativelError` -- este
    metodo so captura, para o laudo reportar o veredito em vez de estourar
    com traceback cru na cara de quem rodou.
    """
    _linha("1. contrato (numero de features)")
    try:
        fusor = Fusor.carregar(CAMINHO_FUSOR)
    except FileNotFoundError:
        print(f"REPROVADO: nenhum artefato em {CAMINHO_FUSOR}.")
        return False, None
    except FusorIncompativelError as erro:
        print(f"REPROVADO: {erro}")
        return False, None
    print(f"OK: artefato bate com o contrato vigente ({len(NOMES_FEATURES)} features).")
    return True, fusor


def conferir_ordem_das_classes(fusor: Fusor) -> bool:
    """Item 2: `classes_` precisa ser [0, 1, 2] -- invariante 8.

    Inverter nao gera erro nenhum: faz o sistema pontuar ao contrario em
    silencio, porque `Fusor.pontuar` e `_diferenca` indexam por VALOR de
    classe (INSATISFEITO=0, SATISFEITO=2), nao por posicao.
    """
    _linha("2. ordem das classes")
    classes = list(fusor._pipeline.named_steps["modelo"].classes_)
    esperado = [0, 1, 2]
    if classes == esperado:
        print(f"OK: classes_ = {classes} (0 insatisfeito, 1 neutro, 2 satisfeito).")
        return True
    print(f"REPROVADO: classes_ = {classes}, esperado {esperado}. Invariante 8 quebrada.")
    return False


def conferir_sinal_por_familia(fusor: Fusor) -> list[str]:
    """Item 3: sinal dos pesos por familia, no eixo satisfeito-menos-insatisfeito.

    Devolve a lista de features sinalizadas como suspeitas -- o laudo aponta,
    nao decide: o script nao sabe o que e certo, sabe o que o nome da feature
    promete.
    """
    _linha("3. sinal dos pesos por familia (eixo satisfeito - insatisfeito)")
    eixo = fusor.eixo_global()
    if not eixo:
        print("sem eixo interpretavel (modelo nao treinado com as duas pontas).")
        return []

    familias: dict[str, list[str]] = {}
    for nome in NOMES_FEATURES:
        prefixo = nome.split("_")[0]
        familias.setdefault(prefixo, []).append(nome)

    suspeitas = []
    for familia, nomes in familias.items():
        print(f"\n  {familia}")
        for nome in nomes:
            peso = eixo.get(nome)
            if peso is None:
                print(f"    {nome:<38} fora do artefato (contrato mudou)")
                continue
            sinal_ok = ""
            esperado = SINAL_ESPERADO.get(nome)
            if esperado is not None:
                obtido = 1 if peso > 0 else (-1 if peso < 0 else 0)
                if obtido != 0 and obtido != esperado:
                    sinal_ok = "  <-- suspeito, confira (sinal esperado: " + (
                        "positivo" if esperado > 0 else "negativo"
                    ) + ")"
                    suspeitas.append(nome)
            print(f"    {nome:<38} {peso:+.4f}{sinal_ok}")

    if suspeitas:
        print(f"\n{len(suspeitas)} feature(s) com sinal suspeito: {', '.join(suspeitas)}")
    else:
        print("\nnenhuma feature com sinal contrario ao esperado (das que tem expectativa declarada).")
    return suspeitas


def conferir_pesos_proximos_de_zero(fusor: Fusor) -> list[str]:
    """Item 4: features com |peso| abaixo de `LIMIAR_PESO_ZERO`.

    Peso zero significa que o treino nao teve o que aprender dela -- pode ser
    limitacao declarada (ex.: `emoji_contagem`, que quase nao varia no
    corpus) ou pode ser bug de extracao (feature sempre constante por erro).
    O laudo lista, nao decide qual e o caso.
    """
    _linha("4. features com peso perto de zero (|peso| < %.2f)" % LIMIAR_PESO_ZERO)
    eixo = fusor.eixo_global()
    proximas = [
        (nome, peso) for nome, peso in eixo.items() if abs(peso) < LIMIAR_PESO_ZERO
    ]
    if not proximas:
        print("nenhuma. Todas as features moveram o eixo em algum grau.")
        return []
    for nome, peso in sorted(proximas, key=lambda item: abs(item[1])):
        print(f"  {nome:<38} {peso:+.4f}")
    print(
        f"\n{len(proximas)} feature(s) perto de zero -- confira se e limitacao "
        "declarada ou bug de extracao antes de aceitar."
    )
    return [nome for nome, _ in proximas]


def conferir_frases_sonda(fusor: Fusor) -> bool:
    """Item 5: as tres frases-sonda, pontuadas com os classificadores reais.

    Exige os tres BERTimbau (texto, emocao, ironia). Se algum faltar, reporta
    qual e segue com o resto do laudo -- os itens 1 a 4 nao dependem deles, e
    abortar o script inteiro por um modelo faltando esconderia o resto da
    conferencia.
    """
    _linha("5. frases-sonda")

    try:
        classificador_texto = ClassificadorTexto(CAMINHO_MODELO_TEXTO)
    except ModeloAusenteError as erro:
        print(f"PULADO: {erro}")
        return False
    try:
        classificador_emocao = ClassificadorEmocao(CAMINHO_MODELO_EMOCAO)
    except ModeloAusenteError as erro:
        print(f"PULADO: {erro}")
        return False
    try:
        classificador_ironia = ClassificadorIronia(CAMINHO_MODELO_IRONIA)
    except ModeloAusenteError as erro:
        print(f"PULADO: {erro}")
        return False

    print(
        "a frase 'ironica' e a frase canonica do projeto -- deveria pontuar "
        "BAIXO (baixo score, nota baixa, classe insatisfeito), porque o "
        "elogio e literal mas o sentido e o oposto.\n"
    )
    print(f"  {'frase':<12} {'esperado':<35} {'score':>7} {'nota':>5} {'classe':<13} {'P(ironico)':>11}")
    for rotulo, texto, esperado in FRASES_SONDA:
        conversa = _conversa_de(texto)
        features = montar_features(conversa, classificador_texto, classificador_emocao)
        score = fusor.pontuar(features)
        classe = fusor.prever(features)
        nome_classe = {0: "insatisfeito", 1: "neutro", 2: "satisfeito"}[classe]
        p_ironico = features_ironia(conversa, classificador_ironia)["ironia_prob_media"]
        print(
            f"  {rotulo:<12} {esperado:<35} {score:>7.2f} {nota_0_10(score):>5} "
            f"{nome_classe:<13} {p_ironico:>11.3f}"
        )
    return True


def conferir_metricas_de_treino() -> None:
    """Item 6: acuracia, f1_macro e tamanho dos conjuntos de `modelos/importancias.json`.

    Acuracia alta demais e sintoma, nao vitoria (invariante 10) -- corpus de
    treino que entrega o rotulo (ex.: faixa de latencia disjunta por classe)
    produz numero bonito e modelo inutil. O laudo imprime o numero e o
    lembrete junto, de proposito.
    """
    _linha("6. metricas do treino")
    dados = metricas_de(CAMINHO_IMPORTANCIAS)
    if dados is None:
        print(f"AUSENTE: {CAMINHO_IMPORTANCIAS} nao existe.")
        return
    acuracia = dados.get("acuracia")
    f1_macro = dados.get("f1_macro")
    treino = dados.get("conversas_treino")
    teste = dados.get("conversas_teste")
    rotulo = dados.get("rotulo", "nao registrado")
    print(f"  acuracia:          {acuracia}")
    print(f"  f1_macro:          {f1_macro}")
    print(f"  conversas_treino:  {treino}")
    print(f"  conversas_teste:   {teste}")
    print(f"  rotulo:            {rotulo}")
    if isinstance(acuracia, (int, float)) and acuracia > 0.97:
        print(
            "\n  ATENCAO: acuracia > 0,97. Acuracia alta demais e sintoma, nao "
            "vitoria (invariante 10) -- confira se alguma feature entrega o "
            "rotulo antes de aceitar o artefato. Ver docs/treinamento.md."
        )
    else:
        print(
            "\n  lembrete: acuracia alta demais e sintoma, nao vitoria "
            "(invariante 10) -- este numero sozinho nao substitui os itens "
            "3, 4 e 5 deste laudo."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--sem-sonda",
        action="store_true",
        help="pula o item 5 (frases-sonda), que exige carregar os tres BERTimbau e e lento",
    )
    argumentos = parser.parse_args()

    print("laudo do fusor vigente")
    print(f"artefato: {CAMINHO_FUSOR.resolve()}")

    pontos_de_atencao = 0

    contrato_ok, fusor = conferir_contrato()
    if not contrato_ok:
        pontos_de_atencao += 1
        _linha("resumo")
        print(
            "REPROVADO no item 1 (contrato): sem fusor compativel carregado, "
            "os itens 2 a 5 nao tem o que conferir. Retreine e rode de novo."
        )
        conferir_metricas_de_treino()
        sys.exit(1)

    if not conferir_ordem_das_classes(fusor):
        pontos_de_atencao += 1

    suspeitas = conferir_sinal_por_familia(fusor)
    if suspeitas:
        pontos_de_atencao += 1

    proximas_de_zero = conferir_pesos_proximos_de_zero(fusor)
    if proximas_de_zero:
        pontos_de_atencao += 1

    if not argumentos.sem_sonda:
        conferir_frases_sonda(fusor)

    conferir_metricas_de_treino()

    _linha("resumo")
    if pontos_de_atencao == 0:
        print("passou tudo.")
    else:
        print(f"{pontos_de_atencao} ponto(s) merecem olhar humano antes de aceitar o artefato.")


if __name__ == "__main__":
    main()
