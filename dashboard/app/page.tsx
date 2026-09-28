import Link from "next/link";
import { ArrowDown, ArrowRight, ShieldCheck } from "lucide-react";
import { CampoDeParticulas } from "@/components/lp/CampoDeParticulas";
import { CenaScroll3DPorta } from "@/components/lp/CenaScroll3DPorta";
import { Esteira } from "@/components/lp/Esteira";
import { PartituraExemplo } from "@/components/lp/PartituraExemplo";
import { OrbitaHero } from "@/components/lp/OrbitaHero";
import { Revelar } from "@/components/lp/Revelar";
import { botaoVitrine, botaoVitrineContorno, botaoVitrineMiudo } from "@/components/lp/botoes";
import { MarcaFraus } from "@/components/shell/MarcaFraus";

const C = "mx-auto w-full max-w-[88rem] px-5 sm:px-8 lg:px-12";
const FATOS = [
  ["07", "famílias de sinal", "camadas independentes"],
  ["39", "features no fusor", "combinadas no score"],
  ["03", "BERTimbau", "fine-tunados em português"],
  ["00", "LLMs", "durante a inferência"],
] as const;
const HONESTIDADE = [
  ["01", "É estimativa, não pesquisa", "O NPS é inferido da conversa e nunca aparece como nota declarada pelo cliente."],
  ["02", "Ausência não vira zero", "Sem fala suficiente, o atendimento aparece como sem sinal. Não medir e medir insatisfação são respostas diferentes."],
  ["03", "Limitação não é rodapé", "O sinal de tempo usa dados sintéticos por falta de corpus público com timestamps. Isso permanece visível."],
] as const;

function Etiqueta({ children }: { children: React.ReactNode }) {
  return <p className="etiqueta-vitrine flex items-center gap-3 text-muted-foreground"><span aria-hidden className="h-px w-8 bg-primary" />{children}</p>;
}

export default function PaginaInicial() {
  return <div className="overflow-x-clip">
    <div aria-hidden className="progresso-leitura fixed inset-x-0 top-0 z-[70] h-px bg-primary shadow-[0_0_12px_var(--primary)]" />
    <header className="absolute inset-x-0 top-0 z-50"><div className={`${C} flex h-20 items-center justify-between`}>
      <Link href="/" className="group flex items-center gap-3" aria-label="Fraus — início"><MarcaFraus tamanho={28} /><strong className="text-sm font-medium tracking-[.08em]">FRAUS</strong><span className="hidden items-center gap-2 border-l border-compasso pl-3 font-mono text-[.6875rem] uppercase tracking-[.16em] text-muted-foreground lg:flex"><i className="size-1 rounded-full bg-primary shadow-[0_0_8px_var(--primary)]" />análise em operação</span></Link>
      <nav aria-label="Navegação principal" className="flex items-center gap-5 lg:gap-8"><a href="#leitura" className="nav-link hidden md:block">Leitura</a><a href="#sistema" className="nav-link hidden md:block">Sistema</a><a href="#metodo" className="nav-link hidden md:block">Método</a><Link href="/cadastrar" className="nav-link hidden sm:block">Cadastro</Link><Link href="/entrar" className={botaoVitrineMiudo}>Acessar <ArrowRight /></Link></nav>
    </div></header>

    <main>
      <section className="hero-espacial relative isolate min-h-svh overflow-hidden border-b border-linha"><CampoDeParticulas /><div className="hero-espacial__horizonte absolute inset-x-0 bottom-0 -z-10 h-1/2" /><div className={`${C} grid min-h-svh items-center gap-4 pb-20 pt-28 lg:grid-cols-[1.02fr_.98fr]`}>
        <div className="relative z-10"><div className="flex flex-wrap items-center gap-x-4 gap-y-2"><Etiqueta>observatório de conversas</Etiqueta><span className="font-mono text-[.6875rem] uppercase tracking-[.2em] text-muted-foreground">pt-br / órbita 07</span></div><h1 className="display-vitrine mt-12 max-w-[10ch]">O que foi <span className="text-dito-texto">dito</span> não é tudo que foi <span className="text-medido-texto">sentido.</span></h1><p className="mt-8 max-w-xl text-lg leading-relaxed text-muted-foreground sm:text-xl">O Fraus lê a conversa inteira — palavras, pausas, emoção e contradições — para revelar a experiência que uma resposta educada pode esconder.</p><div className="mt-9 flex flex-col items-stretch gap-4 sm:flex-row sm:flex-wrap sm:items-center"><Link href="/entrar" className={`${botaoVitrine} w-full sm:w-auto`}>Iniciar leitura <ArrowRight /></Link><a href="#leitura" className={`${botaoVitrineContorno} w-full sm:w-auto`}>Ver uma análise <ArrowDown /></a></div><div className="mt-10 grid gap-2 font-mono text-[.6875rem] uppercase tracking-[.14em] text-muted-foreground sm:flex sm:flex-wrap sm:gap-x-6"><span>modelos locais</span><span>sem LLM em runtime</span><span>resultado explicável</span></div></div>
        <OrbitaHero />
      </div><div className={`${C} absolute inset-x-0 bottom-5 flex justify-between font-mono text-[.6875rem] uppercase tracking-[.18em] text-muted-foreground`}><span className="text-dito-texto">↑ fala observada</span><span className="hidden sm:block">role para atravessar a leitura</span><span className="text-medido-texto">↓ contexto medido</span></div></section>

      <Esteira />
      <section aria-label="Fatos do modelo" className="border-b border-linha bg-card/20"><div className={`${C} grid grid-cols-2 lg:grid-cols-4`}>{FATOS.map(([n, rotulo, detalhe], i) => <div key={rotulo} className={`border-compasso py-8 sm:p-8 ${i % 2 ? "border-l pl-5" : ""} ${i > 1 ? "border-t lg:border-t-0" : ""}`}><p className="num text-5xl font-medium tracking-[-.05em] sm:text-6xl">{n}</p><p className="mt-3 text-sm font-medium">{rotulo}</p><p className="mt-1 text-xs text-muted-foreground">{detalhe}</p></div>)}</div></section>

      <section id="leitura" className="scroll-mt-20 py-24 sm:py-36"><div className={C}><Revelar className="grid items-end gap-8 border-b border-linha pb-12 lg:grid-cols-[.8fr_1.2fr]"><div><Etiqueta>amostra 00-A</Etiqueta><h2 className="titulo-vitrine display-aurora mt-8 max-w-[11ch]">A cortesia mascara. O contexto denuncia.</h2></div><p className="max-w-2xl text-lg leading-relaxed text-muted-foreground lg:justify-self-end">A mesma conversa, separada pela régua que governa o Fraus: acima, o material articulado; abaixo, a leitura produzida.</p></Revelar><Revelar className="lp-amostra relative mt-14 flex justify-center"><PartituraExemplo /></Revelar></div></section>

      <div id="sistema" className="scroll-mt-0"><CenaScroll3DPorta /></div>

      <section id="metodo" className="scroll-mt-20 py-24 sm:py-36"><div className={`${C} grid gap-12 lg:grid-cols-2 lg:gap-24`}><Revelar><Etiqueta>04 · honestidade</Etiqueta><h2 className="titulo-vitrine display-aurora mt-8 max-w-[11ch]">Um modelo que mostra os próprios limites.</h2><p className="mt-8 flex gap-3 text-sm text-muted-foreground"><ShieldCheck className="size-4 text-primary" />Sem número inventado. Sem depoimento fabricado.</p></Revelar><Revelar className="border-t border-linha">{HONESTIDADE.map(([n, titulo, texto]) => <article key={n} className="grid gap-4 border-b border-compasso py-8 sm:grid-cols-[3rem_1fr]"><span className="num text-primary">{n}</span><div><h3 className="text-xl font-medium">{titulo}</h3><p className="mt-3 leading-relaxed text-muted-foreground">{texto}</p></div></article>)}</Revelar></div></section>

      <section className="lp-fecho border-t border-linha py-28 sm:py-40"><Revelar className={`${C} text-center`}><p className="etiqueta-vitrine text-primary">a conversa já tem a resposta</p><h2 className="display-vitrine mx-auto mt-8 max-w-[12ch]">Leia o que ficou nas entrelinhas.</h2><p className="mx-auto mt-8 max-w-xl text-lg leading-relaxed text-muted-foreground">Transforme atendimentos em evidência operacional sem perguntar ao cliente o que ele já demonstrou.</p><div className="mt-10 flex flex-wrap justify-center gap-4"><Link href="/entrar" className={botaoVitrine}>Entrar <ArrowRight /></Link><Link href="/cadastrar" className={botaoVitrineContorno}>Criar acesso</Link></div></Revelar></section>
    </main>
    <footer className="border-t border-linha py-8"><div className={`${C} flex flex-col gap-3 text-sm text-muted-foreground sm:flex-row sm:justify-between`}><span>Fraus · análise de satisfação em português</span><span className="font-mono text-xs">modelos locais · sem LLM em runtime</span></div></footer>
  </div>;
}
