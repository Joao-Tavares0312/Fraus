import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { FormularioAuth } from "@/components/auth/FormularioAuth";
import { MolduraDeConta } from "@/components/auth/MolduraDeConta";
import { loginDisponivel, usuarioDaSessao } from "@/lib/sessao";

export const metadata: Metadata = { title: "Entrar — Fraus" };

export default async function PaginaEntrar() {
  // Quem já está logado não tem o que fazer aqui.
  if (await usuarioDaSessao()) redirect("/dashboard");

  if (!(await loginDisponivel())) {
    // Estado vazio nomeia o que falta: sem FRAUS_JWT_SEGREDO na API não
    // existe login — e a dashboard segue aberta, como a API sem mestra.
    return (
      <MolduraDeConta titulo="Login não configurado">
        <p className="text-sm text-muted-foreground">
          Esta instalação roda em modo aberto: a API não tem a variável{" "}
          <code className="font-mono text-xs">FRAUS_JWT_SEGREDO</code>{" "}
          definida, então não há sessão de usuário para abrir.
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
    <MolduraDeConta titulo="Entrar">
      <FormularioAuth modo="entrar" />
    </MolduraDeConta>
  );
}
