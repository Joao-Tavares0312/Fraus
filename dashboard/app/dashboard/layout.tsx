import { Suspense } from "react";
import { redirect } from "next/navigation";
import { AvisoApiFora } from "@/components/shell/AvisoApiFora";
import { NavegacaoLateral } from "@/components/shell/NavegacaoLateral";
import { SaudeProvider } from "@/components/shell/SaudeProvider";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ProvedorDaMentira } from "@/lib/mentira";
import { loginDisponivel, sessaoAtual } from "@/lib/sessao";

/**
 * O shell da ferramenta, agora atrás do portão de sessão.
 *
 * O portão é OPORTUNISTA aqui e REAL no servidor Python: este redirect decide
 * o que renderizar, mas quem nega dado a um papel sem privilégio é o
 * middleware da API (403 em rota administrativa). Um usuário com o proxy na
 * mão não vira administrador por pular esta tela.
 *
 * Sem login disponível (FRAUS_JWT_SEGREDO ausente na API), a dashboard abre
 * como sempre abriu — é o modo aberto local, o mesmo contrato da API sem
 * mestra. Nesse modo o papel é `dev`, coerente com a API que responde tudo.
 *
 * O papel também cai em `dev` quando a sessão fica INDETERMINADA (a API não
 * respondeu a tempo). Parece otimista e não é: nesse estado a API não está
 * respondendo NADA, então as telas de administração falham igual às outras e
 * o AvisoApiFora explica a causa. Esconder metade da navegação por cima disso
 * só acrescentaria um segundo mistério ao primeiro.
 */
export default async function DashboardLayout({
  children,
}: LayoutProps<"/dashboard">) {
  const sessao = await sessaoAtual();

  // SÓ EXPULSA COM VEREDITO. `ausente` é a API tendo olhado o token e recusado
  // (ou não haver token nenhum); `indeterminada` é a pergunta não ter voltado
  // a tempo -- e as duas viravam a mesma coisa aqui, com o `!usuario`.
  //
  // O efeito era brutal e silencioso: com a API publicada por túnel, uma
  // lentidão da rede mandava para a tela de entrar quem estava logado, com o
  // cookie válido na mão e nada na tela explicando o porquê.
  //
  // No indeterminado a dashboard ABRE. Isso não afrouxa nada, e o comentário
  // acima já dizia por quê: este portão é OPORTUNISTA, quem nega dado é o
  // middleware da API. Sem sessão confirmada as telas de dentro vão receber
  // 401 e desenhar seus próprios estados de erro, com o AvisoApiFora por cima
  // explicando -- que é informação, enquanto o redirect era um enigma.
  if (sessao.estado === "ausente" && (await loginDisponivel())) {
    redirect("/entrar");
  }

  const usuario = sessao.estado === "logada" ? sessao.usuario : null;
  const papel = usuario?.papel ?? "dev";

  return (
    <TooltipProvider>
      <SaudeProvider>
        {/* O easter egg da marca liga a mentira na NAVEGACAO e ela e exibida
            pelos INDICADORES, noutra sub-arvore -- o provedor precisa ficar
            acima das duas, e este e o ponto onde elas se encontram. Fora do
            painel o valor e sempre `false`, e nenhum indicador sabe mentir
            por conta propria. Ver lib/mentira.tsx. */}
        <ProvedorDaMentira>
          <SidebarProvider>
            {/*
              Atalho para quem navega por teclado: sem ele, chegar ao conteudo
              exige percorrer a navegacao lateral inteira a cada troca de
              pagina. Fica invisivel ate receber foco.
            */}
            <a
              href="#conteudo"
              className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-primary focus:px-3 focus:py-2 focus:text-sm focus:font-medium focus:text-primary-foreground"
            >
              Pular para o conteúdo
            </a>
            {/* A navegacao le `useSearchParams` para carregar o periodo entre
                as secoes, e isso exige limite de Suspense no App Router. */}
            <Suspense fallback={null}>
              <NavegacaoLateral papel={papel} usuario={usuario} />
            </Suspense>
            <SidebarInset id="conteudo" className="min-w-0">
              {/* Acima do conteudo, em TODA tela: sem a API todas quebram
                  igual, e a instrucao tem que estar onde o Joao ja esta. */}
              <AvisoApiFora />
              {children}
            </SidebarInset>
          </SidebarProvider>
        </ProvedorDaMentira>
      </SaudeProvider>
    </TooltipProvider>
  );
}
