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

import { pedidoDeOutroSite, recusaDeOutroSite } from "@/lib/mesma-origem";

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
 *
 * O registro sobrevive a API SUBIR: ele nao e so o guard de "ja tem uma
 * subindo", e a resposta para "esta API e nossa?". Sem isso o botao de
 * desligar nao teria como distinguir o processo que a dashboard iniciou de um
 * uvicorn que o Joao subiu no terminal -- e derrubar o segundo pela tela seria
 * matar processo de outra pessoa.
 */
const estado = globalThis as unknown as {
  __fraus_api?: { pid: number; desde: number } | null;
};

/** O processo que iniciamos, se ele ainda existe. */
function nossoProcesso(): { pid: number; desde: number } | null {
  const lembrado = estado.__fraus_api;
  if (!lembrado) return null;
  if (!processoVivo(lembrado.pid)) {
    estado.__fraus_api = null;
    return null;
  }
  return lembrado;
}

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
  const nosso = nossoProcesso();
  return Response.json({
    disponivel: motivo === null,
    motivo,
    // A API no ar foi subida por ESTA dashboard? É o que decide se o botão de
    // desligar aparece. Falso para um uvicorn de terminal -- e aí a tela não
    // oferece uma ação que levaria 409.
    nossa: nosso !== null,
    pid: nosso?.pid ?? null,
    // Sempre devolvido: o aviso mostra o comando para copiar mesmo quando o
    // botão não existe, e a frase do comando é a mesma que a rota executa --
    // uma fonte só, para a instrução da tela não envelhecer.
    comando: `${COMANDO} ${ARGUMENTOS.join(" ")}`,
    log: LOG,
  });
}

export async function POST(requisicao: Request): Promise<Response> {
  // A QUINTA trava, e a que faltava. As quatro acima defendem contra COMANDO
  // arbitrário; nenhuma delas perguntava QUEM pediu. Um POST sem corpo e sem
  // cabeçalho customizado é requisição simples: não gera preflight, então
  // qualquer página aberta noutra aba conseguia spawnar este processo na
  // máquina de quem roda a dashboard.
  if (pedidoDeOutroSite(requisicao)) return recusaDeOutroSite();

  if (indisponivel() !== null) {
    // 404 e nao 403: a rota simplesmente NAO EXISTE fora do modo local.
    return Response.json({ detail: "não encontrado" }, { status: 404 });
  }

  if (await apiResponde()) {
    // O registro NÃO é apagado aqui: subir com sucesso é exatamente quando ele
    // passa a valer, porque é ele que autoriza o botão de desligar a mexer
    // neste processo e em nenhum outro.
    return Response.json({ estado: "ja-no-ar", nossa: nossoProcesso() !== null });
  }

  // `nossoProcesso` ja confere se ele esta VIVO -- sem isso este guard mentia
  // no cenario mais comum de todos: subir pela tela, derrubar a API no terminal
  // e tentar subir de novo. Dentro dos 90s a rota respondia "ja ha uma API
  // subindo" apontando um pid que ja tinha morrido, e o botao ficava inerte sem
  // explicar por que.
  const subindo = nossoProcesso();
  if (subindo && Date.now() - subindo.desde < 90_000) {
    return Response.json(
      { detail: `já há uma API subindo (pid ${subindo.pid})` },
      { status: 409 },
    );
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
      // morre junto tornaria o botão inútil no cenário que o motiva. No POSIX
      // ele também põe o filho num grupo de processos próprio, que é o que
      // permite ao DELETE derrubar a árvore inteira de uma vez.
      detached: true,
      // Sem isto, no Windows, `detached` abre uma JANELA DE CONSOLE por cima do
      // que o João estiver fazendo -- e ela fica lá, aberta, enquanto a API
      // viver. O stdout já vai para o log; o console não mostrava nada que o
      // arquivo não mostre, só roubava o foco.
      windowsHide: true,
      stdio: ["ignore", log, log],
    });
    processo.unref();

    if (processo.pid === undefined) {
      return Response.json(
        { detail: `não foi possível iniciar. Veja ${LOG}` },
        { status: 500 },
      );
    }

    estado.__fraus_api = { pid: processo.pid, desde: Date.now() };
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

/**
 * Derruba a ÁRVORE do processo, não o processo.
 *
 * O pid que guardamos é o do `uv`, e o uvicorn que atende na porta é NETO dele
 * (`uv` -> `python` -> servidor). Um `kill` no pid lembrado encerra o `uv` e
 * deixa a API no ar, órfã e sem ninguém lembrando o pid dela -- o botão diria
 * "desliguei" com o servidor respondendo normalmente atrás. Foi exatamente esse
 * o comportamento observado ao encerrar processos desta rota na mão.
 *
 * Windows: `taskkill /T` percorre a árvore pelo pai. POSIX: o `detached` da
 * subida pôs o filho num grupo próprio, e o sinal negativo alcança o grupo.
 */
async function pararArvore(pid: number): Promise<void> {
  if (process.platform === "win32") {
    await new Promise<void>((resolver) => {
      const matador = spawn("taskkill", ["/PID", String(pid), "/T", "/F"], {
        shell: false,
        windowsHide: true,
        stdio: "ignore",
      });
      matador.on("close", () => resolver());
      matador.on("error", () => resolver());
    });
    return;
  }
  // SIGTERM, não SIGKILL: o uvicorn fecha as conexões abertas e encerra
  // sozinho. Matar à força uma API que sabe se despedir não compra nada.
  process.kill(-pid, "SIGTERM");
}

/**
 * Desliga a API que ESTA dashboard subiu -- e só ela.
 *
 * Aqui havia uma decisão registrada de que este botão não existiria: matar
 * processo é irreversível e não tem contrapartida numa tela sem login. Ela cai
 * porque a premissa mudou em dois pontos. O primeiro é de escopo: a rota só
 * alcança o processo cujo pid ELA guardou ao subir, então não há como derrubar
 * um uvicorn que o João iniciou no terminal -- esse continua respondendo 409 e
 * sendo trabalho de terminal, como sempre foi. O segundo é de origem: rota que
 * muda estado agora recusa chamada de outro site, então "qualquer aba consegue
 * disparar isto" deixou de ser verdade.
 *
 * O que sobra de irreversível é ligar de novo -- que é o botão ao lado.
 */
export async function DELETE(requisicao: Request): Promise<Response> {
  if (pedidoDeOutroSite(requisicao)) return recusaDeOutroSite();

  if (indisponivel() !== null) {
    return Response.json({ detail: "não encontrado" }, { status: 404 });
  }

  const nosso = nossoProcesso();
  if (!nosso) {
    // 409 e não 404: a rota existe, e a recusa tem um motivo que o operador
    // precisa ler. Uma API subida pelo terminal não é nossa para derrubar.
    return Response.json(
      {
        detail:
          "esta API não foi iniciada pela dashboard — quem subiu pelo " +
          "terminal derruba pelo terminal (Ctrl+C na janela dela).",
      },
      { status: 409 },
    );
  }

  try {
    await pararArvore(nosso.pid);
  } catch (erro) {
    const motivo = erro instanceof Error ? erro.message : String(erro);
    return Response.json(
      { detail: `não foi possível encerrar o processo ${nosso.pid}: ${motivo}` },
      { status: 500 },
    );
  }

  estado.__fraus_api = null;
  return Response.json({ estado: "desligada", pid: nosso.pid });
}
