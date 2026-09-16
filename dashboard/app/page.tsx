import Link from "next/link";
import { ArrowRight, Clock3, Drama, HeartPulse, LibraryBig, MessageSquareText, ShieldCheck, SmilePlus, Type } from "lucide-react";
import { PartituraExemplo } from "@/components/lp/PartituraExemplo";
import { Revelar } from "@/components/lp/Revelar";
import { botaoVitrine, botaoVitrineFantasma, botaoVitrineMiudo } from "@/components/lp/botoes";
import { MarcaFraus } from "@/components/shell/MarcaFraus";
import { loginDisponivel, usuarioDaSessao } from "@/lib/sessao";

const C = "mx-auto w-full max-w-[88rem] px-5 sm:px-8 lg:px-12";
const FATOS = [["07", "famílias de sinal"], ["39", "features no fusor"], ["03", "BERTimbau fine-tunados"], ["00", "LLMs em runtime"]] as const;
const SINAIS = [
  [MessageSquareText, "Texto", "Sentimento por mensagem e interlocutor.", "text-dito-texto"],
  [SmilePlus, "Emoji", "Polaridade e posição relativa na frase.", "text-dito-texto"],
  [Type, "Estilo", "Caixa alta, repetição, alongamento e pontuação.", "text-dito-texto"],
  [Clock3, "Tempo", "Espera, abandono, latência e escalação.", "text-medido-texto"],
  [HeartPulse, "Emoção", "Sete classes e desprezo derivado.", "text-medido-texto"],
  [LibraryBig, "Léxico", "SentiLex, negação e vocabulário curado.", "text-medido-texto"],
  [Drama, "Ironia", "Contradição entre tom aparente e contexto.", "text-medido-texto"],
] as const;
const HONESTIDADE = [
  ["01", "É estimativa, não pesquisa", "O NPS é inferido da conversa e nunca aparece como nota declarada pelo cliente."],
  ["02", "Ausência não vira zero", "Sem fala suficiente, o atendimento aparece como sem sinal. Não medir e medir insatisfação são respostas diferentes."],
  ["03", "Limitação não é rodapé", "O sinal de tempo usa dados sintéticos por falta de corpus público com timestamps. Isso permanece visível."],
] as const;

function Etiqueta({ children }: { children: React.ReactNode }) {
  return <p className="etiqueta-vitrine flex items-center gap-3 text-muted-foreground"><span aria-hidden className="h-px w-8 bg-primary" />{children}</p>;
}

function OrbitaFraus() {
  return <div aria-hidden className="orbita-fraus relative mx-auto aspect-square w-full max-w-[34rem]">
    <div className="orbita-fraus__eixo absolute inset-[12%] rounded-full border border-compasso" />
    <div className="orbita-fraus__eixo absolute inset-[25%] rounded-full border border-compasso" />
    <div className="absolute inset-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-medido shadow-[0_0_28px_var(--medido)]" />
    <div className="absolute left-[12%] top-[48%] size-2 rounded-full bg-dito shadow-[0_0_18px_var(--dito)]" />
    <div className="absolute right-[20%] top-[22%] size-1.5 rounded-full bg-primary shadow-[0_0_16px_var(--primary)]" />
    <div className="absolute left-[48%] top-[5%] font-mono text-[.6875rem] uppercase tracking-[.2em] text-muted-foreground">frs / 07</div>
    <div className="absolute bottom-[12%] right-[4%] text-right font-mono text-[.6875rem] uppercase leading-5 tracking-[.16em] text-muted-foreground">39 vetores<br />1 veredito</div>
    <div className="absolute left-1/2 top-1/2 w-36 -translate-x-1/2 translate-y-6 text-center"><p className="font-mono text-[.6875rem] uppercase tracking-[.2em] text-medido-texto">núcleo de leitura</p></div>
  </div>;
}

export default async function PaginaInicial() {
  const usuario = await usuarioDaSessao();
  const temLogin = await loginDisponivel();
  const acao = usuario ? { href: "/dashboard", rotulo: "Ir para a dashboard" } : temLogin ? { href: "/entrar", rotulo: "Entrar" } : { href: "/dashboard", rotulo: "Abrir a dashboard" };
  return <div className="overflow-x-clip">
    <header className="vidro-fino sticky top-0 z-50 border-x-0 border-t-0">
      <div aria-hidden className="progresso-leitura absolute inset-x-0 bottom-0 h-px bg-primary" />
      <div className={`${C} flex h-16 items-center justify-between`}><Link href="/" className="flex items-center gap-3" aria-label="Fraus — início"><MarcaFraus tamanho={30} /><strong className="text-sm">Fraus</strong></Link><nav aria-label="Navegação principal" className="flex items-center gap-2 sm:gap-4"><a href="#metodo" className="hidden text-sm text-muted-foreground hover:text-foreground md:block">Como funciona</a><a href="#honestidade" className="hidden text-sm text-muted-foreground hover:text-foreground md:block">Método</a>{!usuario && temLogin && <Link href="/cadastrar" className={botaoVitrineFantasma}>Criar conta</Link>}<Link href={acao.href} className={botaoVitrineMiudo}>{acao.rotulo}</Link></nav></div>
    </header>
    <main>
      <section className="relative border-b border-linha"><div className={`${C} grid min-h-[calc(100svh-4rem)] items-center gap-8 py-12 lg:grid-cols-[1.08fr_.92fr]`}>
        <div className="relative z-10"><div className="flex items-center justify-between gap-4"><Etiqueta>observatório de conversas</Etiqueta><span className="hidden font-mono text-[.6875rem] uppercase tracking-[.2em] text-muted-foreground sm:block">órbita 07 · pt-br</span></div><h1 className="display-vitrine mt-14 max-w-[11ch]">O que foi <span className="text-dito-texto">dito</span> não é tudo que foi <span className="text-medido-texto">sentido.</span></h1><div className="mt-12 grid max-w-3xl gap-8 border-t border-linha pt-7 sm:grid-cols-[1fr_auto] sm:items-end"><p className="max-w-xl text-lg leading-relaxed text-muted-foreground">O Fraus encontra a distância entre a frase educada e a experiência real — sem pesquisa e sem LLM em runtime.</p><Link href={acao.href} className={botaoVitrine}>Iniciar leitura <ArrowRight /></Link></div></div>
        <div className="orbita-fraus-cena"><OrbitaFraus /></div>
      </div><div className={`${C} pb-5 font-mono text-[.6875rem] uppercase tracking-[.18em] text-muted-foreground`}><span className="text-dito-texto">↑ fala observada</span><span className="mx-4 text-compasso">/</span><span className="text-medido-texto">↓ contexto medido</span></div></section>
      <section aria-label="Fatos do modelo" className="border-b border-linha bg-card/20"><div className={`${C} grid grid-cols-2 lg:grid-cols-4`}>{FATOS.map(([n, r], i) => <div key={r} className={`border-compasso py-8 sm:p-8 ${i % 2 ? "border-l pl-5" : ""} ${i > 1 ? "border-t lg:border-t-0" : ""}`}><p className="num text-5xl font-medium tracking-[-.05em] sm:text-6xl">{n}</p><p className="mt-3 text-sm text-muted-foreground">{r}</p></div>)}</div></section>
      <section id="metodo" className="scroll-mt-20 py-24 sm:py-36"><div className={C}>
        <Revelar className="mb-24 grid items-center gap-16 lg:grid-cols-[.8fr_1.2fr]"><div><Etiqueta>amostra 00-A</Etiqueta><h2 className="titulo-vitrine display-aurora mt-8">A cortesia mascara. O contexto denuncia.</h2><p className="mt-6 max-w-xl leading-relaxed text-muted-foreground">A mesma conversa, separada pela régua que governa o Fraus: acima, o material articulado; abaixo, a leitura produzida.</p></div><div className="lp-amostra relative"><div aria-hidden className="lp-amostra__moldura absolute -inset-5 -z-10 border border-compasso [clip-path:polygon(16px_0,100%_0,100%_calc(100%-16px),calc(100%-16px)_100%,0_100%,0_16px)]" /><PartituraExemplo /></div></Revelar>
        <Revelar className="grid gap-10 lg:grid-cols-2 lg:gap-20"><div><Etiqueta>01 · método</Etiqueta><h2 className="titulo-vitrine display-aurora mt-8 max-w-[10ch]">A fala é só a superfície.</h2></div><div className="self-end"><p className="text-xl leading-relaxed sm:text-2xl">Uma frase educada pode encerrar uma experiência ruim. O Fraus confronta o que foi articulado com o que aconteceu ao redor.</p><p className="mt-5 text-muted-foreground">Sete sinais produzem 39 features. O servidor combina as evidências e entrega score, nota e categoria — nunca o navegador.</p></div></Revelar>
        <div className="mt-20 grid sm:grid-cols-2 lg:grid-cols-4">{SINAIS.map(([Icone, nome, descricao, cor], i) => <Revelar key={nome} className="lp-sinal min-h-56 border-b border-r border-compasso p-7"><div className="flex justify-between"><span className="lp-sinal__icone"><Icone className={`size-5 ${cor}`} /></span><span className="num text-xs text-muted-foreground">0{i + 1}</span></div><h3 className="mt-16 text-xl font-medium">{nome}</h3><p className="mt-3 text-sm leading-relaxed text-muted-foreground">{descricao}</p></Revelar>)}<Revelar className="lp-sinal lp-sinal--nucleo flex min-h-56 flex-col justify-between border-b border-r border-compasso bg-primary p-7 text-primary-foreground"><ArrowRight /><div><p className="text-xl font-medium">O contexto vence a frase.</p><p className="mt-3 text-sm opacity-75">É no cruzamento dos sinais que o “obrigado” deixa de parecer satisfação.</p></div></Revelar></div>
      </div></section>
      <section id="honestidade" className="scroll-mt-20 border-y border-linha bg-card/15 py-24 sm:py-36"><div className={`${C} grid gap-12 lg:grid-cols-2 lg:gap-24`}><Revelar><Etiqueta>02 · honestidade</Etiqueta><h2 className="titulo-vitrine display-aurora mt-8 max-w-[11ch]">Um modelo que mostra os próprios limites.</h2><p className="mt-8 flex gap-3 text-sm text-muted-foreground"><ShieldCheck className="size-4 text-primary" />Sem número inventado. Sem depoimento fabricado.</p></Revelar><Revelar className="border-t border-linha">{HONESTIDADE.map(([n, titulo, texto]) => <article key={n} className="grid gap-4 border-b border-compasso py-8 sm:grid-cols-[3rem_1fr]"><span className="num text-primary">{n}</span><div><h3 className="text-xl font-medium">{titulo}</h3><p className="mt-3 leading-relaxed text-muted-foreground">{texto}</p></div></article>)}</Revelar></div></section>
      <section className="lp-fecho py-28 text-center sm:py-40"><Revelar className={C}><p className="etiqueta-vitrine text-primary">a conversa já tem a resposta</p><h2 className="display-vitrine mx-auto mt-8 max-w-[12ch]">Leia o que ficou nas entrelinhas.</h2><p className="mx-auto mt-8 max-w-xl text-lg text-muted-foreground">Transforme atendimentos em evidência operacional sem perguntar ao cliente o que ele já demonstrou.</p><Link href={acao.href} className={`${botaoVitrine} mt-10`}>{acao.rotulo}<ArrowRight /></Link></Revelar></section>
    </main>
    <footer className="border-t border-linha py-8"><div className={`${C} flex flex-col gap-3 text-sm text-muted-foreground sm:flex-row sm:justify-between`}><span>Fraus · análise de satisfação em português</span><span className="font-mono text-xs">modelos locais · sem LLM em runtime</span></div></footer>
  </div>;
}
