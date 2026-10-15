"use client";

/**
 * Entrar e cadastrar compartilham campos e estados. O erro vem do servidor:
 * recusas de credencial não ganham variações locais.
 *
 * O código de acesso segue a exigência publicada em /auth/estado. Um convite
 * de equipe é outro fluxo: dispensa o código e não concede papel de dev.
 */

import { useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronDown, Eye, EyeOff, KeyRound, LockKeyhole, Mail, UserRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { destinoAuth } from "@/lib/destino-auth";
import { IconeDeAcao } from "@/components/IconeDeAcao";

type Propriedades = { convite?: string | null } & (
  | { modo: "entrar"; cadastroExigeCodigo?: never }
  | { modo: "cadastrar"; cadastroExigeCodigo: boolean }
);

async function detalheDe(resposta: Response): Promise<string> {
  try {
    const corpo = (await resposta.json()) as { detail?: unknown };
    if (typeof corpo.detail === "string") return corpo.detail;
  } catch {
    // corpo não-JSON (ex.: 502 do proxy com HTML) cai no genérico abaixo
  }
  return `o servidor respondeu ${resposta.status}`;
}

export function FormularioAuth({ modo, convite = null, cadastroExigeCodigo = false }: Propriedades) {
  const roteador = useRouter();
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [senhaVisivel, setSenhaVisivel] = useState(false);

  // A CREDENCIAL E A NAVEGACAO SAO DUAS ESPERAS, e confundi-las era o bug.
  //
  // `router.push` NAO e aguardavel: ele dispara a navegacao e retorna na hora.
  // Quem espera de verdade e o React, montando a arvore nova -- e so um
  // `useTransition` sabe quando isso terminou.
  //
  // Sem esta segunda espera, o formulario voltava a dizer "Entrar" assim que a
  // credencial era aceita, com a navegacao ainda em voo. Medido em producao: o
  // botao normalizava aos 2,1s e a dashboard so aparecia aos 8,1s -- SEIS
  // SEGUNDOS de uma tela que parece ociosa depois de um login que deu certo.
  // Ninguem espera parado diante disso: a pessoa conclui que quebrou e sai.
  //
  // A demora nao e defeito de codigo, e o custo de renderizar a dashboard no
  // servidor da Vercel falando com a API atraves do tunel. O defeito era a tela
  // AFIRMAR que nada estava acontecendo enquanto acontecia.
  const [navegando, iniciarNavegacao] = useTransition();
  const ocupado = enviando || navegando;

  async function enviar(evento: React.FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (ocupado) return;
    setErro(null);
    setEnviando(true);

    const dados = new FormData(evento.currentTarget);
    const email = String(dados.get("email") ?? "");
    const senha = String(dados.get("senha") ?? "");

    try {
      if (modo === "cadastrar") {
        const codigo = convite ? "" : String(dados.get("codigo_dev") ?? "").trim();
        const cadastro = await fetch("/api/fraus/auth/registrar", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            nome: String(dados.get("nome") ?? ""),
            email,
            senha,
            ...(codigo ? { codigo_dev: codigo } : {}),
            ...(convite ? { convite_equipe: convite } : {}),
          }),
        });
        if (!cadastro.ok) {
          setErro(await detalheDe(cadastro));
          setEnviando(false);
          return;
        }
      }
      const entrada = await fetch("/api/sessao/entrar", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email, senha }),
      });
      if (!entrada.ok) {
        setErro(await detalheDe(entrada));
        setEnviando(false);
        return;
      }
      // `enviando` NAO e desligado aqui, e nao e esquecimento: a espera apenas
      // TROCA de dona -- de `enviando` para `navegando`. Desligar entre as duas
      // abriria um piscar em que o botao volta ao normal com a navegacao a
      // caminho, que e o bug inteiro em miniatura.
      iniciarNavegacao(() => {
        roteador.push(destinoAuth(convite));
      });
    } catch {
      setErro("não foi possível falar com o servidor");
      setEnviando(false);
    }
  }

  const entrando = modo === "entrar";

  return (
    <form onSubmit={enviar} className="conta-formulario" aria-busy={ocupado}>
      <nav className="conta-navegacao" aria-label="Acesso à conta">
        <Link
          href={convite ? `/entrar?convite=${convite}` : "/entrar"}
          aria-current={entrando ? "page" : undefined}
        >
          Entrar
        </Link>
        <Link
          href={convite ? `/cadastrar?convite=${convite}` : "/cadastrar"}
          aria-current={!entrando ? "page" : undefined}
        >
          Criar conta
        </Link>
      </nav>
      {modo === "cadastrar" && (
        <div className="conta-campo">
          <Label htmlFor="nome">Nome</Label>
          <div className="conta-entrada">
            <UserRound className="conta-icone-campo" aria-hidden="true" />
            <Input id="nome" name="nome" required autoComplete="name" />
          </div>
        </div>
      )}

      <div className="conta-campo">
        <Label htmlFor="email">E-mail</Label>
        <div className="conta-entrada">
          <Mail className="conta-icone-campo" aria-hidden="true" />
          <Input
            id="email"
            name="email"
            type="email"
            required
            autoComplete="email"
          />
        </div>
      </div>

      <div className="conta-campo">
        <Label htmlFor="senha">Senha</Label>
        <div className="conta-entrada conta-senha">
          <LockKeyhole className="conta-icone-campo" aria-hidden="true" />
          <Input
            id="senha"
            name="senha"
            type={senhaVisivel ? "text" : "password"}
            required
            minLength={entrando ? undefined : 8}
            autoComplete={entrando ? "current-password" : "new-password"}
            aria-describedby={entrando ? undefined : "senha-ajuda"}
          />
          <Button
            type="button"
            variant="ghost"
            className="conta-ver-senha"
            aria-label={senhaVisivel ? "Ocultar senha" : "Mostrar senha"}
            aria-controls="senha"
            aria-pressed={senhaVisivel}
            onClick={() => setSenhaVisivel((visivel) => !visivel)}
          >
            {senhaVisivel ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
          </Button>
        </div>
        {!entrando && (
          <p id="senha-ajuda" className="conta-ajuda">Pelo menos 8 caracteres.</p>
        )}
      </div>

      {modo === "cadastrar" && !convite && (
        <div className="conta-admissao">
          {cadastroExigeCodigo && (
            <p id="codigo-exigencia" className="conta-ajuda">
              Esta instalação exige um código de acesso para criar conta.
            </p>
          )}
          <details className="conta-opcoes">
            <summary aria-describedby={cadastroExigeCodigo ? "codigo-exigencia" : undefined}>
              <KeyRound aria-hidden="true" />
              <span>Código de acesso</span>
              {!cadastroExigeCodigo && <span className="conta-opcional">Opcional</span>}
              <ChevronDown className="conta-chevron" aria-hidden="true" />
            </summary>
            <div className="conta-campo">
              <Label htmlFor="codigo_dev">
                {cadastroExigeCodigo ? "Código de acesso" : "Código de acesso (opcional)"}
              </Label>
              <div className="conta-entrada">
                <KeyRound className="conta-icone-campo" aria-hidden="true" />
                <Input
                  id="codigo_dev"
                  name="codigo_dev"
                  required={cadastroExigeCodigo}
                  autoComplete="off"
                  aria-describedby="codigo-ajuda"
                  onInvalid={(evento) => {
                    // Abre antes de o navegador focar o campo obrigatório.
                    // Não toma o foco dos outros campos inválidos do formulário.
                    const opcoes = evento.currentTarget.closest("details");
                    if (opcoes) opcoes.open = true;
                  }}
                />
              </div>
              <p id="codigo-ajuda" className="conta-ajuda">
                {cadastroExigeCodigo
                  ? "Use o código recebido de quem administra o acesso."
                  : "Use apenas se recebeu um código administrativo."}
              </p>
            </div>
          </details>
        </div>
      )}

      {erro && (
        <p
          role="alert"
          className="conta-erro"
        >
          {erro}
        </p>
      )}

      <Button type="submit" className="conta-enviar" disabled={ocupado}>
        <IconeDeAcao acao={entrando ? "entrar" : "criar"} />
        {/* Tres rotulos para tres estados, e o do meio e o que faltava: depois
            da credencial aceita a espera continua, e chama-la de "Entrando…"
            de novo esconderia que o login JA deu certo e o que resta e abrir a
            tela. Numa instalacao por tunel esse trecho leva segundos, e dizer
            o que se espera e a diferenca entre aguardar e desistir. */}
        {navegando
          ? convite ? "Abrindo o convite…" : "Abrindo a dashboard…"
          : enviando
            ? entrando
              ? "Entrando…"
              : "Criando conta…"
            : entrando
              ? "Entrar"
              : "Criar conta"}
      </Button>

    </form>
  );
}
