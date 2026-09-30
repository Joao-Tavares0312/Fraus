import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { FormularioAuth } from "@/components/auth/FormularioAuth";
import { MolduraDeConta } from "@/components/auth/MolduraDeConta";
import { loginDisponivel, usuarioDaSessao } from "@/lib/sessao";
import { destinoAuth, tokenDeConvite } from "@/lib/destino-auth";

export const metadata: Metadata = { title: "Criar conta — Fraus" };

export default async function PaginaCadastrar({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const convite = tokenDeConvite((await searchParams).convite);
  if (await usuarioDaSessao()) redirect(destinoAuth(convite));

  if (!(await loginDisponivel())) {
    return (
      <MolduraDeConta titulo="Cadastro não configurado">
        <p className="text-sm text-muted-foreground">
          Esta instalação roda em modo aberto: a API não tem a variável{" "}
          <code className="font-mono text-xs">FRAUS_JWT_SEGREDO</code>{" "}
          definida, então contas não têm onde entrar.
        </p>
        <p className="mt-4 text-sm">
          <Link
            href="/dashboard"
            className="text-primary underline-offset-4 hover:underline"
          >
            Ir para a dashboard
          </Link>
        </p>
      </MolduraDeConta>
    );
  }

  return (
    <MolduraDeConta titulo="Criar conta">
      <FormularioAuth modo="cadastrar" convite={convite} />
    </MolduraDeConta>
  );
}
