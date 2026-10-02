/**
 * De onde sai a credencial que o servidor Next apresenta à API.
 *
 * Existe como modulo proprio porque sao DOIS os caminhos que falam com a API
 * (o proxy geral e a rota que liga a autenticacao), e credencial resolvida em
 * dois lugares diverge: o primeiro sintoma foi a rota de ligar chegar SEM
 * credencial na tentativa de rotacao, tomando 401 do middleware antes de a
 * propria rota poder explicar que faltava a mestra atual.
 *
 * A ordem de precedencia, e o motivo de cada degrau:
 *
 * 1. `Authorization` que veio do cliente -- so a tela de rotacao manda um, e
 *    ele carrega a MESTRA digitada na hora. Precisa vencer, ou trocar a mestra
 *    seria impossivel com um cookie de chave de acesso presente.
 * 2. `FRAUS_CHAVE_ACESSO` -- a credencial declarada do deploy.
 * 3. O cookie `httpOnly` de quem ligou a autenticacao pela tela -- o atalho que
 *    existe porque variavel de ambiente nao muda em processo vivo.
 * 4. O arquivo que a API escreveu na PRIMEIRA subida dela. E o degrau que faz
 *    um clone novo funcionar sem configuracao nenhuma, agora que a API nasce
 *    fechada.
 *
 * OS DEGRAUS 2 E 4 SO VALEM SEM LOGIN, e isto e conserto de 02/10/2026. Eles
 * sao a credencial do SERVIDOR, e o servidor a entregava a quem chegasse: com
 * login de usuario existindo, um visitante sem sessao passava pelo proxy como
 * a chave tecnica do deploy, enquanto as paginas redirecionavam para `/entrar`.
 * O layout se dizia portao "oportunista" porque quem negaria o dado era a API;
 * so que o proxy apresentava a ela uma credencial que passa por tudo, inclusive
 * pelo portao de papel. Agora, onde ha login, quem nao tem sessao nao tem
 * credencial, e a recusa volta a ser da API. Ver `loginExiste`.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const COOKIE = "fraus_acesso";

// O cookie da SESSAO DE USUARIO (JWT). A constante mora AQUI, e nao em
// lib/sessao.ts, porque este modulo entra na cadeia de bundle dos client
// components (via lib/api.ts) e o `next/headers` estatico de lib/sessao.ts
// quebraria o build -- e o motivo de `autorizacaoDoServidorAtual` importar
// `next/headers` dinamicamente.
export const COOKIE_SESSAO = "fraus_sessao";

/**
 * A chave de acesso que a API gravou na PRIMEIRA subida dela.
 *
 * Existe porque a API passou a nascer fechada: sem ler este arquivo, um clone
 * novo subiria a API com autenticação ligada e a dashboard tomaria 401 em toda
 * tela, obrigando o usuário a abrir um .txt e copiar uma chave para uma
 * variável de ambiente -- exatamente o trabalho manual que gerar as chaves
 * sozinha veio eliminar.
 *
 * Só a chave de ACESSO é lida daqui. A mestra está no mesmo arquivo e continua
 * sendo digitada quando se administra chaves: ler a de leitura para a tela
 * funcionar é uma coisa; dar poder de administração a quem abrir a URL, sem
 * login nenhum no caminho, é outra.
 *
 * Ler a cada chamada é deliberado: o arquivo nasce quando a API sobe pela
 * primeira vez, que pode ser DEPOIS do servidor Next: um valor lido uma vez no
 * boot ficaria `undefined` para sempre no caso mais comum de primeiro uso.
 */
function chaveDoArquivo(): string | undefined {
  // O arquivo e conveniencia exclusiva do clone local. Em deploy a chave vem
  // do ambiente; tentar descobrir caminho dinamico faz o bundler rastrear o
  // projeto inteiro e pode empacotar arquivos que nao pertencem ao servidor.
  if (
    process.env.NODE_ENV === "production" &&
    process.env.FRAUS_MODO_LOCAL !== "1"
  ) return undefined;
  const caminho =
    process.env.FRAUS_CAMINHO_CHAVES ??
    resolve(process.cwd(), "..", ".fraus-chaves.txt");
  try {
    // O caminho e configuravel porque API e dashboard podem ser iniciadas de
    // diretorios diferentes no clone local. Ele nao e uma dependencia do
    // bundle: em producao este degrau ja foi encerrado acima e a credencial
    // vem do ambiente. Sem a anotacao, o rastreador do Next inclui o projeto
    // inteiro na funcao server-side ao tentar antecipar todo caminho possivel.
    const conteudo = readFileSync(/* turbopackIgnore: true */ caminho, "utf8");
    return /^chave_acesso=(.+)$/m.exec(conteudo)?.[1]?.trim() || undefined;
  } catch {
    // Não existe (API nunca subiu, ou instalação anterior a este arquivo).
    return undefined;
  }
}

const API = process.env.FRAUS_API_URL ?? "http://localhost:8000";

// Um minuto: `/auth/estado` so muda quando alguem define ou remove
// FRAUS_JWT_SEGREDO e reinicia a API, e a pergunta roda a cada requisicao
// ANONIMA do proxy.
//
// A FALTA de resposta tambem e lembrada, mas so por cinco segundos. Sem isso,
// cada chamada sem sessao a uma API degradada levava uma segunda chamada de
// carona -- dobrar o trafego de quem ja esta lento e exatamente a tempestade
// que o teto do plano B (`obterDetalhes`) existe para evitar. Cinco segundos
// porque a duvida fecha a credencial: lembrar mais que isso manteria a
// dashboard do modo local sem dado depois de a API voltar.
const VALIDADE_DO_ESTADO_MS = 60_000;
const VALIDADE_DA_DUVIDA_MS = 5_000;
const ESPERA_ESTADO_MS = 15_000;
let estadoDoLogin: { existe: boolean | null; ate: number } | null = null;
// Uma pergunta por vez: as chamadas que chegam juntas esperam a mesma resposta.
let perguntaEmCurso: Promise<boolean | null> | null = null;

/** Para os testes: cada caso comeca sem resposta lembrada. */
export function esquecerEstadoDoLogin(): void {
  estadoDoLogin = null;
  perguntaEmCurso = null;
}

/**
 * Se esta instalacao TEM login de usuario -- ou `null` quando nao deu para
 * perguntar.
 *
 * E a pergunta que decide se o servidor empresta a propria credencial a quem
 * chega sem sessao. Sem login (o modo local do README) emprestar e o desenho:
 * a dashboard e de quem a abriu. Com login, emprestar e entregar os dados a
 * qualquer visitante.
 *
 * `null` NAO e `false`. `loginDisponivel`, em lib/sessao.ts, resolve a duvida
 * abrindo a tela, e esta certo ali: tela aberta sem dado e so uma tela. Aqui a
 * duvida fecha, porque o que se abre e a credencial.
 */
async function loginExiste(): Promise<boolean | null> {
  if (estadoDoLogin && Date.now() < estadoDoLogin.ate) return estadoDoLogin.existe;
  perguntaEmCurso ??= perguntarSeHaLogin().finally(() => {
    perguntaEmCurso = null;
  });
  return perguntaEmCurso;
}

async function perguntarSeHaLogin(): Promise<boolean | null> {
  let existe: boolean | null = null;
  try {
    const resposta = await fetch(`${API}/auth/estado`, {
      cache: "no-store",
      signal: AbortSignal.timeout(ESPERA_ESTADO_MS),
    });
    if (resposta.ok) {
      const corpo = (await resposta.json()) as { disponivel?: unknown };
      if (typeof corpo.disponivel === "boolean") existe = corpo.disponivel;
    }
  } catch {
    // API fora do ar ou tempo esgotado: fica a duvida.
  }
  estadoDoLogin = {
    existe,
    ate: Date.now() + (existe === null ? VALIDADE_DA_DUVIDA_MS : VALIDADE_DO_ESTADO_MS),
  };
  return existe;
}

/**
 * Os degraus que NAO sao sessao de usuario, na ordem de sempre: ambiente,
 * cookie de quem ligou a autenticacao pela tela, arquivo da primeira subida.
 *
 * A credencial do proprio servidor (ambiente e arquivo) so entra onde nao ha
 * login. O cookie `fraus_acesso` continua valendo nos dois modos: ele nao e do
 * servidor, e a chave que AQUELE navegador recebeu ao ligar a autenticacao.
 */
async function credencialSemSessao(doCookie: string | undefined): Promise<string | undefined> {
  const servidorEmpresta = (await loginExiste()) === false;
  const doAmbiente = servidorEmpresta ? process.env.FRAUS_CHAVE_ACESSO : undefined;
  if (doAmbiente) return `Bearer ${doAmbiente}`;
  if (doCookie) return `Bearer ${doCookie}`;
  const doArquivo = servidorEmpresta ? chaveDoArquivo() : undefined;
  return doArquivo ? `Bearer ${doArquivo}` : undefined;
}

export function chaveDoCookie(
  requisicao: Request,
  procurado: string = COOKIE,
): string | undefined {
  const bruto = requisicao.headers.get("cookie");
  if (!bruto) return undefined;
  for (const pedaco of bruto.split(";")) {
    const [nome, ...resto] = pedaco.trim().split("=");
    // `join("=")`: valor de cookie pode conter `=`, e cortar no primeiro
    // truncaria a chave sem erro nenhum aparecer.
    if (nome === procurado) return resto.join("=");
  }
  return undefined;
}

/**
 * A credencial DO SERVIDOR: ambiente, ou o cookie de quem ligou pela tela.
 *
 * O `Authorization` do navegador NAO entra aqui, e a omissao e a regra que o
 * proxy sempre teve: a credencial da API e a do deploy, nunca a que o cliente
 * mandar. Um cliente que pudesse escolher o proprio header transformaria o
 * proxy em oraculo para testar chaves.
 */
export async function autorizacaoDoServidor(
  requisicao: Request,
): Promise<string | undefined> {
  // Degrau 0 (31/08/2026): a SESSAO DE USUARIO, quando existe. Ela precisa
  // vencer a chave do deploy, ou o portao de papel da API nunca veria o
  // papel: toda chamada chegaria como a credencial tecnica `fra_`, que passa
  // por tudo, e um analista logado administraria atraves do proxy sem nenhum
  // 403 no caminho. Sessao expirada degrada para os degraus de baixo -- e a
  // dashboard volta a exigir login no proximo render do layout.
  const daSessao = chaveDoCookie(requisicao, COOKIE_SESSAO);
  if (daSessao) return `Bearer ${daSessao}`;

  // Sem sessão: a credencial do servidor só é emprestada onde não há login.
  // O arquivo vem depois do cookie porque quem clicou em ligar nesta sessão
  // declarou uma credencial mais recente que a do primeiro boot.
  return credencialSemSessao(chaveDoCookie(requisicao));
}

/**
 * A mesma credencial do servidor, para quem fala com a API SEM ter um
 * `Request` em maos -- os Server Components, que (em `lib/api.ts`) chamam a
 * API direto em vez de passar pelo proxy (ver o comentario de `urlDaApi`).
 *
 * Existe para nao deixar os Server Components reinventarem o proprio degrau:
 * credencial resolvida em dois lugares diverge, e essa divergencia especifica
 * -- quem ligou a autenticacao pela tela (cookie) ou depende so do arquivo da
 * primeira subida nunca era autenticado no render -- e o bug que este export
 * conserta. A ordem e a MESMA de `autorizacaoDoServidor` acima, de proposito:
 * ambiente, cookie, arquivo.
 *
 * O cookie aqui vem de `next/headers`, que so funciona DENTRO do escopo de
 * uma requisicao (Server Component, Route Handler, Server Action) e lanca
 * fora dele. Por isso so ele fica em try/catch: sem escopo de requisicao a
 * resolucao degrada para ambiente/arquivo em vez de derrubar a pagina --
 * o caso comum de uma dashboard sem cookie mas com o arquivo presente
 * continua funcionando.
 *
 * O degrau 1 do proxy (`Authorization` do cliente) fica de fora de proposito:
 * aqui nao ha requisicao de NAVEGADOR para inspecionar -- o Server Component
 * roda no processo do servidor, nunca no do usuario, entao nao existe cliente
 * para mandar header nenhum.
 */
export async function autorizacaoDoServidorAtual(): Promise<string | undefined> {
  let daSessao: string | undefined;
  let doCookie: string | undefined;
  try {
    const { cookies } = await import("next/headers");
    const jarra = await cookies();
    // Degrau 0, o mesmo de `autorizacaoDoServidor`: a sessao de usuario vence
    // a chave do deploy para o portao de papel da API enxergar o papel.
    daSessao = jarra.get(COOKIE_SESSAO)?.value;
    doCookie = jarra.get(COOKIE)?.value;
  } catch {
    // Fora do escopo de uma requisicao -- `cookies()` lanca. Degrada para os
    // proximos degraus, que nao dependem dele.
  }
  if (daSessao) return `Bearer ${daSessao}`;

  return credencialSemSessao(doCookie);
}

/**
 * A credencial para a rota que LIGA/ROTACIONA a mestra.
 *
 * Aqui o `Authorization` do cliente entra, e precisa: e o unico lugar da
 * dashboard onde o Joao digita a mestra atual, e sem ele rotacionar seria
 * impossivel com um cookie de chave de acesso presente. A rota da API valida a
 * chave de qualquer forma -- ela devolve 409 para credencial que nao seja a
 * mestra vigente, entao aceitar o header nao afrouxa nada.
 *
 * O degrau para a credencial do servidor existe por uma razao de MENSAGEM: sem
 * credencial nenhuma, a chamada de rotacao morre no middleware com "informe a
 * chave de acesso" em vez do 409 que explica que falta a mestra atual.
 */
export async function autorizacaoParaLigar(
  requisicao: Request,
): Promise<string | undefined> {
  return (
    requisicao.headers.get("authorization") ?? (await autorizacaoDoServidor(requisicao))
  );
}

export { COOKIE as NOME_DO_COOKIE };
