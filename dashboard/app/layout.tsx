import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import localFont from "next/font/local";
import "./globals.css";
import { Atelier } from "@/components/shell/Atelier";
import { Movimento } from "@/components/shell/Movimento";
import { SCRIPT_ANTI_PISCADA } from "@/lib/tema";

/**
 * Etapa 1 do Pauta evoluído (spec 2026-08-31): Inter no lugar da sans de
 * sistema, JetBrains Mono nos dados. `next/font` baixa os arquivos NO BUILD e
 * os serve do próprio deploy — nenhuma chamada ao Google em runtime, que é a
 * regra da casa. As variáveis entram no `<html>` e o globals.css as põe na
 * frente da pilha com fallback de sistema.
 */
const inter = Inter({
  subsets: ["latin", "latin-ext"],
  variable: "--fonte-inter",
  display: "swap",
});
const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--fonte-jetbrains",
  display: "swap",
});

/**
 * A DISPLAY DA VITRINE, e só dela — DESIGN.md §4. Mona Sans variável, a mesma
 * da landonorris.com, escolhida em 04/09/2026 pelo diagnóstico da nota de
 * reformulação: as seis referências usam grotescas de autoria, e a Inter
 * carrega a memória de "aplicação moderna bem-feita".
 *
 * O corte usado é `MonaSansVF[opsz,wght].woff2` (eixos `opsz` e `wght`), não
 * o corte com `wdth` do mesmo release: nenhuma regra desta tarefa aciona o
 * eixo de largura (`.display-vitrine` e `.titulo-vitrine` só definem
 * `font-family`, e a primeira trava `font-weight: 500`), então o corte com
 * `wdth` seria 2,2x o tamanho por um eixo morto. O `opsz`, ao contrário, serve
 * ao caso: é uma display em corpo grande, e o ajuste óptico automático é
 * ganho de graça. O nome do arquivo não foi alterado — ele anuncia os eixos
 * que de fato tem.
 *
 * `next/font/local` a partir do arquivo VERSIONADO no repo, e não
 * `next/font/google`: o binário está em app/fontes/, servido do próprio
 * deploy. Nenhuma chamada de rede, nem no build nem em runtime.
 */
const mona = localFont({
  src: "./fontes/MonaSansVF[opsz,wght].woff2",
  variable: "--fonte-mona",
  display: "swap",
  weight: "200 900",
});

const DESCRICAO =
  "Painel de satisfação inferida a partir do texto, dos emojis e do tempo de resposta dos atendimentos.";

export const metadata: Metadata = {
  title: "Fraus — satisfação em atendimentos por chatbot",
  description: DESCRICAO,
  // `openGraph` existe para quando o link for compartilhado na apresentacao ou
  // no repositorio: sem ele, o preview sai com o titulo cru e sem imagem.
  openGraph: {
    title: "Fraus — satisfação em atendimentos por chatbot",
    description: DESCRICAO,
    type: "website",
    locale: "pt_BR",
    images: [{ url: "/fraus-logo.png", width: 640, height: 640, alt: "Fraus" }],
  },
};

/**
 * Casca COMUM: html, tema e ateliê. O shell da ferramenta (sidebar, saúde,
 * provedores) desceu para `app/dashboard/layout.tsx` em 31/08/2026, quando a
 * raiz virou a página pública do produto — a LP não tem navegação lateral, e
 * um visitante sem sessão não precisa carregar os provedores da dashboard.
 *
 * `className="dark"` no `<html>` e fixo, e continua fixo: os DOIS temas do
 * Fraus sao escuros, entao o `dark` do chassi vale para os dois e nao ha
 * modo claro a alternar.
 *
 * O que MUDOU, e este comentario dizia o contrario ate 24/08/2026: existe
 * alternador. Ele nao troca `dark` por `light` -- poe (ou tira) a classe
 * `.tema-chuva` no mesmo `<html>`, e o tema sobrepoe so o chassi. O argumento
 * antigo ("um contrato de contraste verificado por calculo vale para uma
 * paleta") nao caiu: `scripts/contraste.mjs` passou a ser CIENTE DE TEMA e
 * roda a matriz inteira por tema, entao as duas paletas sao verificadas, nao
 * uma. Ver DESIGN.md, seccao 8.
 */
export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // `suppressHydrationWarning` no `<html>`: o script abaixo pode adicionar a
    // classe do tema antes da hidratacao, e o React acusaria a diferenca entre
    // o HTML que o servidor mandou e o que encontrou no DOM. A divergencia e
    // intencional e e o ponto do script.
    <html
      lang="pt-BR"
      className={`dark ${inter.variable} ${jetbrains.variable} ${mona.variable}`}
      suppressHydrationWarning
    >
      <head>
        {/* ANTES DE TUDO. Ver SCRIPT_ANTI_PISCADA em lib/tema.ts: sem isto,
            quem escolheu "chuva de neon" ve a tela pintar em grafite e trocar
            depois da hidratacao, a cada navegacao. */}
        <script
          dangerouslySetInnerHTML={{ __html: SCRIPT_ANTI_PISCADA }}
        />
      </head>
      <body className="min-h-svh antialiased">
        <Atelier />
        <Movimento>{children}</Movimento>
      </body>
    </html>
  );
}
