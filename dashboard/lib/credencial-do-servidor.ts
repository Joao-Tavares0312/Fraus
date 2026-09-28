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
    const conteudo = readFileSync(caminho, "utf8");
    return /^chave_acesso=(.+)$/m.exec(conteudo)?.[1]?.trim() || undefined;
  } catch {
    // Não existe (API nunca subiu, ou instalação anterior a este arquivo).
    return undefined;
  }
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
export function autorizacaoDoServidor(requisicao: Request): string | undefined {
  // Degrau 0 (31/08/2026): a SESSAO DE USUARIO, quando existe. Ela precisa
  // vencer a chave do deploy, ou o portao de papel da API nunca veria o
  // papel: toda chamada chegaria como a credencial tecnica `fra_`, que passa
  // por tudo, e um analista logado administraria atraves do proxy sem nenhum
  // 403 no caminho. Sessao expirada degrada para os degraus de baixo -- e a
  // dashboard volta a exigir login no proximo render do layout.
  const daSessao = chaveDoCookie(requisicao, COOKIE_SESSAO);
  if (daSessao) return `Bearer ${daSessao}`;

  const doAmbiente = process.env.FRAUS_CHAVE_ACESSO;
  if (doAmbiente) return `Bearer ${doAmbiente}`;

  const doCookie = chaveDoCookie(requisicao);
  if (doCookie) return `Bearer ${doCookie}`;

  // Último degrau: a chave que a própria API gerou na primeira subida. Vem
  // depois do cookie porque quem clicou em ligar nesta sessão declarou uma
  // credencial mais recente que a do primeiro boot.
  const doArquivo = chaveDoArquivo();
  return doArquivo ? `Bearer ${doArquivo}` : undefined;
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

  const doAmbiente = process.env.FRAUS_CHAVE_ACESSO;
  if (doAmbiente) return `Bearer ${doAmbiente}`;

  if (doCookie) return `Bearer ${doCookie}`;

  const doArquivo = chaveDoArquivo();
  return doArquivo ? `Bearer ${doArquivo}` : undefined;
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
export function autorizacaoParaLigar(requisicao: Request): string | undefined {
  return (
    requisicao.headers.get("authorization") ?? autorizacaoDoServidor(requisicao)
  );
}

export { COOKIE as NOME_DO_COOKIE };
