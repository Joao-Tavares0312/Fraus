"""O mapa de features do TypeScript e o contrato do fusor sao duas metades da
mesma verdade -- e so o lado Python tinha guarda.

`tests/test_fusor.py::test_contrato_cobre_todos_os_prefixos_esperados` conhece
os prefixos esperados e ate cita `dashboard/lib/derivacoes.ts` num comentario,
mas nenhum teste atravessava a fronteira de linguagem: nada impedia o mapa TS
de ficar para tras em silencio quando uma familia nova entrasse no vetor. Foi
exatamente o que aconteceu em 03/09/2026 -- a familia `incongruencia_*` (5
features) entrou em `NOMES_FEATURES`, mas `SINAL_POR_PREFIXO` e
`ROTULO_FEATURE` nunca souberam dela. Por um dia, as cinco features caiam no
balde de sobras ("outros") do grafico de pesos, e o rotulo exibido ao usuario
era o proprio nome tecnico em snake_case.

Este teste le `derivacoes.ts` como TEXTO (mesmo padrao de
`tests/test_pii_integracao.py::test_toda_origem_de_dado_real_censura_pii`,
que le arquivos `.py` como texto) e falha se algum prefixo de
`NOMES_FEATURES` nao aparecer em `SINAL_POR_PREFIXO`, ou se alguma chave nao
tiver rotulo em `ROTULO_FEATURE`. Assim a proxima familia nova nao repete o
mesmo silencio.
"""

import pathlib
import re

from fraus.fusor import NOMES_FEATURES

RAIZ = pathlib.Path(__file__).parent.parent
CAMINHO_DERIVACOES = RAIZ / "dashboard" / "lib" / "derivacoes.ts"
CAMINHO_VITRINE = RAIZ / "dashboard" / "app" / "page.tsx"


def _prefixo_de(nome: str) -> str:
    """O prefixo de familia de uma feature, do jeito que `SINAL_POR_PREFIXO` espera.

    A maioria das familias tem prefixo com underscore ("texto_", "emoji_"),
    mas a familia tempo tem dois prefixos SEM underscore: "escalou" e
    "abandonou" sao o nome inteiro da feature, nao um prefixo cortado em "_".
    Uma logica ingenua de `nome.split("_")[0] + "_"` marcaria esses dois como
    "escalou_"/"abandonou_", que nao existe em `SINAL_POR_PREFIXO` -- falso
    positivo. Por isso os dois sao casos especiais aqui, do mesmo jeito que
    sao no arquivo TS.
    """
    if nome in ("escalou", "abandonou"):
        return nome
    return nome.split("_")[0] + "_"


def test_todo_prefixo_de_nomes_features_esta_no_mapa_de_sinal_do_dashboard():
    fonte = CAMINHO_DERIVACOES.read_text(encoding="utf-8")

    prefixos_esperados = {_prefixo_de(nome) for nome in NOMES_FEATURES}

    faltando = [
        prefixo
        for prefixo in prefixos_esperados
        if f'"{prefixo}"' not in fonte
    ]

    assert not faltando, (
        f"prefixo(s) sem entrada em SINAL_POR_PREFIXO (dashboard/lib/derivacoes.ts): "
        f"{faltando}. Toda familia nova de NOMES_FEATURES precisa de uma linha em "
        "SINAL_POR_PREFIXO, senao cai muda no balde 'outros' do grafico de pesos."
    )


def test_toda_feature_de_nomes_features_tem_rotulo_no_dashboard():
    fonte = CAMINHO_DERIVACOES.read_text(encoding="utf-8")

    bloco = re.search(
        r"ROTULO_FEATURE: Record<string, string> = \{(.*?)\n\};",
        fonte,
        re.DOTALL,
    )
    assert bloco, "nao encontrei o bloco ROTULO_FEATURE em derivacoes.ts"
    corpo = bloco.group(1)

    sem_rotulo = [nome for nome in NOMES_FEATURES if f"{nome}:" not in corpo]

    assert not sem_rotulo, (
        f"feature(s) sem entrada em ROTULO_FEATURE (dashboard/lib/derivacoes.ts): "
        f"{sem_rotulo}. Sem rotulo, o usuario ve o nome tecnico em snake_case cru "
        "na tela."
    )


def test_a_vitrine_anuncia_o_numero_real_de_features():
    """A landing page promete "nenhum numero inventado" -- isto e o que cobra.

    `dashboard/app/page.tsx` mostra a contagem de features ao visitante, e
    `docs/handoff.md` declara que os numeros da LP sao fatos do codigo. Em
    04/09/2026 o contrato caiu de 40 para 38 e a LP continuou anunciando 35:
    numero falso numa tela publica, que e exatamente o que a promessa exclui.
    Nenhum teste pegava porque a contagem e um literal em TypeScript, do outro
    lado da fronteira de linguagem.

    A honestidade metodologica do projeto nao vale menos por estar na vitrine
    em vez de estar num sinal -- vale MAIS, porque e a parte que o visitante ve
    antes de qualquer ressalva.
    """
    fonte = CAMINHO_VITRINE.read_text(encoding="utf-8")

    anunciado = re.search(
        r'\[\s*"(\d+)"\s*,\s*"features no fusor"(?:\s*,\s*"[^"]+")?\s*\]',
        fonte,
    )
    assert anunciado, (
        "nao encontrei o contador de features em dashboard/app/page.tsx. Se o "
        "formato mudou, atualize esta busca -- nao apague a guarda."
    )

    assert int(anunciado.group(1)) == len(NOMES_FEATURES), (
        f"a vitrine anuncia {anunciado.group(1)} features, mas NOMES_FEATURES tem "
        f"{len(NOMES_FEATURES)}. Atualize dashboard/app/page.tsx -- e as outras "
        "mencoes do numero em lp/Contador.tsx e lp/Constelacao.tsx junto."
    )


def test_sem_sinal_e_notacao_e_nao_so_texto():
    """A §1.1 do DESIGN.md promete cabeca vazada para o sem sinal.

    Guarda que atravessa a fronteira de linguagem, no mesmo molde de
    `test_a_vitrine_anuncia_o_numero_real_de_features`: o pytest le o TSX
    como texto. O que ela impede e a regressao silenciosa de alguem trocar a
    notacao de volta por uma string, que nenhum gate de front pegaria.
    """
    componentes = RAIZ / "dashboard" / "components"
    assert (componentes / "CabecaVazada.tsx").is_file()

    # EtiquetaCategoria entrou aqui no fix round 1: categoria == null desenhava
    # um ponto CHEIO cinza no mesmo slot dos tres pontos cheios coloridos --
    # "cinza dentro da escala" que a DESIGN.md §5 probe por nome. E a
    # instancia mais vista da peca (toda linha sem sinal da tabela e da lista
    # de piores atendimentos), entao a guarda cobre ela tambem.
    for arquivo in ("TabelaConversas.tsx", "DistribuicaoScores.tsx", "EtiquetaCategoria.tsx"):
        fonte = (componentes / arquivo).read_text(encoding="utf-8")
        assert "CabecaVazada" in fonte, f"{arquivo} ainda imprime sem sinal cru"


def test_a_cabeca_vazada_carrega_rotulo_textual():
    """Categoria nunca e comunicada so por cor -- nem so por forma.

    Um anel oco sem rotulo obrigaria o leitor a saber a convencao, e o
    PRODUCT.md exige o rotulo textual junto.
    """
    caminho = RAIZ / "dashboard" / "components" / "CabecaVazada.tsx"
    fonte = caminho.read_text(encoding="utf-8")
    assert "sem sinal" in fonte


def test_a_tela_modelo_abre_pelo_veredito():
    """O que o avaliador precisa ler primeiro nao pode estar no meio da pagina.

    As tres ressalvas estruturais do modelo -- ironia fora do vetor, metricas
    suspeitas e corpus de tempo sintetico -- sobem para um sistema dominante
    no topo.
    """
    painel = RAIZ / "dashboard"
    componente = painel / "components" / "modelo" / "EstadoDoModelo.tsx"
    assert componente.is_file()

    pagina = (painel / "app" / "dashboard" / "modelo" / "page.tsx").read_text(
        encoding="utf-8"
    )
    assert "EstadoDoModelo" in pagina

    # Premissa desta guarda: os componentes sao importados SEM alias. A
    # comparacao abaixo casa o nome literal `<EstadoDoModelo`/`<Simulador` no
    # USO em JSX -- se algum dia um `import { EstadoDoModelo as X }` renomear
    # o componente, o `index()` de baixo devolve -1 e falha de um jeito
    # ilegivel (ValueError sem contexto). Esta asserção existe so para essa
    # falha vir com o motivo escrito, em vez de obrigar quem le a caçar um
    # -1. Acoplar a guarda ao identificador é o padrao ja usado em
    # `dashboard/lib/hierarquia.test.ts`; nao vale parsear TypeScript aqui so
    # para tolerar alias.
    assert "EstadoDoModelo as" not in pagina, (
        "esta guarda pressupoe `EstadoDoModelo` importado sem alias -- "
        "se foi renomeado no import, atualize tambem o nome usado nesta "
        "comparacao de ordem"
    )

    # A comparacao tem que ser sobre o USO em JSX (`<EstadoDoModelo`,
    # `<Simulador`), nao sobre a primeira ocorrencia do nome no arquivo --
    # senao o teste passa so pela ordem alfabetica do bloco de import
    # (`EstadoDoModelo` importado antes de `Simulador`), que nao garante nada
    # sobre a ordem de renderizacao no corpo da pagina. `<Simulador` so
    # aparece uma vez no arquivo, como elemento; o titulo em prosa do Painel
    # ("Simulador ao vivo") nao bate no prefixo `<Simulador`.
    assert pagina.index("<EstadoDoModelo") < pagina.index("<Simulador")
