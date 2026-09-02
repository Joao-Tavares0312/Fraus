import Link from "next/link";
import {
  ArrowDown,
  ArrowRight,
  Clock3,
  Drama,
  HeartPulse,
  LibraryBig,
  MessageSquareText,
  SmilePlus,
  Type,
} from "lucide-react";
import GlitchText from "@/components/GlitchText";
import { BotaoEstelar } from "@/components/lp/BotaoEstelar";
import { CampoDeParticulas } from "@/components/lp/CampoDeParticulas";
import { Constelacao } from "@/components/lp/Constelacao";
import { Contador } from "@/components/lp/Contador";
import { Esteira } from "@/components/lp/Esteira";
import { FechoVitrine } from "@/components/lp/FechoVitrine";
import { PartituraExemplo } from "@/components/lp/PartituraExemplo";
import { Revelar } from "@/components/lp/Revelar";
import { botaoVitrineContorno, botaoVitrineFantasma, botaoVitrineMiudo } from "@/components/lp/botoes";
import { MarcaFraus } from "@/components/shell/MarcaFraus";
import { loginDisponivel, usuarioDaSessao } from "@/lib/sessao";

/**
 * =============================================================================
 * A PÁGINA PÚBLICA DO PRODUTO — reescrita do zero em 01/09/2026.
 * =============================================================================
 *
 * O DIAGNÓSTICO DA VERSÃO ANTERIOR, porque ele governa tudo que vem abaixo. Ela
 * não estava errada em conteúdo; estava PLANA em forma, e um defeito explicava
 * todos os outros: **faixa dinâmica estreita**. Manchete em 4,75rem, títulos de
 * seção em 2,25rem, corpo em 14–18px, e absolutamente tudo dentro do mesmo
 * `max-w-6xl px-6`. Sem quebra de escala e sem quebra de largura, a página
 * inteira lia num único tom de voz — competente e esquecível.
 *
 * As seis referências fixadas pelo dono do projeto (Corn Revolution, Personaal,
 * Lando Norris de um lado; Cloudflare, Stripe, Revolut do outro) não têm estilo
 * visual em comum. Têm GRAMÁTICA em comum, e é ela que foi importada:
 *
 *   1. CONTRASTE DE ESCALA VIOLENTO — display enorme contra etiqueta mono
 *      minúscula, com quase nada no meio (`.display-vitrine` / `.etiqueta-vitrine`);
 *   2. RITMO DE LARGURA — full-bleed alternando com contido, para a página não
 *      ler como documento;
 *   3. O PRODUTO COMO ARTEFATO — a lição do Stripe: a tela do produto aparece
 *      grande e centrada, com o texto de legenda, e não espremida ao lado de um
 *      parágrafo que disputa a mesma largura;
 *   4. MOVIMENTO COMO CONTEÚDO — a esteira entrega os sete sinais a quem rola
 *      rápido; o glitch entrega a tese sem uma palavra a mais.
 *
 * O ESPETÁCULO É ARGUMENTADO, NÃO DECORATIVO — e esta é a linha que separa esta
 * página de um template com WebGL colado por cima. Cada peça pesada responde a
 * uma ideia do produto:
 *
 *   · o CAMPO DE PARTÍCULAS é o tema do produto, não um plano de fundo genérico;
 *   · o GLITCH cai sobre “ok, obrigado 🙂” e só sobre ela. O produto se chama
 *     Fraus — o dáimon romano do ENGANO — e a tese é que aquela frase educada
 *     esconde um detrator. Texto que diz uma coisa e mostra outra é literalmente
 *     o assunto da ferramenta. É a única peça da página que É o argumento;
 *   · a REFRAÇÃO do fecho fecha o arco: a última frase é vista através do vidro,
 *     como tudo que a ferramenta lê.
 *
 * O QUE NÃO MUDOU, e é a linha que separa reescrita de invenção: **nenhum fato
 * foi tocado**. 35 features, 7 sinais, 3 BERTimbau e 0 LLMs em runtime continuam
 * sendo fatos do código; o cartão continua ilustrativo e continua DIZENDO isso;
 * as três honestidades metodológicas estão palavra por palavra. A cor continua
 * obedecendo o encoding — âmbar = dito, azul = medido, dourado = ação — e
 * nenhum componente de terceiro abriu exceção nisso.
 *
 * EMENDA AO CABEÇALHO ANTERIOR, que ficou mentindo e agora está corrigido: ele
 * dizia “nunca o espetáculo WebGL, que é a antítese de uma ferramenta de
 * leitura”. A frase estava certa sobre a FERRAMENTA e errada ao estendê-la à
 * VITRINE. A dashboard segue sem WebGL; a distinção está escrita em
 * `components/lp/CampoDeParticulas.tsx`.
 */

const SINAIS = [
  {
    Icone: MessageSquareText,
    nome: "Texto",
    cor: "--dito",
    descricao:
      "BERTimbau fine-tunado lê cada mensagem do cliente e devolve probabilidade por fala — é o que permite apontar quem puxou a nota.",
  },
  {
    Icone: SmilePlus,
    nome: "Emoji",
    cor: "--no-emoji",
    descricao:
      "Léxico de sentimento com a posição relativa do emoji na mensagem — o 🙂 do fim de frase não vale o do começo.",
  },
  {
    Icone: Clock3,
    nome: "Tempo",
    cor: "--tempo",
    descricao: "Latência, escalação e abandono como features aprendidas.",
  },
  {
    Icone: HeartPulse,
    nome: "Emoção",
    cor: "--emocao",
    descricao: "Sete classes, com desprezo derivado da díade raiva + nojo.",
  },
  {
    Icone: LibraryBig,
    nome: "Léxico",
    cor: "--lexico",
    descricao: "SentiLex-PT02 com escopo de negação, mais o léxico curado.",
  },
  {
    Icone: Drama,
    nome: "Ironia",
    cor: "--ironia",
    descricao:
      "“Ótimo atendimento” nem sempre elogia. Uma cabeça binária só para virar a leitura dos outros sinais.",
  },
  {
    Icone: Type,
    nome: "Estilo",
    cor: "--estilo",
    descricao:
      "CAIXA ALTA, pontuação!!!, alongamennnto e palavrão — a forma de escrever carrega o afeto que a palavra esconde.",
  },
] as const;

const FATOS = [
  { numero: 35, rotulo: "features no fusor" },
  { numero: 7, rotulo: "famílias de sinal" },
  { numero: 3, rotulo: "BERTimbau fine-tunados" },
  { numero: 0, rotulo: "LLMs em runtime" },
] as const;

const HONESTIDADES = [
  {
    n: "01",
    titulo: "O NPS é estimado, não perguntado",
    texto:
      "Ninguém responde pesquisa aqui: a categoria vem do texto, e toda tela que a exibe carrega a etiqueta de estimativa. Apresentar como NPS declarado seria falso.",
  },
  {
    n: "02",
    titulo: "Ausência de dado não é insatisfação",
    texto:
      "Conversa em que o cliente não falou aparece como “sem sinal” — nunca como zero, em célula, gráfico ou média. Não medir e medir zero são respostas diferentes.",
  },
  {
    n: "03",
    titulo: "O sinal de tempo é treinado em sintético",
    texto:
      "Nenhum corpus público de atendimento em português tem timestamps de diálogo, então esse sinal é calibrado por literatura. Limitação declarada, não segredo.",
  },
] as const;

const ATRIBUICOES = [
  {
    fala: "“passei 40 minutos esperando pra isso”",
    peso: "▼ puxou para baixo",
  },
  { fala: "“ok, obrigado 🙂”", peso: "▼ ironia provável" },
  { fala: "“a atendente Maria foi ótima”", peso: "▲ segurou a nota" },
] as const;

/**
 * AS QUATRO CHAMADAS que anotam o cartão do produto, na ORDEM DO PIPELINE — a
 * mesma da faixa `7 sinais → 35 features → regressão logística → score`.
 *
 * Cada uma herda a cor da camada de que fala, e isso é o encoding, não escolha:
 * as duas primeiras são âmbar porque comentam o que foi DITO; as duas últimas
 * são azuis porque comentam o que foi MEDIDO. Quem sobe os olhos para o cartão
 * encontra as mesmas duas cores separadas pela mesma régua.
 *
 * O TEXTO COMENTA, NÃO ACRESCENTA. Nenhuma chamada afirma número que o cartão
 * não mostre, e nenhuma sugere que os valores saíram do modelo — o rodapé do
 * cartão diz, e continua dizendo, que o exemplo é ilustrativo.
 */
const CHAMADAS = [
  {
    n: "01",
    lado: "esq",
    cor: "--dito-texto",
    titulo: "o dito",
    texto:
      "Fala, texto e emoji, acima da régua. O material bruto é educado por natureza — quase ninguém xinga o robô antes de desistir.",
  },
  {
    n: "02",
    lado: "esq",
    cor: "--dito-texto",
    titulo: "a contradição",
    texto:
      "O agradecimento contradiz os 40 minutos de espera. É a cabeça de ironia que autoriza virar a leitura dos outros sinais.",
  },
  {
    n: "03",
    lado: "dir",
    cor: "--medido-texto",
    titulo: "o medido",
    texto:
      "Latência, emoção e polaridade descem para baixo da régua. Nenhuma delas é perguntada ao cliente — todas são lidas.",
  },
  {
    n: "04",
    lado: "dir",
    cor: "--medido-texto",
    titulo: "o veredito",
    texto:
      "Score, nota e categoria são derivados no servidor, nunca no cliente, e chegam à tela sempre com a etiqueta de estimativa.",
  },
] as const;

/**
 * Uma chamada. O FIO é o que amarra o texto ao cartão: sem ele são quatro
 * parágrafos soltos ao lado de uma figura, e o olho não sabe que um comenta o
 * outro. Ele nasce na cor da camada e se apaga na direção do cartão —
 * gradiente e não linha chapada, porque linha cheia encostando na borda leria
 * como moldura, e o que se quer é um gesto apontando.
 */
function Chamada({ n, lado, cor, titulo, texto }: (typeof CHAMADAS)[number]) {
  const paraDireita = lado === "esq";
  return (
    <Revelar>
      <div className={paraDireita ? "text-right" : "text-left"}>
        <p className="etiqueta-vitrine mb-3" style={{ color: `var(${cor})` }}>
          {n} · {titulo}
        </p>
        <p className="text-sm leading-relaxed text-muted-foreground">{texto}</p>
        <div
          aria-hidden
          className="mt-4 h-px w-full"
          style={{
            background: `linear-gradient(to ${
              paraDireita ? "right" : "left"
            }, transparent, var(${cor}))`,
            opacity: 0.45,
          }}
        />
      </div>
    </Revelar>
  );
}

/**
 * A COLUNA DE LEITURA, uma constante e não uma classe repetida à mão.
 *
 * Era assim que a versão anterior garantia largura igual em TUDO — e era esse o
 * problema. Aqui ela garante largura igual só onde a largura deve ser igual: o
 * full-bleed passou a ser exceção declarada (as seções que não a usam dizem por
 * quê), em vez de esquecimento.
 */
const COLUNA = "mx-auto w-full max-w-6xl px-6";

export default async function PaginaInicial() {
  const usuario = await usuarioDaSessao();
  const temLogin = await loginDisponivel();

  const acaoPrimaria = usuario
    ? { href: "/dashboard", rotulo: "Ir para a dashboard" }
    : temLogin
      ? { href: "/entrar", rotulo: "Entrar" }
      : { href: "/dashboard", rotulo: "Abrir a dashboard" };

  return (
    <div className="relative">
      {/* O FIO DE PROGRESSO DE LEITURA, colado na borda de baixo do header.
          CSS puro via `animation-timeline: scroll()` — nenhum listener, nenhum
          quadro de JavaScript. Ver `.progresso-leitura` no globals.css sobre por
          que ele simplesmente não existe onde o navegador não suporta, em vez de
          aparecer cheio e parado. */}
      <header className="vidro-fino sticky top-0 z-40 border-x-0 border-t-0">
        <div
          aria-hidden
          className="progresso-leitura absolute inset-x-0 bottom-0 h-px bg-primary"
        />
        <div className={`${COLUNA} flex items-center justify-between py-3`}>
          <Link
            href="/"
            aria-label="Fraus — início"
            className="flex items-center gap-2.5 outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <MarcaFraus tamanho={30} />
            <span className="text-sm font-semibold tracking-tight">Fraus</span>
          </Link>
          <nav className="flex items-center gap-1 sm:gap-4">
            <a
              href="#como-funciona"
              className="hidden text-sm text-muted-foreground transition-colors duration-150 ease-fluid hover:text-foreground sm:block"
            >
              Como funciona
            </a>
            <a
              href="#honestidade"
              className="hidden text-sm text-muted-foreground transition-colors duration-150 ease-fluid hover:text-foreground sm:block"
            >
              Honestidade
            </a>
            {!usuario && temLogin && (
              <Link href="/cadastrar" className={botaoVitrineFantasma}>
                Criar conta
              </Link>
            )}
            <Link href={acaoPrimaria.href} className={botaoVitrineMiudo}>
              {acaoPrimaria.rotulo}
            </Link>
          </nav>
        </div>
      </header>

      <main>
        {/* ============================== HERO ==============================

            OCUPA A TELA, e em `svh`: no navegador móvel a barra de endereço
            some ao rolar, e `100vh` empurraria o CTA para baixo da dobra
            justamente no aparelho em que a dobra é mais cara.

            O CARTÃO SAIU DAQUI, e é a mudança estrutural mais importante da
            reescrita. Na versão anterior a `PartituraExemplo` dividia o hero
            com a manchete numa grade de duas colunas, e o resultado era que
            NENHUM DOS DOIS tinha tamanho: a manchete travava em ~4,75rem porque
            só sobrava metade da largura, e o cartão — que é a melhor peça da
            página, porque é o único lugar em que o produto aparece — chegava
            espremido. Separados, os dois crescem. */}
        {/* `min-h` e nao `h`: a secao CRESCE se o conteudo pedir, em vez de
            recortar. E o `py` encolhe em tela baixa pelo mesmo motivo que o
            corpo do display encolhe -- ver `.display-vitrine` no globals.css,
            onde esta o defeito que isto conserta. */}
        <section className="relative flex min-h-[88svh] items-center">
          <div className="pointer-events-none absolute inset-0 -z-10">
            <CampoDeParticulas />
          </div>

          <div className={`${COLUNA} py-14 lg:py-20`}>
            <Revelar className="max-w-4xl">
              <p className="etiqueta-vitrine mb-7 inline-flex items-center gap-2.5 text-muted-foreground">
                {/* O ponto NÃO pisca. Indicador pulsante sem mudança de estado
                    por trás é ruído com cara de alerta — DESIGN.md §6. */}
                <span aria-hidden className="size-1.5 rounded-full bg-primary" />
                satisfação inferida · sem pesquisa
              </p>

              {/* O GLITCH, e só nesta frase.
                  `enableOnHover` porque glitch perpétuo atrás de um `<h1>` é
                  exatamente a decoração-pela-decoração que o DESIGN.md §6
                  proíbe — e porque no repouso a frase precisa ser lida sem
                  esforço, já que ela É a manchete. No hover ela se descola, que
                  é o gesto: a frase educada não é o que parece.
                  É `<span>` dentro do `<h1>` e o texto é real (`data-text` +
                  conteúdo), então busca e leitor de tela recebem a manchete
                  inteira — não há canvas nem imagem aqui. */}
              {/* SEM `.display-aurora` AQUI, e a tentativa está registrada porque o
                  defeito é sutil e alguém vai querer tentar de novo: gradiente
                  em texto usa `background-clip: text` com
                  `-webkit-text-fill-color: transparent`, e isso recorta TODO o
                  conteúdo do elemento — inclusive os filhos. Aplicado neste
                  `<h1>` ele fez duas coisas erradas de uma vez: transformou o
                  🙂 numa bolha branca (o emoji é colorido pela fonte, e a
                  fonte perde para o recorte) e apagou o âmbar do
                  `text-dito-texto` da frase citada, que é o encoding do
                  PRODUCT.md e não decoração. A aurora vive nos
                  `.titulo-vitrine`, que são texto puro. */}
              <h1 className="display-vitrine">
                O cliente escreve{" "}
                <GlitchText
                  enableOnHover
                  speed={0.4}
                  corAntes="var(--medido)"
                  corDepois="var(--emocao)"
                  className="inline text-dito-texto"
                >
                  {"“ok, obrigado 🙂”"}
                </GlitchText>{" "}
                e sai insatisfeito.
              </h1>

              <p className="mt-7 max-w-2xl text-pretty text-lg leading-relaxed text-muted-foreground">
                A nota declarada mente. O Fraus lê o atendimento inteiro — o que
                foi <span className="text-dito-texto">dito</span> e o que pôde
                ser <span className="text-medido-texto">medido</span> — e estima
                a satisfação sem perguntar nada.
              </p>

              <div className="mt-9 flex flex-wrap items-center gap-3">
                <BotaoEstelar href={acaoPrimaria.href}>
                  {acaoPrimaria.rotulo}
                </BotaoEstelar>
                {!usuario && temLogin && (
                  <Link href="/cadastrar" className={botaoVitrineContorno}>
                    Criar conta
                  </Link>
                )}
              </div>
            </Revelar>
          </div>

          {/* A dica de rolagem só existe de `sm` para cima: num hero de 92svh
              no celular a próxima seção já encosta na dobra, então ela
              resolveria um problema que ali não existe e roubaria altura de
              quem tem menos. */}
          <div
            aria-hidden
            className="absolute inset-x-0 bottom-8 hidden justify-center sm:flex"
          >
            <ArrowDown className="size-4 text-muted-foreground/60" />
          </div>
        </section>

        {/* ===================== ESTEIRA (full-bleed) ===================== */}
        <Esteira />

        {/* ==================== O ARTEFATO: a partitura ====================

            A SEÇÃO QUE A VERSÃO ANTERIOR NÃO TINHA. A lição vem do Stripe: o
            produto aparece grande e centrado, com o texto servindo de legenda.
            Esta é a única peça da página que mostra o que a ferramenta de fato
            faz — ela merecia mais que meia coluna de hero.

            AS CHAMADAS ANOTADAS são a segunda rodada. A primeira versão só
            EXIBIA o cartão, e cartão sozinho no meio de muito escuro não ensina
            nada: quem não conhece o produto vê um print de chat e segue
            rolando. Agora ele é LIDO em voz alta — quatro chamadas apontando
            para faixas do cartão, na ordem em que o sistema processa: o dito, a
            contradição, o medido, o veredito. É a mesma técnica de anotação que
            Stripe e Linear usam em captura de produto, e ela transforma a seção
            de vitrine em explicação.

            A NUMERAÇÃO NÃO É ENFEITE: é a ordem do pipeline, a mesma da faixa
            `7 sinais → 35 features → regressão → score` mais abaixo.

            AS CHAMADAS SÓ EXISTEM DE `lg` PARA CIMA, e a alternativa foi
            considerada e rejeitada: empilhá-las acima e abaixo do cartão no
            celular partiria a leitura contínua da conversa em duas metades
            separadas por texto explicativo. Numa tela estreita o cartão fala
            melhor sozinho — ele já traz os próprios rótulos ("DITO ↑",
            "↓ MEDIDO", "DETRATOR · ESTIMADO"). Nada se perde: as chamadas
            COMENTAM o que o cartão mostra, não acrescentam fato. */}
        <section className="relative py-28 lg:py-36">
          {/* O HOLOFOTE, e ele resolve um problema de composição real: o cartão
              é uma superfície escura sobre fundo escuro, e sem nada por trás ele
              boiava. A luz é a da nebulosa do tema (`--atelie-fria`), então não
              é recurso novo — é a mesma cena, concentrada onde o olho para. */}
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 -z-10"
            style={{
              background:
                "radial-gradient(58% 46% at 50% 52%, var(--atelie-fria), transparent 70%)",
              opacity: "calc(var(--atelie-op-fria) * 0.8)",
            }}
          />

          <Revelar className={`${COLUNA} max-w-3xl text-center`}>
            <p className="etiqueta-vitrine mb-5 text-primary">o veredito</p>
            <h2 className="titulo-vitrine display-aurora">
              Duas vozes, separadas por uma régua
            </h2>
            <p className="mx-auto mt-6 max-w-xl text-pretty leading-relaxed text-muted-foreground">
              Acima da linha, o que o cliente{" "}
              <span className="text-dito-texto">disse</span>. Abaixo, o que a
              conversa deixou <span className="text-medido-texto">medir</span>.
              A distância entre as duas é a informação.
            </p>
          </Revelar>

          {/* GRADE DE TRÊS COLUNAS — chamadas, cartão, chamadas. Grade e não
              posicionamento absoluto: absoluto exigiria saber a altura do cartão
              em cada largura, e ele cresce quando o texto quebra. A grade deixa
              o navegador resolver. */}
          <div
            className={`${COLUNA} mt-16 grid items-center gap-y-10 lg:grid-cols-[1fr_minmax(0,34rem)_1fr] lg:gap-x-10`}
          >
            <div className="hidden flex-col gap-16 lg:flex">
              {CHAMADAS.filter((c) => c.lado === "esq").map((c) => (
                <Chamada key={c.n} {...c} />
              ))}
            </div>

            <Revelar className="flex justify-center">
              {/* O cartão nasceu com `max-w-xl` para caber na coluna do hero
                  antigo. Aqui a coluna da grade é que manda: o wrapper solta o
                  teto sem editar o componente, que continua servindo a qualquer
                  largura que o pai der. */}
              <div className="w-full [&>figure]:max-w-none">
                <PartituraExemplo />
              </div>
            </Revelar>

            <div className="hidden flex-col gap-16 lg:flex">
              {CHAMADAS.filter((c) => c.lado === "dir").map((c) => (
                <Chamada key={c.n} {...c} />
              ))}
            </div>
          </div>
        </section>

        {/* ================= FATOS REAIS (full-bleed) =================

            A PRIMEIRA QUEBRA DE LARGURA depois da esteira, e ela é deliberada.
            Os números são ENORMES e mono: na versão anterior eram `text-4xl`
            dentro de caixinhas com borda — do tamanho de um título qualquer,
            ou seja, sem hierarquia nenhuma apesar de serem a prova mais dura
            que a página tem. */}
        <Revelar>
          <section
            aria-label="Números do sistema"
            className="border-y border-border/50"
          >
            <div
              className={`${COLUNA} grid grid-cols-2 gap-x-6 gap-y-10 py-16 lg:grid-cols-4 lg:py-20`}
            >
              {FATOS.map(({ numero, rotulo }) => (
                <div key={rotulo}>
                  <div className="num text-[clamp(3.25rem,7vw,5.5rem)] font-medium leading-[0.9] tracking-[-0.04em]">
                    <Contador valor={numero} />
                  </div>
                  {/* A régua do sistema (`--linha`), a única linha da casa que
                      AFIRMA algo. Aqui ela afirma que o número acima e a
                      legenda abaixo são a mesma medida. */}
                  <div className="mt-5 h-px w-full bg-linha" />
                  <div className="mt-3 text-sm text-muted-foreground">
                    {rotulo}
                  </div>
                </div>
              ))}
            </div>
            <div className={`${COLUNA} pb-6`}>
              <p className="etiqueta-vitrine text-muted-foreground/70">
                fatos do código · fraus.fusor.NOMES_FEATURES
              </p>
            </div>
          </section>
        </Revelar>

        {/* ========================= SETE SINAIS ========================= */}
        <section id="como-funciona" className="scroll-mt-24 py-28 lg:py-36">
          <Revelar className={`${COLUNA} max-w-2xl`}>
            <p className="etiqueta-vitrine mb-5 text-primary">como funciona</p>
            <h2 className="titulo-vitrine display-aurora">Sete sinais, um veredito</h2>
            <p className="mt-6 leading-relaxed text-muted-foreground">
              Cada família lê a conversa por um ângulo próprio. Um fusor leve
              combina tudo num score de 0 a 100 — a inferência roda local, em
              CPU, e nenhuma mensagem sai da máquina para ser pontuada.
            </p>
          </Revelar>

          {/* A CONSTELAÇÃO — a peça que substituiu a bento grid de sete
              cartões, que era a coisa mais genérica da página. Ver
              `components/lp/Constelacao.tsx`: ela não é ilustração de tema, é o
              diagrama de arquitetura do fusor desenhado com o vocabulário
              visual que o tema já tinha, e cada estrela usa o TOKEN de cor
              daquele sinal na dashboard.

              É `aria-hidden` porque é a figura da lista logo abaixo — os nomes
              e as descrições vivem lá, em HTML de verdade. */}
          <Revelar className={`${COLUNA} mt-6`}>
            <div className="mx-auto max-w-4xl">
              <Constelacao />
            </div>
          </Revelar>

          {/* A LISTA, e ela é editorial e não mais um cartão de vidro.
              A figura acima já dá a estrutura (sete pontas, um centro); repetir
              essa estrutura numa grade de caixas seria dizer a mesma coisa duas
              vezes com menos elegância. Aqui o que importa é o TEXTO, então o
              tratamento é o de texto: régua fina, nome grande, descrição.
              O ponto colorido amarra cada linha à sua estrela lá em cima — é o
              único elo entre a figura e a lista, e ele custa 10px. */}
          <div
            className={`${COLUNA} mt-16 grid gap-x-12 gap-y-px sm:grid-cols-2`}
          >
            {SINAIS.map(({ Icone, nome, descricao, cor }) => (
              <Revelar key={nome}>
                <div className="group flex gap-5 border-t border-border/50 py-7">
                  {/* UM MARCADOR SÓ, e ele carrega as duas informações.
                      A primeira versão tinha ícone cinza E bolinha colorida
                      antes do nome — dois símbolos para a mesma coisa, um
                      ruído clássico de lista. O ícone recebeu a COR DO SINAL:
                      ele continua dando a leitura rápida de "que tipo de coisa
                      é esta" e passa a amarrar a linha à sua estrela lá em
                      cima, que era todo o trabalho da bolinha. */}
                  <Icone
                    aria-hidden
                    className="mt-0.5 size-5 shrink-0 opacity-80 transition-opacity duration-150 ease-fluid group-hover:opacity-100"
                    style={{ color: `var(${cor})` }}
                  />
                  <div>
                    <h3 className="text-lg font-medium tracking-tight">
                      {nome}
                    </h3>
                    <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                      {descricao}
                    </p>
                  </div>
                </div>
              </Revelar>
            ))}
          </div>

          <Revelar className={COLUNA}>
            <div className="vidro mt-3 flex flex-wrap items-center justify-center gap-x-4 gap-y-2 px-6 py-6 font-mono text-xs text-muted-foreground sm:text-sm">
              <span className="text-dito-texto">7 sinais</span>
              <ArrowRight aria-hidden className="size-3.5 shrink-0" />
              <span>35 features</span>
              <ArrowRight aria-hidden className="size-3.5 shrink-0" />
              <span>regressão logística</span>
              <ArrowRight aria-hidden className="size-3.5 shrink-0" />
              <span className="text-medido-texto">score 0–100</span>
              <ArrowRight aria-hidden className="size-3.5 shrink-0" />
              <span className="text-medido-texto">
                NPS estimado<span className="align-super text-[9px]">*</span>
              </span>
            </div>
            <p className="etiqueta-vitrine mt-3 text-right text-muted-foreground/70">
              * estimado a partir do texto — e rotulado assim em toda tela
            </p>
          </Revelar>
        </section>

        {/* ============ A REGRA MESTRA (full-bleed, dito/medido) ============

            Full-bleed, e com a régua REAL no meio: a divisória usa `--linha`, o
            mesmo token da régua do sistema. A seção não fala SOBRE a régua —
            ela É a régua, em tamanho de página. */}
        <Revelar>
          <section
            aria-label="A regra mestra da interface"
            className="border-y border-border/50"
          >
            <div className={`${COLUNA} grid lg:grid-cols-2`}>
              <div className="border-b border-linha py-16 lg:border-b-0 lg:border-r lg:py-24 lg:pr-14">
                <p className="etiqueta-vitrine text-dito-texto">
                  acima da linha
                </p>
                <h3 className="mt-6 text-[clamp(1.9rem,3.4vw,3rem)] font-medium leading-[1.05] tracking-[-0.03em]">
                  O que foi <span className="text-dito-texto">dito</span>
                </h3>
                <p className="mt-5 max-w-md leading-relaxed text-muted-foreground">
                  Fala, texto, emoji — o que o cliente articulou, em âmbar. É o
                  material bruto, educado por natureza: quase ninguém xinga o
                  robô antes de desistir.
                </p>
              </div>
              <div className="py-16 lg:py-24 lg:pl-14">
                <p className="etiqueta-vitrine text-medido-texto">
                  abaixo da linha
                </p>
                <h3 className="mt-6 text-[clamp(1.9rem,3.4vw,3rem)] font-medium leading-[1.05] tracking-[-0.03em]">
                  O que foi <span className="text-medido-texto">medido</span>
                </h3>
                <p className="mt-5 max-w-md leading-relaxed text-muted-foreground">
                  Score, probabilidade, latência, tendência — em azul. A
                  distância entre as duas vozes é a informação que o produto
                  vende, e a interface inteira é desenhada para mostrá-la.
                </p>
              </div>
            </div>
          </section>
        </Revelar>

        {/* ========================= ATRIBUIÇÃO ========================= */}
        <section className="py-28 lg:py-36">
          <div
            className={`${COLUNA} grid items-center gap-14 lg:grid-cols-[0.95fr_1fr]`}
          >
            <Revelar>
              <p className="etiqueta-vitrine mb-5 text-primary">atribuição</p>
              <h2 className="titulo-vitrine display-aurora">
                O número aponta as falas que o puxaram
              </h2>
              <p className="mt-6 leading-relaxed text-muted-foreground">
                O sinal de texto pontua <em>por mensagem</em>: o Fraus mostra
                quais falas derrubaram (ou salvaram) a nota de cada atendimento,
                em vez de devolver um score opaco para a operação discutir às
                cegas. É o que um número sozinho não conta — e o que um produto
                vizinho não copia com honestidade.
              </p>
            </Revelar>
            <Revelar>
              <ul className="flex flex-col gap-2">
                {ATRIBUICOES.map(({ fala, peso }) => (
                  <li
                    key={fala}
                    className="vidro-fino flex flex-col gap-1.5 px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:gap-4"
                  >
                    <span className="text-sm text-dito-texto sm:text-base">
                      {fala}
                    </span>
                    <span className="shrink-0 font-mono text-xs text-medido-texto">
                      {peso}
                    </span>
                  </li>
                ))}
              </ul>
              <p className="etiqueta-vitrine mt-3 text-right text-muted-foreground/70">
                exemplo ilustrativo
              </p>
            </Revelar>
          </div>
        </section>

        {/* ========================= HONESTIDADE ========================= */}
        <section
          id="honestidade"
          className="scroll-mt-24 border-t border-border/50 py-28 lg:py-36"
        >
          <Revelar className={`${COLUNA} max-w-2xl`}>
            <p className="etiqueta-vitrine mb-5 text-primary">
              honestidade metodológica
            </p>
            <h2 className="titulo-vitrine display-aurora">O que é medido, o que é estimado</h2>
            <p className="mt-6 leading-relaxed text-muted-foreground">
              A ferramenta leva o nome do daemon romano do engano por um motivo:
              o texto engana, e medir isso exige dizer com precisão o que é fato
              e o que é inferência.
            </p>
          </Revelar>

          {/* SEM CARTÃO, e a escolha é semântica. Esta é a seção em que o
              produto admite os próprios limites; embrulhar as três admissões em
              vidro as faria ler como três benefícios a mais. Numeral grande,
              régua, texto — tratamento editorial, que é como uma ressalva se
              apresenta quando é levada a sério. */}
          <div
            className={`${COLUNA} mt-16 grid gap-x-10 gap-y-14 lg:grid-cols-3`}
          >
            {HONESTIDADES.map(({ n, titulo, texto }) => (
              <Revelar key={n}>
                <span className="num block text-3xl font-medium text-primary">
                  {n}
                </span>
                <div className="mt-5 h-px w-full bg-linha" />
                <h3 className="mt-5 text-xl font-medium tracking-tight">
                  {titulo}
                </h3>
                <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                  {texto}
                </p>
              </Revelar>
            ))}
          </div>
        </section>

        {/* ==================== O FECHO (full-bleed) ====================

            A última frase é vista ATRAVÉS do vidro — é o arco fechando: tudo o
            que a ferramenta lê, ela lê através de uma superfície. Ver
            `components/lp/FechoVitrine.tsx` para as três decisões de integração
            (por que o `GlassSurface` não substitui o `vidro` da casa, por que a
            cor do `WarpText` é um hex, e por que há um `<h2>` invisível). */}
        <Revelar>
          <section className={`${COLUNA} pb-28 lg:pb-36`}>
            <FechoVitrine titulo="Pronto para ler o que o cliente não disse?">
              <div className="flex flex-wrap items-center justify-center gap-3">
                <BotaoEstelar href={acaoPrimaria.href}>
                  {acaoPrimaria.rotulo}
                </BotaoEstelar>
                {!usuario && temLogin && (
                  <Link href="/cadastrar" className={botaoVitrineContorno}>
                    Criar conta
                  </Link>
                )}
              </div>
            </FechoVitrine>
          </section>
        </Revelar>
      </main>

      <footer className="border-t border-border/50">
        <div
          className={`${COLUNA} flex flex-col items-start justify-between gap-2 py-10 text-xs text-muted-foreground sm:flex-row sm:items-center`}
        >
          <span className="flex items-center gap-2">
            <MarcaFraus tamanho={18} />
            Fraus — trabalho de conclusão de curso.
          </span>
          <span>
            Os dados de demonstração são sintéticos e rotulados como tal.
          </span>
        </div>
      </footer>
    </div>
  );
}
