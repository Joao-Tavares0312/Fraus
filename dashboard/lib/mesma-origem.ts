/**
 * A trava que separa "a dashboard pediu" de "outro site pediu pela dashboard".
 *
 * O PROBLEMA. As rotas deste servidor mudam estado -- o proxy escreve na API
 * com a credencial do deploy, `/api/fraus/iniciar` sobe um processo. Nenhuma
 * delas perguntava QUEM pediu. Um site qualquer aberto noutra aba podia
 * disparar um POST para `localhost:3000` e o efeito acontecia: o navegador
 * bloqueia a LEITURA da resposta (CORS), nunca o envio da requisicao. Dois
 * alvos concretos: `/api/fraus/iniciar`, que executa um comando na maquina, e
 * `POST /api/fraus/acesso/mestra`, que ligaria a autenticacao com uma chave
 * que ninguem chega a ver -- trancando o dono fora da propria API.
 *
 * As rotas de corpo JSON estavam protegidas por ACIDENTE: `content-type:
 * application/json` obriga o navegador a fazer preflight, o Next nao responde
 * OPTIONS, e o preflight morre. Isso e sorte de configuracao, nao defesa --
 * some no dia em que alguem aceitar `text/plain`, e sem aviso nenhum.
 *
 * A REGRA. `Sec-Fetch-Site` e um cabecalho que o NAVEGADOR escreve e que o JS
 * da pagina nao consegue forjar (e um nome proibido pela spec do fetch). Ele
 * diz de onde a requisicao partiu, e e por isso que da para confiar nele:
 *
 * - `same-origin` -> a propria dashboard. Passa.
 * - `cross-site` / `same-site` -> outro site. Recusa.
 * - `none` -> o usuario digitou a URL ou abriu um favorito. Passa: nao ha
 *   pagina de terceiro no meio.
 * - AUSENTE -> nao veio de navegador nenhum (curl, script, um teste). Passa.
 *   Recusar aqui quebraria todo cliente de linha de comando sem fechar buraco
 *   algum: um navegador NAO consegue omitir esse cabecalho, entao a ausencia
 *   nunca e um ataque disfarcado.
 *
 * O `Origin` entra como segundo degrau para navegador antigo que nao manda
 * `Sec-Fetch-Site`: se ele existe e nao bate com o host da requisicao, recusa.
 */

/** Métodos que mudam estado. `GET`/`HEAD` não passam por aqui. */
const METODOS_PROTEGIDOS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export function pedidoDeOutroSite(requisicao: Request): boolean {
  if (!METODOS_PROTEGIDOS.has(requisicao.method.toUpperCase())) return false;

  const local = requisicao.headers.get("sec-fetch-site");
  if (local === "cross-site" || local === "same-site") return true;

  // Navegador sem Sec-Fetch-Site: o Origin ainda denuncia a origem cruzada.
  const origem = requisicao.headers.get("origin");
  if (origem) {
    try {
      // Comparação por HOST, não pela URL inteira: a dashboard é alcançada por
      // `localhost:3000` e por `127.0.0.1:3000`, e cada um deles é a origem
      // legítima de si mesmo. O host da requisição é a referência porque é o
      // endereço pelo qual esta página foi de fato aberta.
      const host = requisicao.headers.get("host");
      if (host && new URL(origem).host !== host) return true;
    } catch {
      // Origin malformado não é requisição de navegador saudável.
      return true;
    }
  }

  return false;
}

/** A recusa, com a mesma frase nas três rotas. */
export function recusaDeOutroSite(): Response {
  return Response.json(
    {
      detail:
        "requisição de outra origem recusada. Esta rota muda estado e só " +
        "aceita chamadas feitas pela própria dashboard.",
    },
    { status: 403 },
  );
}
