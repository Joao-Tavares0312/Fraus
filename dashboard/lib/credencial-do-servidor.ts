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
 */

const COOKIE = "fraus_acesso";

export function chaveDoCookie(requisicao: Request): string | undefined {
  const bruto = requisicao.headers.get("cookie");
  if (!bruto) return undefined;
  for (const pedaco of bruto.split(";")) {
    const [nome, ...resto] = pedaco.trim().split("=");
    // `join("=")`: valor de cookie pode conter `=`, e cortar no primeiro
    // truncaria a chave sem erro nenhum aparecer.
    if (nome === COOKIE) return resto.join("=");
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
  const doAmbiente = process.env.FRAUS_CHAVE_ACESSO;
  if (doAmbiente) return `Bearer ${doAmbiente}`;

  const doCookie = chaveDoCookie(requisicao);
  return doCookie ? `Bearer ${doCookie}` : undefined;
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
