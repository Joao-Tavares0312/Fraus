import Link from "next/link";
import {
  ArrowRight,
  Clock3,
  Drama,
  HeartPulse,
  LibraryBig,
  MessageSquareText,
  SmilePlus,
  Type,
} from "lucide-react";
import { PartituraExemplo } from "@/components/lp/PartituraExemplo";
import { Revelar } from "@/components/lp/Revelar";
import {
  botaoVitrine,
  botaoVitrineContorno,
  botaoVitrineFantasma,
  botaoVitrineMiudo,
} from "@/components/lp/botoes";
import { MarcaFraus } from "@/components/shell/MarcaFraus";
import { loginDisponivel, usuarioDaSessao } from "@/lib/sessao";

/**
 * A página pública do produto (spec 2026-08-31, §2.8), na linguagem que a
 * pesquisa de 31/08 destilou dos sites de referência: base quase-mono com UM
 * acento, display grande com tracking negativo, zero sombra, bento grid,
 * microinterações curtas e reveals por rolagem (Stripe/Linear/Revolut — nunca
 * o espetáculo WebGL, que é a antítese de uma ferramenta de leitura).
 *
 * A regra que governa cada número: NENHUM é inventado. 35 features, 7 sinais
 * e 3 BERTimbau são fatos do código; o cartão do hero é ilustrativo e DIZ
 * isso. É a única tela com licença de display; a cor continua obedecendo:
 * âmbar = dito, azul = medido, dourado = ação.
 */

const SINAIS = [
  {
    Icone: MessageSquareText,
    nome: "Texto",
    descricao:
      "BERTimbau fine-tunado lê cada mensagem do cliente e devolve probabilidade por fala — é o que permite apontar quem puxou a nota.",
    span: "sm:col-span-2 lg:col-span-3",
  },
  {
    Icone: SmilePlus,
    nome: "Emoji",
    descricao:
      "Léxico de sentimento com a posição relativa do emoji na mensagem — o 🙂 do fim de frase não vale o do começo.",
    span: "sm:col-span-2 lg:col-span-3",
  },
  {
    Icone: Clock3,
    nome: "Tempo",
    descricao: "Latência, escalação e abandono como features aprendidas.",
    span: "lg:col-span-2",
  },
  {
    Icone: HeartPulse,
    nome: "Emoção",
    descricao: "Sete classes, com desprezo derivado da díade raiva + nojo.",
    span: "lg:col-span-2",
  },
  {
    Icone: LibraryBig,
    nome: "Léxico",
    descricao: "SentiLex-PT02 com escopo de negação, mais o léxico curado.",
    span: "lg:col-span-2",
  },
  {
    Icone: Drama,
    nome: "Ironia",
    descricao:
      "“Ótimo atendimento” nem sempre elogia. Uma cabeça binária só para virar a leitura dos outros sinais.",
    span: "sm:col-span-2 lg:col-span-3",
  },
  {
    Icone: Type,
    nome: "Estilo",
    descricao:
      "CAIXA ALTA, pontuação!!!, alongamennnto e palavrão — a forma de escrever carrega o afeto que a palavra esconde.",
    span: "sm:col-span-2 lg:col-span-3",
  },
] as const;

const FATOS = [
  { numero: "35", rotulo: "features no fusor" },
  { numero: "7", rotulo: "famílias de sinal" },
  { numero: "3", rotulo: "BERTimbau fine-tunados" },
  { numero: "0", rotulo: "LLMs em runtime" },
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
      {/* Header fixo em vidro — o backdrop-blur discreto que a lição do menu
          do Corn Revolutionized autoriza num produto. */}
      <header className="vidro-fino sticky top-0 z-40 border-x-0 border-t-0">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-3">
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
              <Link
                href="/cadastrar"
                className={botaoVitrineFantasma}
              >
                Criar conta
              </Link>
            )}
            <Link
              href={acaoPrimaria.href}
              className={botaoVitrineMiudo}
            >
              {acaoPrimaria.rotulo}
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl px-6">
        {/* ============================== HERO ============================== */}
        <section className="grid items-center gap-12 py-20 lg:grid-cols-[1.1fr_1fr] lg:py-28">
          <Revelar>
            <p className="mb-5 inline-block rounded-full border border-border/60 px-3 py-1 font-mono text-xs uppercase tracking-widest text-muted-foreground">
              satisfação inferida · sem pesquisa
            </p>
            <h1 className="text-balance text-[clamp(2.75rem,6vw,4.75rem)] font-medium leading-[1.04] tracking-[-0.02em]">
              O cliente escreve{" "}
              <span className="text-dito-texto">“ok, obrigado&nbsp;🙂”</span>
              <br className="hidden sm:block" /> e sai insatisfeito.
            </h1>
            <p className="mt-6 max-w-xl text-pretty text-lg leading-relaxed text-muted-foreground">
              A nota declarada mente. O Fraus lê o atendimento inteiro — o que
              foi <span className="text-dito-texto">dito</span> e o que pôde
              ser <span className="text-medido-texto">medido</span> — e estima
              a satisfação sem perguntar nada.
            </p>
            <div className="mt-9 flex flex-wrap items-center gap-3">
              <Link
                href={acaoPrimaria.href}
                className={botaoVitrine}
              >
                {acaoPrimaria.rotulo}
                <ArrowRight aria-hidden />
              </Link>
              {!usuario && temLogin && (
                <Link
                  href="/cadastrar"
                  className={botaoVitrineContorno}
                >
                  Criar conta
                </Link>
              )}
            </div>
          </Revelar>
          <Revelar className="justify-self-center lg:justify-self-end">
            <PartituraExemplo />
          </Revelar>
        </section>

        {/* ========================= FATOS REAIS ========================= */}
        <Revelar>
          <section
            aria-label="Números do sistema"
            className="grid grid-cols-2 gap-px overflow-hidden rounded-md border border-border/60 bg-border/60 lg:grid-cols-4"
          >
            {FATOS.map(({ numero, rotulo }) => (
              <div key={rotulo} className="bg-background/80 px-6 py-6">
                <div className="num text-4xl font-semibold tracking-tight">
                  {numero}
                </div>
                <div className="mt-1 text-sm text-muted-foreground">{rotulo}</div>
              </div>
            ))}
          </section>
          <p className="mt-2 text-right font-mono text-[11px] text-muted-foreground">
            fatos do código — fraus.fusor.NOMES_FEATURES
          </p>
        </Revelar>

        {/* ========================= SETE SINAIS ========================= */}
        <section id="como-funciona" className="scroll-mt-24 py-24">
          <Revelar className="max-w-2xl">
            <p className="mb-3 font-mono text-xs uppercase tracking-widest text-primary">
              como funciona
            </p>
            <h2 className="text-4xl font-medium tracking-[-0.015em]">
              Sete sinais, um veredito
            </h2>
            <p className="mt-4 text-muted-foreground">
              Cada família lê a conversa por um ângulo próprio. Um fusor leve
              combina tudo num score de 0 a 100 — a inferência roda local, em
              CPU, e nenhuma mensagem sai da máquina para ser pontuada.
            </p>
          </Revelar>

          <div className="mt-12 grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
            {SINAIS.map(({ Icone, nome, descricao, span }) => (
              <Revelar key={nome} className={span}>
                <div className="vidro-fino group h-full p-5 transition-transform duration-150 ease-fluid hover:-translate-y-0.5">
                  <Icone
                    aria-hidden
                    className="size-5 text-muted-foreground transition-colors duration-150 ease-fluid group-hover:text-primary"
                  />
                  <h3 className="mt-3 text-base font-semibold tracking-tight">
                    {nome}
                  </h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
                    {descricao}
                  </p>
                </div>
              </Revelar>
            ))}
          </div>

          {/* O fluxo do fusor — a régua de novo, agora como pipeline. */}
          <Revelar>
            <div className="vidro mt-3 flex flex-wrap items-center justify-center gap-x-3 gap-y-2 px-6 py-5 font-mono text-xs text-muted-foreground sm:text-sm">
              <span className="text-dito-texto">7 sinais</span>
              <ArrowRight aria-hidden className="size-3.5" />
              <span>35 features</span>
              <ArrowRight aria-hidden className="size-3.5" />
              <span>regressão logística</span>
              <ArrowRight aria-hidden className="size-3.5" />
              <span className="text-medido-texto">score 0–100</span>
              <ArrowRight aria-hidden className="size-3.5" />
              <span className="text-medido-texto">
                NPS estimado<span className="align-super text-[9px]">*</span>
              </span>
            </div>
            <p className="mt-2 text-right font-mono text-[11px] text-muted-foreground">
              * estimado a partir do texto — e rotulado assim em toda tela
            </p>
          </Revelar>
        </section>

        {/* ==================== A REGRA MESTRA (dito/medido) ==================== */}
        <Revelar>
          <section
            aria-label="A regra mestra da interface"
            className="overflow-hidden rounded-md border border-border/60"
          >
            <div className="grid lg:grid-cols-2">
              <div className="border-b border-linha p-8 lg:border-b-0 lg:border-r lg:p-10">
                <p className="font-mono text-xs uppercase tracking-widest text-dito-texto">
                  acima da linha
                </p>
                <h3 className="mt-3 text-2xl font-medium tracking-tight">
                  O que foi <span className="text-dito-texto">dito</span>
                </h3>
                <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                  Fala, texto, emoji — o que o cliente articulou, em âmbar. É o
                  material bruto, educado por natureza: quase ninguém xinga o
                  robô antes de desistir.
                </p>
              </div>
              <div className="p-8 lg:p-10">
                <p className="font-mono text-xs uppercase tracking-widest text-medido-texto">
                  abaixo da linha
                </p>
                <h3 className="mt-3 text-2xl font-medium tracking-tight">
                  O que foi <span className="text-medido-texto">medido</span>
                </h3>
                <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                  Score, probabilidade, latência, tendência — em azul. A
                  distância entre as duas vozes é a informação que o produto
                  vende, e a interface inteira é desenhada para mostrá-la.
                </p>
              </div>
            </div>
          </section>
        </Revelar>

        {/* ========================= ATRIBUIÇÃO ========================= */}
        <section className="grid items-center gap-10 py-24 lg:grid-cols-2">
          <Revelar>
            <p className="mb-3 font-mono text-xs uppercase tracking-widest text-primary">
              atribuição
            </p>
            <h2 className="text-4xl font-medium tracking-[-0.015em]">
              O número aponta as falas que o puxaram
            </h2>
            <p className="mt-4 leading-relaxed text-muted-foreground">
              O sinal de texto pontua <em>por mensagem</em>: o Fraus mostra
              quais falas derrubaram (ou salvaram) a nota de cada atendimento,
              em vez de devolver um score opaco para a operação discutir às
              cegas. É o que um número sozinho não conta — e o que um produto
              vizinho não copia com honestidade.
            </p>
          </Revelar>
          <Revelar>
            <ul className="flex flex-col gap-2">
              {[
                { fala: "“passei 40 minutos esperando pra isso”", peso: "▼ puxou para baixo" },
                { fala: "“ok, obrigado 🙂”", peso: "▼ ironia provável" },
                { fala: "“a atendente Maria foi ótima”", peso: "▲ segurou a nota" },
              ].map(({ fala, peso }) => (
                <li
                  key={fala}
                  className="vidro-fino flex items-center justify-between gap-4 px-4 py-3"
                >
                  <span className="text-sm text-dito-texto">{fala}</span>
                  <span className="shrink-0 font-mono text-xs text-medido-texto">
                    {peso}
                  </span>
                </li>
              ))}
            </ul>
            <p className="mt-2 text-right font-mono text-[11px] text-muted-foreground">
              exemplo ilustrativo
            </p>
          </Revelar>
        </section>

        {/* ========================= HONESTIDADE ========================= */}
        <section id="honestidade" className="scroll-mt-24 pb-24">
          <Revelar className="max-w-2xl">
            <p className="mb-3 font-mono text-xs uppercase tracking-widest text-primary">
              honestidade metodológica
            </p>
            <h2 className="text-4xl font-medium tracking-[-0.015em]">
              O que é medido, o que é estimado
            </h2>
            <p className="mt-4 text-muted-foreground">
              A ferramenta leva o nome do daemon romano do engano por um
              motivo: o texto engana, e medir isso exige dizer com precisão o
              que é fato e o que é inferência.
            </p>
          </Revelar>
          <div className="mt-12 grid gap-3 lg:grid-cols-3">
            {HONESTIDADES.map(({ n, titulo, texto }) => (
              <Revelar key={n}>
                <div className="vidro-fino h-full p-6">
                  <span className="font-mono text-sm text-primary">{n}</span>
                  <h3 className="mt-3 text-base font-semibold tracking-tight">
                    {titulo}
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                    {texto}
                  </p>
                </div>
              </Revelar>
            ))}
          </div>
        </section>

        {/* ========================= CTA FINAL ========================= */}
        <Revelar>
          <section className="vidro mb-24 flex flex-col items-center gap-6 px-8 py-16 text-center">
            <h2 className="max-w-2xl text-balance text-[clamp(2rem,4vw,3rem)] font-medium leading-tight tracking-[-0.02em]">
              Pronto para ler o que o cliente{" "}
              <span className="text-dito-texto">não disse</span>?
            </h2>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <Link
                href={acaoPrimaria.href}
                className={botaoVitrine}
              >
                {acaoPrimaria.rotulo}
                <ArrowRight aria-hidden />
              </Link>
              {!usuario && temLogin && (
                <Link
                  href="/cadastrar"
                  className={botaoVitrineContorno}
                >
                  Criar conta
                </Link>
              )}
            </div>
          </section>
        </Revelar>
      </main>

      <footer className="border-t border-border/50">
        <div className="mx-auto flex w-full max-w-6xl flex-col items-start justify-between gap-2 px-6 py-8 text-xs text-muted-foreground sm:flex-row sm:items-center">
          <span className="flex items-center gap-2">
            <MarcaFraus tamanho={18} />
            Fraus — trabalho de conclusão de curso.
          </span>
          <span>Os dados de demonstração são sintéticos e rotulados como tal.</span>
        </div>
      </footer>
    </div>
  );
}
