"""Avaliacao POR FATIA: onde o modelo erra, e nao so quanto.

Acuracia agregada esconde o que a banca pergunta primeiro -- "e se a conversa
for curta?", "e se o cliente so disser obrigado?". Uma media de 0,95 pode ser
0,99 em conversa longa e 0,60 em conversa de uma fala, e o numero unico nao
deixa ver a diferenca.

Aqui mora so a PARTE PURA: dizer a que fatias uma conversa pertence e contar
acerto por fatia. Quem roda os modelos e `scripts/avaliar_por_fatias.py`. A
separacao existe para as regras de fatia serem testadas sem 1 GB de pesos.

O que ISTO NAO E: medida de desempenho em atendimento real. As conversas
avaliadas vem do simulador (o unico corpus rotulado com timestamps que o
projeto tem), e a fatia de latencia e parcialmente circular -- o simulador
sorteia a latencia por rotulo. O relatorio diz isso ao lado de cada numero.
"""

from collections import defaultdict
from statistics import median

from fraus.modelos import Conversa
from fraus.sinais.emoji import emojis_com_posicao
from fraus.sinais.tempo import latencias_da_conversa

def fatias_de(conversa: Conversa) -> dict[str, str]:
    """Eixo -> valor da fatia. Sem sinal, a conversa nao entra em avaliacao
    nenhuma (invariante 2): quem chama filtra antes. Por isso nao ha eixo "so
    cortesia" -- desde 15/09/2026 essa conversa e sem sinal (fraus/cortesia.py)
    e nunca chega a ter nota para ser avaliada."""
    n = len(conversa.mensagens_cliente)
    latencias = latencias_da_conversa(conversa)
    mediana = median(latencias) if latencias else None
    return {
        "falas do cliente": "1" if n == 1 else "2-3" if n <= 3 else "4+",
        "latencia mediana": (
            "sem medida" if mediana is None
            else "<30 s" if mediana < 30
            else "30-180 s" if mediana <= 180
            else ">180 s"
        ),
        "emoji": "com" if any(_tem_emoji(m.texto) for m in conversa.mensagens_cliente) else "sem",
        "escalou para humano": "sim" if conversa.escalou_para_humano else "nao",
    }


def _tem_emoji(texto: str) -> bool:
    return bool(emojis_com_posicao(texto))


def metricas_por_fatia(
    registros: list[tuple[dict[str, str], int, int]],
) -> dict[str, dict[str, dict]]:
    """`registros`: (fatias, rotulo, predito). Devolve eixo -> valor -> metricas.

    F1-macro so sobre as classes presentes NA FATIA: numa fatia sem neutro,
    contar o neutro como F1 zero puniria a fatia por algo que ela nao tem.
    """
    grupos: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)
    for fatias, rotulo, predito in registros:
        for eixo, valor in fatias.items():
            grupos[(eixo, valor)].append((rotulo, predito))

    saida: dict[str, dict[str, dict]] = defaultdict(dict)
    for (eixo, valor), pares in sorted(grupos.items()):
        acertos = sum(r == p for r, p in pares)
        saida[eixo][valor] = {
            "n": len(pares),
            "acuracia": acertos / len(pares),
            "f1_macro": _f1_macro(pares),
        }
    return dict(saida)


def _f1_macro(pares: list[tuple[int, int]]) -> float:
    classes = sorted({r for r, _ in pares})
    f1s = []
    for classe in classes:
        vp = sum(r == classe and p == classe for r, p in pares)
        fp = sum(r != classe and p == classe for r, p in pares)
        fn = sum(r == classe and p != classe for r, p in pares)
        f1s.append(0.0 if vp == 0 else 2 * vp / (2 * vp + fp + fn))
    return sum(f1s) / len(f1s)
