"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { KeyRound, Lock, LockOpen, RefreshCw } from "lucide-react";
import type { EstadoDeAcesso } from "@/lib/api";
import { ChaveEmClaro } from "@/components/ChaveEmClaro";
import { Painel } from "@/components/Painel";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type Ligadas = {
  chave_mestra: string;
  /** `null` na rotacao: a chave de acesso de antes continua valendo. */
  chave_acesso: string | null;
};

/**
 * Liga a autenticacao da API sem sair da tela.
 *
 * O que o botao faz, na ordem: a API gera a chave MESTRA, grava o hash dela e
 * -- no primeiro uso -- emite junto uma chave de ACESSO para esta dashboard. O
 * servidor NAO e reiniciado: a exigencia de chave vale na requisicao seguinte,
 * porque quem decide e um middleware que le o estado a cada requisicao.
 *
 * A chave de acesso emitida vai para um cookie httpOnly pela rota
 * `/api/fraus/ligar-autenticacao` -- e o que faz a dashboard continuar
 * navegando depois do clique em vez de cair em 401.
 *
 * NAO existe botao de desligar, e a ausencia e deliberada: um controle que
 * BAIXA a defesa nao tem contrapartida de risco aceitavel numa tela sem login.
 * Desligar continua sendo trabalho de ambiente.
 */
export function Autenticacao({
  estado,
  semCredencial = false,
}: {
  estado: EstadoDeAcesso;
  /**
   * A pagina viu 401 nas outras leituras -- isto e, a autenticacao esta ligada
   * e ESTA sessao nao tem credencial. Acontece de verdade: outro navegador, ou
   * o mesmo depois de fechado (o cookie e de sessao).
   */
  semCredencial?: boolean;
}) {
  // O estado de "acabou de ligar" mora no PAI porque duas coisas dependem dele:
  // o corpo (que mostra as chaves) e o rotulo do cabecalho. Com ele so no
  // corpo, o cabecalho seguia dizendo "API aberta" ao lado da mestra
  // recem-criada -- e a tela se contradizia.
  const [ligadas, setLigadas] = useState<Ligadas | null>(null);

  return (
    <Painel
      titulo="Autenticação"
      /* O rotulo mora AQUI, e nao na pagina, porque so este componente sabe que
         a autenticacao acabou de ser ligada: o estado da pagina e do servidor e
         so muda no refresh. Com o rotulo la fora, a tela exibia "API aberta" no
         cabecalho logo acima da chave mestra recem-criada -- duas afirmacoes
         contrarias na mesma tela. */
      acessorio={<IndicadorDeEstado ligada={estado.ligada || ligadas !== null} />}
      legenda="A única coisa nesta tela que não é de leitura: ligar passa a exigir chave em toda rota da API, na requisição seguinte, sem reiniciar o servidor."
      rodape="A chave mestra administra (emite e revoga chaves de acesso, troca a si mesma); a chave de acesso apenas lê. POST /ingestao segue regido pela chave da fonte, que é uma credencial por rota — nenhuma das duas a substitui."
    >
      <Corpo
        estado={estado}
        semCredencial={semCredencial}
        ligadas={ligadas}
        setLigadas={setLigadas}
      />
    </Painel>
  );
}


function Corpo({
  estado,
  semCredencial,
  ligadas,
  setLigadas,
}: {
  estado: EstadoDeAcesso;
  semCredencial: boolean;
  ligadas: Ligadas | null;
  setLigadas: (valor: Ligadas | null) => void;
}) {
  const router = useRouter();
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [mestraAtual, setMestraAtual] = useState("");

  async function ligar(comMestraAtual?: string) {
    setOcupado(true);
    setErro(null);
    try {
      const resposta = await fetch("/api/fraus/ligar-autenticacao", {
        method: "POST",
        headers: comMestraAtual
          ? { authorization: `Bearer ${comMestraAtual}` }
          : {},
      });
      const corpo = await resposta.json().catch(() => null);
      if (!resposta.ok) {
        // A frase da API é a instrução útil ("apresente a atual em
        // Authorization"). Trocá-la por "erro ao ligar" jogaria fora a única
        // informação que diz o que fazer em seguida.
        setErro(corpo?.detail ?? `a API respondeu ${resposta.status}`);
        return;
      }
      setLigadas({
        chave_mestra: corpo.chave_mestra,
        chave_acesso: corpo.chave_acesso ?? null,
      });
      setMestraAtual("");
      // NAO chamo router.refresh() aqui: o re-render do server component
      // remontaria este painel e a chave em claro sumiria da tela antes de o
      // João copiá-la. O refresh acontece quando ele dispensa o aviso.
    } catch {
      setErro("não foi possível falar com a dashboard");
    } finally {
      setOcupado(false);
    }
  }

  function dispensar() {
    setLigadas(null);
    router.refresh();
  }

  if (ligadas) {
    return (
      <div className="flex flex-col gap-3">
        <ChaveEmClaro chave={ligadas.chave_mestra} titulo="Chave mestra — copie agora">
          <p>
            É a credencial de <strong>administração</strong>: emitir e revogar
            chaves de acesso, e trocar a própria mestra. O servidor guarda apenas
            o hash dela — se você perder, o conserto é definir{" "}
            <code className="num">FRAUS_CHAVE_MESTRA</code> no ambiente e
            reiniciar a API.
          </p>
        </ChaveEmClaro>

        {ligadas.chave_acesso ? (
          <ChaveEmClaro
            chave={ligadas.chave_acesso}
            titulo="Chave de acesso desta dashboard"
          >
            <p>
              Já está em uso: ela foi guardada num cookie do servidor, e é por
              isso que esta tela continua funcionando. Guarde a cópia para subir
              a dashboard em outro lugar com{" "}
              <code className="num">FRAUS_CHAVE_ACESSO</code>.
            </p>
          </ChaveEmClaro>
        ) : (
          <Alert>
            <AlertTitle>Mestra trocada</AlertTitle>
            <AlertDescription>
              A anterior deixou de valer agora. As chaves de acesso continuam as
              mesmas — trocar a mestra não desconecta a dashboard.
            </AlertDescription>
          </Alert>
        )}

        <div>
          <Button type="button" size="sm" variant="outline" onClick={dispensar}>
            Já copiei
          </Button>
        </div>
      </div>
    );
  }

  if (!estado.ligada) {
    return (
      <div className="flex flex-col gap-3">
        {erro ? (
          <Alert variant="destructive">
            <AlertTitle>Não foi possível ligar</AlertTitle>
            <AlertDescription>{erro}</AlertDescription>
          </Alert>
        ) : null}

        <p className="text-xs leading-relaxed text-muted-foreground">
          A API está <strong className="text-foreground">aberta</strong>: quem
          alcança a porta dela lê os atendimentos, sem chave. Ligar gera a chave
          mestra e uma chave de acesso para esta dashboard, e passa a exigir
          credencial em toda rota — <strong>sem reiniciar o servidor</strong>. A
          exceção é <code className="num">POST /ingestao</code>, que continua
          regido pela chave da fonte.
        </p>

        <div>
          <Button type="button" size="sm" onClick={() => ligar()} disabled={ocupado}>
            <Lock aria-hidden />
            {ocupado ? "Ligando…" : "Ligar autenticação"}
          </Button>
        </div>
      </div>
    );
  }

  if (estado.origem === "ambiente") {
    return (
      <div className="flex flex-col gap-2">
        <p className="text-xs leading-relaxed text-muted-foreground">
          Ligada, com a mestra vinda do{" "}
          <strong className="text-foreground">ambiente</strong> (
          <code className="num">FRAUS_CHAVE_MESTRA</code>). A variável tem
          precedência sobre qualquer chave gravada, então esta tela não a troca:
          trocar por aqui criaria duas credenciais com a do ambiente ganhando, e
          o botão pareceria funcionar sem mudar nada.
        </p>
        <p className="text-xs leading-relaxed text-muted-foreground">
          Para trocar: edite a variável e reinicie a API. As chaves de acesso
          continuam valendo — quem perde o posto é só a mestra.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {erro ? (
        <Alert variant="destructive">
          <AlertTitle>Não foi possível trocar</AlertTitle>
          <AlertDescription>{erro}</AlertDescription>
        </Alert>
      ) : null}

      {semCredencial ? (
        <Alert>
          <AlertTitle>Esta sessão não tem chave de acesso</AlertTitle>
          <AlertDescription>
            A autenticação está ligada e as telas de dados vão responder 401
            daqui. A chave desta dashboard foi guardada num cookie de sessão
            quando alguém clicou em ligar — outro navegador, ou este depois de
            fechado, não a tem. O conserto é subir a dashboard com{" "}
            <code className="num">FRAUS_CHAVE_ACESSO</code>, ou emitir outra com
            a mestra em <code className="num">POST /acesso/chaves</code>.
          </AlertDescription>
        </Alert>
      ) : null}

      <p className="text-xs leading-relaxed text-muted-foreground">
        Ligada, com a mestra <strong className="text-foreground">gravada</strong>{" "}
        nesta instalação — ela sobrevive a reiniciar a API. As chaves de acesso
        emitidas aparecem em{" "}
        <code className="num">GET /acesso/chaves</code> e podem ser revogadas uma
        a uma sem tocar na mestra.
      </p>

      <details className="text-xs text-muted-foreground">
        <summary className="cursor-pointer">Trocar a chave mestra</summary>
        <div className="mt-2 flex flex-col gap-2">
          <p>
            Exige a mestra <strong>atual</strong> — sem ela a troca é recusada
            com 409, e é isso que impede alguém de tomar a API de quem já está
            dentro. A antiga deixa de valer no mesmo instante.
          </p>
          <Label htmlFor="mestra-atual" className="text-foreground">
            Chave mestra atual
          </Label>
          <Input
            id="mestra-atual"
            type="password"
            autoComplete="off"
            className="num"
            placeholder="frm_…"
            value={mestraAtual}
            onChange={(evento) => setMestraAtual(evento.target.value)}
          />
          <div>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => ligar(mestraAtual)}
              disabled={ocupado || mestraAtual.trim() === ""}
            >
              <RefreshCw aria-hidden />
              {ocupado ? "Trocando…" : "Gerar nova mestra"}
            </Button>
          </div>
        </div>
      </details>
    </div>
  );
}

/** Rótulo do cabeçalho: o estado legível antes de qualquer prosa. */
function IndicadorDeEstado({ ligada }: { ligada: boolean }) {
  return ligada ? (
    <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
      <KeyRound aria-hidden className="size-3.5" />
      exigindo chave
    </span>
  ) : (
    <span className="flex items-center gap-1.5 text-xs" style={{ color: "var(--detrator)" }}>
      <LockOpen aria-hidden className="size-3.5" />
      API aberta
    </span>
  );
}
