/**
 * MODO LOCAL: sobe a API do Fraus como processo filho do servidor Next.
 *
 * Uma rota HTTP que dispara um comando e execucao remota de codigo. Esta aqui
 * existe sob CINCO travas SIMULTANEAS, e nenhuma delas e opcional:
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
 * 5. **So a propria dashboard chama.** Requisicao de outro site leva 403. As
 *    quatro travas acima defendem contra COMANDO arbitrario, e nenhuma delas
 *    perguntava QUEM pediu -- um POST sem corpo e sem cabecalho customizado e
 *    requisicao simples, que nao gera preflight.
 *
 * DERRUBAR e possivel (`DELETE`), mas so o processo que ESTA rota subiu: um
 * uvicorn iniciado no terminal continua sendo trabalho de terminal.
 */

import { spawn } from "node:child_process";
import { existsSync, openSync, readFileSync } from "node:fs";
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
/**
 * HOST E PORTA VEM DO `FRAUS_API_URL`, e nao cravados aqui.
 *
 * Eram `127.0.0.1:8000` fixos enquanto a linha 36 ja lia a variavel para saber
 * ONDE falar com a API. Os dois lados podiam discordar em silencio: quem
 * apontasse o `FRAUS_API_URL` para outra porta veria o botao subir a API na
 * 8000 e a dashboard procurar noutro lugar -- "iniciei e continua fora do ar",
 * sem nenhuma pista de por que.
 *
 * Aconteceu de verdade nesta maquina: a 8000 ja estava tomada por outro
 * processo e o uvicorn morria com `winerror 10013` DEPOIS de "startup
 * complete", entao o log parecia o de uma API sadia.
 *
 * NAO ENFRAQUECE A TRAVA 2: o valor vem do ambiente do servidor, que e o mesmo
 * nivel de confianca do codigo -- nunca do corpo nem dos cabecalhos da
 * requisicao. Ainda assim a porta e validada como inteiro em faixa antes de
 * virar argumento, porque variavel de ambiente torta deve falhar aqui e nao
 * dentro do uvicorn.
 */
function enderecoDeEscuta(): { host: string; porta: string } {
  const padrao = { host: "127.0.0.1", porta: "8000" };
  let url: URL;
  try {
    url = new URL(API);
  } catch {
    return padrao;
  }
  const porta = Number(url.port || (url.protocol === "https:" ? 443 : 80));
  if (!Number.isInteger(porta) || porta < 1 || porta > 65535) return padrao;
  // `localhost` vira 127.0.0.1: em Windows com pilha dupla o uvicorn ligado a
  // `localhost` pode escutar so em IPv6, e o fetch do Next chega por IPv4.
  const host =
    url.hostname === "localhost" || url.hostname === "::1"
      ? "127.0.0.1"
      : url.hostname;
  return { host, porta: String(porta) };
}

const { host: HOST_ESCUTA, porta: PORTA_ESCUTA } = enderecoDeEscuta();

/**
 * `python -m uvicorn` e nao `uv run uvicorn`: o segundo depende do trampolim
 * que o uv instala para o `uvicorn.exe` do .venv, e esse trampolim quebra
 * ("uv trampoline failed to canonicalize script path") quando o venv e movido
 * ou recriado -- foi o que aconteceu nesta maquina.
 */
const COMANDO = "uv";
const ARGUMENTOS = [
  "run",
  "python",
  "-m",
  "uvicorn",
  "fraus.api.main:app",
  "--host",
  HOST_ESCUTA,
  "--port",
  PORTA_ESCUTA,
];

/** Os argumentos do uvicorn, sem quem o executa. */
const ALVO = ARGUMENTOS.slice(2);

/**
 * O `pythonw.exe` BASE do venv -- o interpretador que não abre console.
 *
 * O PROBLEMA QUE ISTO RESOLVE. Subir pelo botão abria uma janela de console
 * por cima da tela, e ela ficava aberta enquanto a API vivesse. `windowsHide:
 * true` sozinho não resolve, por dois motivos que se somam:
 *
 * 1. `detached: true` liga `DETACHED_PROCESS`, e a documentação do
 *    `CreateProcess` diz que `CREATE_NO_WINDOW` -- o que o `windowsHide`
 *    liga -- é IGNORADO nessa combinação. E `detached` não é opcional aqui: a
 *    API precisa sobreviver ao reload do servidor Next. Medido: sem ele, o
 *    processo morre junto com quem o iniciou.
 * 2. Mesmo que resolvesse, a flag vale para o filho IMEDIATO. `uv run python`
 *    executa o interpretador como processo PRÓPRIO, e esse neto é um app de
 *    console sem console para herdar -- situação em que o Windows aloca um
 *    novo. O `conhost` observado tinha como pai o `python`, não o `uv`.
 *
 * A saída é não ter neto: chamar o interpretador direto. O `python.exe` do
 * `.venv/Scripts` também não serve -- num venv do `uv` ele é um TRAMPOLIM que
 * lança o interpretador de verdade, recriando o neto (`sys._base_executable`
 * aponta para outro lugar). Quem serve é o `pythonw.exe` do diretório `home`
 * declarado no `pyvenv.cfg`: mesmo interpretador, compilado para o subsistema
 * GUI, sem console e sem alocar um.
 *
 * Como ele é o interpretador BASE, o venv precisa entrar por `PYTHONPATH` (ver
 * `comandoReal`). É um degrau a menos de isolamento do que ativar o venv,
 * e aceitável aqui porque o venv foi criado A PARTIR deste mesmo interpretador:
 * mesma versão, mesmo ABI, e o `site-packages` da base do `uv` é vazio.
 *
 * `null` fora do Windows (não há console a esconder) ou quando o venv não
 * existe -- e aí o comando volta a ser o `uv`, com a janela e tudo. Preferível
 * a não subir.
 */
function pythonSemConsole(): string | null {
  if (process.platform !== "win32") return null;
  try {
    const configuracao = readFileSync(resolve(RAIZ, ".venv", "pyvenv.cfg"), "utf8");
    const base = /^home\s*=\s*(.+)$/m.exec(configuracao)?.[1]?.trim();
    if (!base) return null;
    const caminho = resolve(base, "pythonw.exe");
    return existsSync(caminho) ? caminho : null;
  } catch {
    // Sem `.venv` ainda (clone novo, antes do `uv sync`). O `uv` resolve.
    return null;
  }
}

/**
 * O que vai ser executado de fato, com o ambiente que aquele caminho exige.
 *
 * `PYTHONPATH` só entra no caminho do interpretador BASE, e só nele: é ele que
 * não enxergaria o `uvicorn` nem o `torch` sem ajuda, porque não é o
 * interpretador do venv. Pelo `uv` a variável não teria função nenhuma -- e o
 * caminho `Lib/Scripts` que ela apontaria nem existe fora do Windows.
 */
function comandoReal(): {
  comando: string;
  argumentos: string[];
  ambiente: NodeJS.ProcessEnv;
} {
  const semConsole = pythonSemConsole();
  if (semConsole) {
    return {
      comando: semConsole,
      argumentos: ALVO,
      ambiente: {
        ...process.env,
        PYTHONPATH: resolve(RAIZ, ".venv", "Lib", "site-packages"),
      },
    };
  }
  return { comando: COMANDO, argumentos: ARGUMENTOS, ambiente: process.env };
}

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

/**
 * A ULTIMA LINHA DE FALHA DO LOG, para a tela mostrar o que aconteceu de
 * verdade em vez de adivinhar.
 *
 * POR QUE ISTO EXISTE: o aviso dizia "o motivo mais comum e modelo ausente em
 * modelos/". Num caso real o modelo estava no lugar e o uvicorn morria com
 * `winerror 10013` -- porta ja tomada por outro processo --, DEPOIS de
 * "startup complete", entao nem o log lido por cima denunciava. A tela
 * afirmava com seguranca uma causa errada e mandava o Joao procurar no lugar
 * errado.
 *
 * Numa ferramenta batizada com o nome do daemon do engano, palpite apresentado
 * como diagnostico e o pior defeito possivel. O principio de produto ja
 * mandava: onde falta dado, a tela NOMEIA o que falta -- nao preenche com o
 * plausivel.
 *
 * Devolve `null` quando nao ha log ou nao ha falha nele: sem linha de erro, a
 * tela volta a dizer so o que sabe.
 */
function ultimaFalhaDoLog(): string | null {
  try {
    if (!existsSync(LOG)) return null;
    const linhas = readFileSync(LOG, "utf8").split(/\r?\n/);
    for (let i = linhas.length - 1; i >= 0; i -= 1) {
      const linha = linhas[i].trim();
      if (!linha) continue;
      if (/^(ERROR|CRITICAL)/.test(linha) || /Error:|Exception:/.test(linha)) {
        // Teto de tamanho: traceback inteiro nao cabe numa faixa de aviso, e a
        // ultima linha e a que diz o que falhou.
        return linha.length > 300 ? `${linha.slice(0, 300)}…` : linha;
      }
    }
    return null;
  } catch {
    // Log ilegivel nao pode derrubar a rota que existe para diagnosticar.
    return null;
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
    // botão não existe.
    //
    // É o comando do `uv`, e NÃO o `pythonw.exe` que a rota pode executar: no
    // terminal, quem digita quer ver o log rolando e derrubar com Ctrl+C, e o
    // `pythonw` sairia mudo e sem console -- exatamente o que se quer do botão
    // e exatamente o que não se quer da mão. Cada caminho mostra o comando que
    // serve a ele.
    comando: `${COMANDO} ${ARGUMENTOS.join(" ")}`,
    log: LOG,
    // A ULTIMA FALHA REAL, e nao um palpite. Ver `ultimaFalhaDoLog`.
    ultimaFalha: ultimaFalhaDoLog(),
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
    const { comando, argumentos, ambiente } = comandoReal();
    const processo = spawn(comando, argumentos, {
      cwd: RAIZ,
      env: ambiente,
      // Sem shell: o argv vai direto para o executável, e não existe string de
      // comando para um `;` ou um `&&` alterarem.
      shell: false,
      // `detached` para a API sobreviver a um reload do servidor Next -- em
      // desenvolvimento ele recompila e reinicia o tempo todo, e uma API que
      // morre junto tornaria o botão inútil no cenário que o motiva. No POSIX
      // ele também põe o filho num grupo de processos próprio, que é o que
      // permite ao DELETE derrubar a árvore inteira de uma vez.
      detached: true,
      // Esconde o console do filho IMEDIATO. Sozinho não bastava: quem abria a
      // janela era o NETO (`uv` -> `python`), e por isso a subida usa o
      // `pythonw.exe` do venv quando ele existe -- ver `interpretadorSemConsole`.
      // As duas coisas juntas é que fecham o caso.
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
