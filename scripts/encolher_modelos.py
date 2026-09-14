"""Converte os tres BERTimbau para ONNX int8 -- SEM RETREINAR NADA.

O PROBLEMA. Os tres checkpoints somam 1,25 GB (417 MB cada, fp32) e o `torch`
que os executa pesa mais 497 MB. Isso e ~1,75 GB de imagem para um sistema
cujo trabalho, em runtime, e multiplicar matrizes de 110M de parametros em CPU.

O QUE ESTE SCRIPT FAZ, e por que ele nao viola a invariante 10. Ele nao treina:
exporta o grafo do checkpoint que JA EXISTE para ONNX e aplica quantizacao
DINAMICA int8 -- uma transformacao pos-treino sobre os pesos ja aprendidos. O
que o modelo aprendeu nao muda; muda a precisao com que os numeros sao
guardados e a biblioteca que os executa.

POR QUE DINAMICA E NAO ESTATICA. A estatica da mais compressao, e exige um
conjunto de CALIBRACAO representativo -- e escolher esse conjunto errado
introduziria exatamente o tipo de vies silencioso que a invariante 10 existe
para impedir. A dinamica quantiza so os PESOS de antemao e calcula a escala das
ativacoes em tempo de execucao, sem calibracao nenhuma.

O QUE ELE NAO ACEITA DE GRACA. Encolher e barato; encolher e continuar
acertando e a pergunta. Por isso a conversao termina medindo a CONCORDANCIA
com o modelo original nas mesmas frases -- diferenca maxima de probabilidade e
divergencia de rotulo -- e o script FALHA se a divergencia passar do teto.
Numero que sai daqui sem comparacao e numero em que ninguem pode confiar.

Uso:

    uv sync --extra conversao
    uv run python scripts/encolher_modelos.py
    uv run python scripts/encolher_modelos.py --so satisfacao   # um de cada vez
"""

import argparse
import shutil
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ORIGEM = RAIZ / "modelos"
DESTINO = RAIZ / "modelos-onnx"

# Os tres, pelo nome do diretorio. A ironia esta aqui apesar de nao pontuar:
# ela continua obrigatoria para a API subir (invariante 7) e continua sendo
# lida por mensagem na dashboard, entao ela pesa na imagem igual as outras.
MODELOS = ("satisfacao", "emocao", "ironia")

# Frases de aferição. Elas nao sao corpus de avaliacao -- sao SONDA: o que se
# mede aqui e se o modelo quantizado responde o MESMO que o original, nao se
# ele acerta. Por isso variam em polaridade, tamanho e ruido de digitacao, que
# e onde a quantizacao costuma divergir primeiro.
SONDAS = [
    "o atendimento foi pessimo, esperei 3 horas e ninguem resolveu",
    "muito obrigado, resolveram rapidinho!",
    "ok",
    "que atendimento maravilhoso, so esperei 3 horas",
    "nao gostei de ficar esperando",
    "AINDA ESTOU ESPERANDO UMA RESPOSTA",
    "meu boleto venceu e o sistema nao deixa emitir a segunda via",
    "vcs sao otimos, valeu msm 😊",
    "cancela minha conta agora",
    "tudo certo por aqui, era so isso",
]

# Tetos de divergencia aceita entre o original e o quantizado.
#
# 0,02 de diferenca maxima de probabilidade e um limite APERTADO de proposito:
# o score do Fraus e uma projecao dessas probabilidades num eixo 0-100, e as
# fronteiras de nota (6/7, 8/9) ja custaram um defeito real neste projeto. Dois
# centesimos de probabilidade nao movem uma nota; dois decimos poderiam.
#
# Rotulo divergente e ZERO tolerado: se a classe vencedora muda numa sonda, a
# quantizacao mudou a opiniao do modelo, e ai nao e mais o mesmo modelo.
TETO_DIFERENCA_PROB = 0.02
TETO_ROTULOS_DIVERGENTES = 0


def _tamanho_mb(caminho: Path) -> float:
    if caminho.is_file():
        return caminho.stat().st_size / 1024 / 1024
    return sum(f.stat().st_size for f in caminho.rglob("*") if f.is_file()) / 1024 / 1024


def _probabilidades_torch(diretorio: Path, textos: list[str]) -> list[list[float]]:
    """A opiniao do modelo ORIGINAL -- a referencia contra a qual se compara."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizador = AutoTokenizer.from_pretrained(str(diretorio))
    modelo = AutoModelForSequenceClassification.from_pretrained(str(diretorio))
    modelo.eval()
    with torch.inference_mode():
        entradas = tokenizador(
            textos, truncation=True, max_length=192, padding=True, return_tensors="pt"
        )
        return torch.softmax(modelo(**entradas).logits, dim=-1).tolist()


def _probabilidades_onnx(diretorio: Path, textos: list[str]) -> list[list[float]]:
    """A opiniao do modelo QUANTIZADO, pelo mesmo caminho que o runtime usara."""
    from fraus.sinais.onnx import SessaoOnnx

    return SessaoOnnx(diretorio).prever(textos)


def converter(nome: str, precisao: str = "int8") -> dict:
    """Exporta UM modelo para ONNX, opcionalmente quantizando, medindo o que mudou.

    `precisao` existe por causa da VARIANTE MISTA, e ela merece explicacao
    porque parece inconsistencia: por que oferecer `fp32`, que nao encolhe peso
    nenhum?

    Porque o ONNX fp32 JA GANHA a metade do problema sem pagar nada. A imagem
    de inferencia sao ~1,75 GB, e 497 MB deles sao o `torch` -- que o
    `onnxruntime` dispensa. Exportar em fp32 troca o executor sem mexer num
    unico peso: a diferenca de probabilidade fica na ordem do erro de ponto
    flutuante, e o modelo continua sendo o mesmo modelo no sentido forte.

    E isso e o que viabiliza a mistura. A medicao de 10/09 recusou a int8 nos
    tres porque UMA conversa atravessou duas faixas e trocou de veredito
    (59,95 -> 85,61, detrator -> promotor). Quem governa o score e a
    SATISFACAO; emocao e ironia entram como features ao lado de 30 outras. Se a
    satisfacao ficar intacta em fp32 e so as outras duas forem quantizadas, a
    causa do flip sai por construcao -- e sobra a pergunta empirica de quanto
    desvio as outras duas ainda injetam, que e o que `comparar_backends.py`
    responde.

    Nao ha `fp16` aqui de proposito. Em CPU o `onnxruntime` tem poucos kernels
    fp16 nativos: o normal e ele inserir `Cast` e computar em fp32, o que
    devolve o consumo de MEMORIA ao tamanho original e ainda paga a conversao.
    fp16 economiza disco e nao economiza RAM, e RAM e o que limita a maquina de
    1 GB. Implementar o caminho sem medir isso primeiro seria vender ganho que
    talvez nao exista.
    """
    from onnxruntime.quantization import QuantType, quantize_dynamic
    from optimum.onnxruntime import ORTModelForSequenceClassification
    from transformers import AutoTokenizer

    origem = ORIGEM / f"bertimbau-{nome}"
    destino = DESTINO / f"bertimbau-{nome}"
    if not origem.is_dir():
        raise SystemExit(f"checkpoint ausente: {origem}")

    print(f"\n=== {nome} ===", file=sys.stderr)
    print(f"  original: {_tamanho_mb(origem):.1f} MB", file=sys.stderr)

    # 1. A referencia, medida ANTES de qualquer conversao -- se o original for
    #    carregado depois, uma mudanca de ambiente no meio do caminho passaria
    #    por diferenca de quantizacao.
    referencia = _probabilidades_torch(origem, SONDAS)

    # 2. Exportacao do grafo. `export=True` roda o tracing uma vez; o resultado
    #    e o MESMO modelo, em outro formato.
    destino.mkdir(parents=True, exist_ok=True)
    modelo = ORTModelForSequenceClassification.from_pretrained(str(origem), export=True)
    modelo.save_pretrained(str(destino))
    AutoTokenizer.from_pretrained(str(origem)).save_pretrained(str(destino))

    # `config.json` carrega `id2label`, e ele NAO e decorativo aqui: a ordem das
    # classes (0 insatisfeito, 1 neutro, 2 satisfeito) e a invariante 8, e
    # perde-la na conversao faria o sistema pontuar ao contrario em silencio.
    shutil.copy2(origem / "config.json", destino / "config.json")
    for extra in ("metricas.json",):
        if (origem / extra).exists():
            shutil.copy2(origem / extra, destino / extra)

    fp32 = destino / "model.onnx"
    print(f"  onnx fp32: {_tamanho_mb(fp32):.1f} MB", file=sys.stderr)

    if precisao == "fp32":
        # Nada a quantizar, e nada a apagar: aqui o `model.onnx` fp32 E o
        # artefato final. O `model.onnx_data` (pesos externos) tambem fica --
        # apaga-lo deixaria um grafo sem pesos, que carrega e falha na primeira
        # inferencia, bem longe daqui.
        tamanho_final = _tamanho_mb(destino)
        print(f"  mantido em fp32: {tamanho_final:.1f} MB", file=sys.stderr)
        convertido = _probabilidades_onnx(destino, SONDAS)
        maior_diferenca = max(
            abs(a - b)
            for linha_a, linha_b in zip(referencia, convertido)
            for a, b in zip(linha_a, linha_b)
        )
        divergentes = [
            texto
            for texto, a, b in zip(SONDAS, referencia, convertido)
            if a.index(max(a)) != b.index(max(b))
        ]
        return {
            "nome": nome,
            "precisao": precisao,
            "mb_original": _tamanho_mb(origem),
            "mb_final": tamanho_final,
            "maior_diferenca_prob": maior_diferenca,
            "rotulos_divergentes": divergentes,
        }

    # 3. Quantizacao dinamica int8. QInt8 nos pesos; as ativacoes ganham escala
    #    em tempo de execucao, sem conjunto de calibracao.
    int8 = destino / "model_int8.onnx"
    # `per_channel=True` NAO e ajuste fino: e a diferenca entre aceitar e
    # recusar. Medido sobre `bertimbau-satisfacao`, com as mesmas sondas:
    #
    #   estrategia                     tamanho   max dp   classe mudou
    #   qint8 em tudo                   105,5 M   0,4535   1 sonda
    #   qint8 so em MatMul              172,0 M   0,4953   1 sonda
    #   qint8 MatMul + per_channel      172,4 M   0,1385   nenhuma
    #   quint8 so em MatMul             172,0 M   0,2620   1 sonda
    #   qint8 em tudo + per_channel     105,9 M   0,1015   nenhuma   <- esta
    #   qint8 tudo + per_channel + reduce_range
    #                                   105,9 M   0,1798   nenhuma
    #
    # A escala POR CANAL da a cada coluna de peso a propria faixa, em vez de
    # espremer a matriz inteira numa so -- e numa camada de atencao as colunas
    # tem magnitudes muito diferentes. Sem ela, a variante mais compacta era
    # tambem a que mudava de opiniao.
    #
    # Note que a intuicao comum ("nao quantize o embedding, so MatMul") sai
    # PIOR aqui nas duas pontas: 63% maior e menos fiel. Foi medido, nao
    # herdado de tutorial.
    quantize_dynamic(fp32, int8, weight_type=QuantType.QInt8, per_channel=True)
    fp32.unlink()  # o intermediario nao vai para lugar nenhum
    dados_externos = destino / "model.onnx_data"
    if dados_externos.exists():
        dados_externos.unlink()
    int8.rename(destino / "model.onnx")

    tamanho_final = _tamanho_mb(destino)
    print(f"  onnx int8: {tamanho_final:.1f} MB", file=sys.stderr)

    # 4. A pergunta que importa: ele ainda pensa a mesma coisa?
    convertido = _probabilidades_onnx(destino, SONDAS)
    maior_diferenca = max(
        abs(a - b)
        for linha_a, linha_b in zip(referencia, convertido)
        for a, b in zip(linha_a, linha_b)
    )
    divergentes = [
        texto
        for texto, a, b in zip(SONDAS, referencia, convertido)
        if a.index(max(a)) != b.index(max(b))
    ]

    return {
        "nome": nome,
        "precisao": precisao,
        "mb_original": _tamanho_mb(origem),
        "mb_final": tamanho_final,
        "maior_diferenca_prob": maior_diferenca,
        "rotulos_divergentes": divergentes,
    }


def medir_latencia(nome: str, repeticoes: int = 3) -> tuple[float, float]:
    """Segundos por lote das SONDAS, original contra convertido."""
    origem = ORIGEM / f"bertimbau-{nome}"
    destino = DESTINO / f"bertimbau-{nome}"

    def cronometrar(funcao) -> float:
        funcao(SONDAS)  # aquece: a primeira chamada paga carregamento de grafo
        inicio = time.perf_counter()
        for _ in range(repeticoes):
            funcao(SONDAS)
        return (time.perf_counter() - inicio) / repeticoes

    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizador = AutoTokenizer.from_pretrained(str(origem))
    modelo = AutoModelForSequenceClassification.from_pretrained(str(origem))
    modelo.eval()

    def com_torch(textos):
        with torch.inference_mode():
            entradas = tokenizador(
                textos, truncation=True, max_length=192, padding=True, return_tensors="pt"
            )
            return torch.softmax(modelo(**entradas).logits, dim=-1).tolist()

    from fraus.sinais.onnx import SessaoOnnx

    sessao = SessaoOnnx(destino)
    return cronometrar(com_torch), cronometrar(sessao.prever)


def main() -> int:
    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument("--so", choices=MODELOS, help="converter apenas um")
    argumentos.add_argument(
        "--precisao",
        choices=("int8", "fp32"),
        default="int8",
        help="int8 quantiza; fp32 so troca o executor (ver docstring de converter)",
    )
    argumentos.add_argument(
        "--latencia", action="store_true", help="medir tempo por lote (mais lento)"
    )
    opcoes = argumentos.parse_args()

    alvos = (opcoes.so,) if opcoes.so else MODELOS
    laudos = [converter(nome, opcoes.precisao) for nome in alvos]

    print("\n" + "=" * 66, file=sys.stderr)
    print(f"{'modelo':12} {'antes':>10} {'depois':>10} {'reducao':>9} {'max Δp':>9}", file=sys.stderr)
    for laudo in laudos:
        reducao = laudo["mb_original"] / laudo["mb_final"]
        print(
            f"{laudo['nome']:12} {laudo['mb_original']:9.1f}M {laudo['mb_final']:9.1f}M "
            f"{reducao:8.2f}x {laudo['maior_diferenca_prob']:9.4f}",
            file=sys.stderr,
        )
    total_antes = sum(l["mb_original"] for l in laudos)
    total_depois = sum(l["mb_final"] for l in laudos)
    print(
        f"{'TOTAL':12} {total_antes:9.1f}M {total_depois:9.1f}M "
        f"{total_antes / total_depois:8.2f}x",
        file=sys.stderr,
    )

    if opcoes.latencia:
        print("\nlatencia por lote de 10 frases:", file=sys.stderr)
        for nome in alvos:
            antes, depois = medir_latencia(nome)
            print(
                f"  {nome:12} torch {antes * 1000:7.1f} ms -> onnx {depois * 1000:7.1f} ms "
                f"({antes / depois:.2f}x)",
                file=sys.stderr,
            )

    # O PORTAO. Ele existe para este script nao poder terminar em verde com um
    # modelo que mudou de opiniao -- "encolheu 4x" e uma frase perigosa quando
    # nao vem acompanhada de "e continua respondendo o mesmo".
    problemas = []
    for laudo in laudos:
        if laudo["maior_diferenca_prob"] > TETO_DIFERENCA_PROB:
            problemas.append(
                f"{laudo['nome']}: diferenca maxima de probabilidade "
                f"{laudo['maior_diferenca_prob']:.4f} passa do teto {TETO_DIFERENCA_PROB}"
            )
        if len(laudo["rotulos_divergentes"]) > TETO_ROTULOS_DIVERGENTES:
            problemas.append(
                f"{laudo['nome']}: a classe vencedora MUDOU em "
                f"{len(laudo['rotulos_divergentes'])} sonda(s): "
                f"{laudo['rotulos_divergentes']}"
            )

    if problemas:
        print("\nCONVERSAO RECUSADA:", file=sys.stderr)
        for problema in problemas:
            print(f"  - {problema}", file=sys.stderr)
        print(
            "\nOs arquivos convertidos estao em modelos-onnx/ para inspecao, mas "
            "NAO devem ser promovidos: o modelo quantizado nao responde o mesmo "
            "que o original.",
            file=sys.stderr,
        )
        return 1

    print("\nconversao aceita: os tres respondem o mesmo dentro do teto.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
