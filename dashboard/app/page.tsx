import Link from "next/link";
import {
  Activity,
  Clock3,
  Drama,
  HeartPulse,
  LibraryBig,
  MessageSquareText,
  SmilePlus,
  Type,
} from "lucide-react";
import { MarcaFraus } from "@/components/shell/MarcaFraus";
import { buttonVariants } from "@/components/ui/button";
import { loginDisponivel, usuarioDaSessao } from "@/lib/sessao";

/**
 * A página pública do produto (spec 2026-08-31, §2.8): a tese, os sete
 * sinais, a honestidade metodológica e a entrada.
 *
 * A regra que governa cada número desta tela: NENHUM é inventado. 35 features
 * e sete sinais são fatos do código (`fraus.fusor.NOMES_FEATURES`); não há
 * "98% de acurácia", contador de clientes nem depoimento — numa ferramenta
 * batizada com o nome do daemon do engano, número fabricado na vitrine seria
 * a pior falha possível.
 *
 * É a única tela com licença de display: o modo Operate governa a ferramenta,
 * não a vitrine. Ainda assim a cor obedece: âmbar = dito, azul = medido,
 * dourado = ação — os mesmos tokens, os mesmos significados.
 */

const SINAIS = [
  {
    Icone: MessageSquareText,
    nome: "Texto",
    descricao: "BERTimbau fine-tunado lê cada mensagem do cliente.",
  },
  {
    Icone: SmilePlus,
    nome: "Emoji",
    descricao: "Léxico de sentimento com a posição do emoji na fala.",
  },
  {
    Icone: Clock3,
    nome: "Tempo",
    descricao: "Latência, escalação e abandono como features aprendidas.",
  },
  {
    Icone: HeartPulse,
    nome: "Emoção",
    descricao: "Sete classes, com desprezo derivado da díade raiva + nojo.",
  },
  {
    Icone: LibraryBig,
    nome: "Léxico",
    descricao: "SentiLex-PT02 com escopo de negação, mais o léxico curado.",
  },
  {
    Icone: Drama,
    nome: "Ironia",
    descricao: "“Ótimo atendimento” nem sempre elogia — uma cabeça só para isso.",
  },
  {
    Icone: Type,
    nome: "Estilo",
    descricao: "Caixa alta, pontuação, alongamento e palavrão carregam afeto.",
  },
] as const;

const HONESTIDADES = [
  {
    titulo: "O NPS é estimado, não perguntado",
    texto:
      "Ninguém responde pesquisa aqui: a categoria vem do texto, e toda tela que a exibe carrega a etiqueta de estimativa. Apresentar como NPS declarado seria falso.",
  },
  {
    titulo: "Ausência de dado não é insatisfação",
    texto:
      "Conversa em que o cliente não falou aparece como “sem sinal” — nunca como zero, em célula, gráfico ou média. Não medir e medir zero são respostas diferentes.",
  },
  {
    titulo: "O sinal de tempo é treinado em dados sintéticos",
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
    <div className="mx-auto flex min-h-svh w-full max-w-5xl flex-col px-6">
      <header className="flex items-center justify-between py-6">
        <div className="flex items-center gap-3">
          <MarcaFraus tamanho={32} />
          <div className="flex flex-col">
            <span className="text-sm font-semibold tracking-tight">Fraus</span>
            <span className="text-xs text-muted-foreground">
              satisfação inferida
            </span>
          </div>
        </div>
        <nav className="flex items-center gap-2">
          {!usuario && temLogin && (
            <Link
              href="/cadastrar"
              className={buttonVariants({ variant: "ghost", size: "sm" })}
            >
              Criar conta
            </Link>
          )}
          <Link href={acaoPrimaria.href} className={buttonVariants({ size: "sm" })}>
            {acaoPrimaria.rotulo}
          </Link>
        </nav>
      </header>

      <main className="flex flex-1 flex-col gap-20 pb-24 pt-16">
        {/* A tese */}
        <section className="max-w-3xl">
          <p className="mb-4 text-sm font-medium uppercase tracking-widest text-muted-foreground">
            Satisfação em atendimentos por chatbot
          </p>
          <h1 className="text-balance text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
            O cliente escreve{" "}
            <span className="text-dito-texto">&ldquo;ok, obrigado 🙂&rdquo;</span>{" "}
            e sai insatisfeito.
          </h1>
          <p className="mt-6 max-w-2xl text-pretty text-lg text-muted-foreground">
            A nota declarada mente. O Fraus lê o atendimento inteiro — o que
            foi <span className="text-dito-texto">dito</span> e o que pôde ser{" "}
            <span className="text-medido-texto">medido</span> — e estima a
            satisfação sem perguntar nada ao cliente.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link href={acaoPrimaria.href} className={buttonVariants({ size: "lg" })}>
              {acaoPrimaria.rotulo}
            </Link>
            {!usuario && temLogin && (
              <Link
                href="/cadastrar"
                className={buttonVariants({ variant: "outline", size: "lg" })}
              >
                Criar conta
              </Link>
            )}
          </div>
        </section>

        {/* Como funciona */}
        <section aria-labelledby="como-funciona">
          <h2
            id="como-funciona"
            className="text-2xl font-semibold tracking-tight"
          >
            Sete sinais, um veredito
          </h2>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Cada família de sinal lê a conversa por um ângulo próprio. Um fusor
            leve combina as 35 features num score de 0 a 100, que vira nota e
            categoria de NPS —{" "}
            <strong className="font-medium text-foreground">
              sem nenhum LLM em runtime
            </strong>
            : a inferência roda local, em CPU, e nenhuma mensagem sai da
            máquina para ser pontuada.
          </p>
          <ul className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {SINAIS.map(({ Icone, nome, descricao }) => (
              <li key={nome} className="vidro-fino p-4">
                <div className="flex items-center gap-2.5">
                  <Icone aria-hidden className="size-4 text-muted-foreground" />
                  <h3 className="text-sm font-semibold">{nome}</h3>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{descricao}</p>
              </li>
            ))}
            <li className="vidro-fino border-primary/30 p-4">
              <div className="flex items-center gap-2.5">
                <Activity aria-hidden className="size-4 text-primary" />
                <h3 className="text-sm font-semibold">O fusor</h3>
              </div>
              <p className="mt-2 text-sm text-muted-foreground">
                Regressão logística sobre as 35 features — pesos aprendidos e
                inspecionáveis na tela Modelo, não uma caixa-preta.
              </p>
            </li>
          </ul>
        </section>

        {/* Atribuição */}
        <section aria-labelledby="atribuicao" className="max-w-3xl">
          <h2 id="atribuicao" className="text-2xl font-semibold tracking-tight">
            O número aponta as falas que o puxaram
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            O sinal de texto pontua <em>por mensagem</em>, então o Fraus mostra
            quais falas derrubaram (ou salvaram) a nota de cada atendimento —
            em vez de devolver um score opaco para a operação discutir às
            cegas.
          </p>
        </section>

        {/* Honestidade metodológica */}
        <section aria-labelledby="honestidade">
          <h2 id="honestidade" className="text-2xl font-semibold tracking-tight">
            O que é medido, o que é estimado
          </h2>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            A ferramenta leva o nome do daemon romano do engano por um motivo:
            o texto engana, e medir isso exige dizer com precisão o que é fato
            e o que é inferência.
          </p>
          <ul className="mt-8 grid gap-4 lg:grid-cols-3">
            {HONESTIDADES.map(({ titulo, texto }) => (
              <li key={titulo} className="vidro-fino p-4">
                <h3 className="text-sm font-semibold">{titulo}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{texto}</p>
              </li>
            ))}
          </ul>
        </section>
      </main>

      <footer className="border-t border-border/50 py-6 text-xs text-muted-foreground">
        Fraus — trabalho de conclusão de curso. Os dados de demonstração são
        sintéticos e estão rotulados como tal.
      </footer>
    </div>
  );
}
