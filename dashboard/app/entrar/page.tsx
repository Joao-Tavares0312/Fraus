import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { FormularioAuth } from "@/components/auth/FormularioAuth";
import { MolduraDeConta } from "@/components/auth/MolduraDeConta";
import { estadoAutenticacao, usuarioDaSessao } from "@/lib/sessao";
import { destinoAuth, tokenDeConvite } from "@/lib/destino-auth";

export const metadata: Metadata = { title: "Entrar — Fraus" };

export default async function PaginaEntrar({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const convite = tokenDeConvite((await searchParams).convite);
  // Quem já está logado não tem o que fazer aqui.
  if (await usuarioDaSessao()) redirect(destinoAuth(convite));

  const autenticacao = await estadoAutenticacao();
  if (autenticacao.estado === "indisponivel") {
    return (
      <MolduraDeConta titulo="Acesso indisponível">
        <div className="conta-estado">
          <p role="alert">Não foi possível consultar o serviço de autenticação. Tente novamente.</p>
          <Link className="conta-acao" href={convite ? `/entrar?convite=${convite}` : "/entrar"} prefetch={false}>
            Tentar novamente
          </Link>
        </div>
      </MolduraDeConta>
    );
  }

  if (autenticacao.estado === "desativado") {
    return (
      <MolduraDeConta titulo="Login não configurado">
        <div className="conta-estado">
          <p>O login está desativado nesta instalação. A dashboard continua disponível em modo aberto.</p>
          {convite && <p>O convite de equipe exige uma sessão de usuário e não pode ser aceito em modo aberto.</p>}
          <Link href="/dashboard" className="conta-acao">
            Ir para a dashboard
          </Link>
        </div>
      </MolduraDeConta>
    );
  }

  return (
    <MolduraDeConta titulo="Entrar">
      <p className="conta-contexto">
        {convite ? "Entre na sua conta para continuar com o convite de equipe." : "Acesse seus atendimentos e continue a análise."}
      </p>
      <FormularioAuth modo="entrar" convite={convite} />
    </MolduraDeConta>
  );
}
