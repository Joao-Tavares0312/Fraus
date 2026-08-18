/**
 * MODO LOCAL: sobe a API do Fraus como processo filho do servidor Next.
 *
 * Uma rota HTTP que dispara um comando e execucao remota de codigo. Esta aqui
 * existe sob quatro travas SIMULTANEAS, e nenhuma delas e opcional:
 *
 * 1. **Ligada em desenvolvimento, desligada em producao.** Padrao por
 *    `NODE_ENV`, com `FRAUS_MODO_LOCAL` como override explicito nos dois
 *    sentidos (ver `modoLocalLigado`). Desligada, a rota responde 404 -- nao
 *    403: quem nao deveria saber que ela existe nao descobre que existe. Um
 *    build de producao (`npm run build && npm run start`) fica sem ela por
 *    padrao; publicar isso ligado exige `FRAUS_MODO_LOCAL=1` no deploy, o que
 *    e deliberadamente um passo a mais, nao um esquecimento.
 * 2. **Comando fixo.** O argv e literal neste arquivo. Nada do corpo, da query
 *    ou dos cabecalhos entra nele, e o spawn roda SEM shell -- nao ha string
 *    de comando a injetar.
 * 3. **Uma instancia.** Consulta `/saude` antes de subir e lembra o processo
 *    que ja iniciou.
 * 4. **Escuta so em 127.0.0.1.** A API subida daqui nao aceita conexao de fora
 *    da maquina.
 *
 * NAO existe caminho para DERRUBAR a API: matar processo e irreversivel e nao
 * tem contrapartida numa tela sem login. Quem subiu pelo terminal derruba pelo
 * terminal.
 */

import { spawn } from "node:child_process";
import { openSync } from "node:fs";
import { resolve } from "node:path";

const API = process.env.FRAUS_API_URL ?? "http://localhost:8000";

/** Onde o stdout/stderr da API vai parar. Sem log, "nao subiu" e beco sem saida. */
const LOG = resolve(process.cwd(), ".fraus-api.log");

/** A raiz do repositorio -- o `dashboard/` e um nivel abaixo dela. */
const RAIZ = resolve(process.cwd(), "..");

/**
 * O comando, literal. Trocar isto por algo vindo da requisicao seria trocar a
 * trava 2 por uma porta de execucao arbitraria.
 *
 * `python -m uvicorn` e nao `uv run uvicorn`: o segundo depende do trampolim
 * que o uv instala para o `uvicorn.exe` do .venv, e esse trampolim quebra
 * ("uv trampoline failed to canonicalize script path") quando o venv e movido
 * ou recriado -- foi o que aconteceu nesta maquina. `-m` chama o modulo pelo
 * interpretador e nao depende de shim nenhum.
 */
const COMANDO = "uv";
const ARGUMENTOS = [
  "run",
  "python",
  "-m",
  "uvicorn",
  "fraus.api.main:app",
  "--host",
  "127.0.0.1",
  "--port",
  "8000",
];

/**
 * O processo que ESTA rota iniciou, lembrado entre requisicoes.
 *
 * Vai no `globalThis` porque o hot reload do Next descarta o modulo e criaria
 * um segundo "primeiro" processo a cada recompilacao em desenvolvimento --
 * exatamente o cenario em que este botao e usado.
 */
const estado = globalThis as unknown as {
  __fraus_subindo?: { pid: number; desde: number } | null;
};

/**
 * Ligado por padrao em DESENVOLVIMENTO, desligado por padrao em producao.
 *
 * `npm run dev` seta `NODE_ENV=development` sozinho -- e essa e a distincao
 * que importa, nao a presenca da variavel. Sem o padrao, quem roda `npm run
 * dev` sem lembrar de exportar `FRAUS_MODO_LOCAL=1` perde o botao sem aviso
 * nenhum, e foi exatamente esse o caso que motivou a mudanca.
 *
 * `FRAUS_MODO_LOCAL` continua valendo como OVERRIDE explicito nos dois
 * sentidos: `"1"` liga mesmo em producao (raro, e por isso exige a variavel),
 * `"0"` desliga mesmo em dev (para quem quer testar a dashboard como ela se
 * comporta publicada, sem subir outro ambiente).
 */
function modoLocalLigado(): boolean {
  if (process.env.FRAUS_MODO_LOCAL === "1") return true;
  if (process.env.FRAUS_MODO_LOCAL === "0") return false;
  return process.env.NODE_ENV !== "production";
}

/**
 * A API configurada roda NESTA maquina?
 *
 * Se `FRAUS_API_URL` aponta para outro host, nao ha o que iniciar aqui -- e
 * subir um uvicorn local seria pior do que nao fazer nada: a dashboard
 * continuaria falando com o host remoto, e o botao teria "funcionado" sem
 * consertar coisa alguma.
 */
function apiELocal(): boolean {
  try {
    const { hostname } = new URL(API);
    return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1";
  } catch {
    return false;
  }
}

function indisponivel(): string | null {
  if (!modoLocalLigado()) {
    return process.env.NODE_ENV === "production"
      ? "modo local desligado em produção (defina FRAUS_MODO_LOCAL=1 para ligar)"
      : "modo local desligado (FRAUS_MODO_LOCAL=0)";
  }
  if (!apiELocal()) return `a API não é local: ${API}`;
  return null;
}

/**
 * O processo ainda existe?
 *
 * `kill(pid, 0)` nao envia sinal nenhum -- so pergunta. Lanca quando o processo
 * sumiu, e e essa a unica resposta que interessa aqui.
 */
function processoVivo(pid: number): boolean {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

async function apiResponde(): Promise<boolean> {
  try {
    const resposta = await fetch(`${API}/saude`, {
      cache: "no-store",
      signal: AbortSignal.timeout(2_000),
    });
    return resposta.ok;
  } catch {
    return false;
  }
}

/** A tela pergunta ANTES de desenhar o botão: sem isto ela ofereceria um 404. */
export async function GET(): Promise<Response> {
  const motivo = indisponivel();
  return Response.json({
    disponivel: motivo === null,
    motivo,
    // Sempre devolvido: o aviso mostra o comando para copiar mesmo quando o
    // botão não existe, e a frase do comando é a mesma que a rota executa --
    // uma fonte só, para a instrução da tela não envelhecer.
    comando: `${COMANDO} ${ARGUMENTOS.join(" ")}`,
    log: LOG,
  });
}

export async function POST(): Promise<Response> {
  if (indisponivel() !== null) {
    // 404 e nao 403: a rota simplesmente NAO EXISTE fora do modo local.
    return Response.json({ detail: "não encontrado" }, { status: 404 });
  }

  if (await apiResponde()) {
    estado.__fraus_subindo = null;
    return Response.json({ estado: "ja-no-ar" });
  }

  const subindo = estado.__fraus_subindo;
  if (subindo) {
    // Duas condicoes, e as DUAS precisam valer para recusar: o processo
    // lembrado ainda existe E ainda esta dentro do teto.
    //
    // Sem a checagem de vida, este guard mentia no cenario mais comum de todos:
    // subir pela tela, derrubar a API no terminal e tentar subir de novo --
    // dentro dos 90s a rota respondia "ja ha uma API subindo" apontando um pid
    // que ja tinha morrido, e o botao ficava inerte sem explicar por que.
    const decorrido = Date.now() - subindo.desde;
    if (decorrido < 90_000 && processoVivo(subindo.pid)) {
      return Response.json(
        { detail: `já há uma API subindo (pid ${subindo.pid})` },
        { status: 409 },
      );
    }
    estado.__fraus_subindo = null;
  }

  try {
    const log = openSync(LOG, "a");
    const processo = spawn(COMANDO, ARGUMENTOS, {
      cwd: RAIZ,
      // Sem shell: o argv vai direto para o executável, e não existe string de
      // comando para um `;` ou um `&&` alterarem.
      shell: false,
      // `detached` para a API sobreviver a um reload do servidor Next -- em
      // desenvolvimento ele recompila e reinicia o tempo todo, e uma API que
      // morre junto tornaria o botão inútil no cenário que o motiva.
      detached: true,
      stdio: ["ignore", log, log],
    });
    processo.unref();

    if (processo.pid === undefined) {
      return Response.json(
        { detail: `não foi possível iniciar. Veja ${LOG}` },
        { status: 500 },
      );
    }

    estado.__fraus_subindo = { pid: processo.pid, desde: Date.now() };
    return Response.json(
      { estado: "subindo", pid: processo.pid, log: LOG },
      { status: 202 },
    );
  } catch (erro) {
    // `uv` fora do PATH cai aqui. A mensagem nomeia o comando e o log, porque
    // "falhou ao iniciar" sem eles não diz o que consertar.
    const motivo = erro instanceof Error ? erro.message : String(erro);
    return Response.json(
      { detail: `não foi possível executar \`${COMANDO}\`: ${motivo}. Veja ${LOG}` },
      { status: 500 },
    );
  }
}
