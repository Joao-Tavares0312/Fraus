# Autenticação da API — design

**Data:** 2026-08-14 · **Status:** aprovado em conversa, aguardando implementação

## O problema

A chave de API protege só `POST /ingestao`. Todo o resto — leitura de conversas
com PII, importação, análise, e inclusive a rota que **gera** a chave de
ingestão — é aberto. Aceitável rodando local; inaceitável hospedado com dado
real (o adaptador da Totalk já traz conversa de cliente de verdade, e o texto
das mensagens carrega nome, documento e endereço). Esta é a pendência P0 de
autenticação do README.

## Decisões (tomadas com o João, 14/08)

1. **Modelo de acesso: múltiplas chaves de leitura revogáveis** — não um token
   único, não login com senha. Reusa o desenho de `fraus/credencial.py`.
2. **Bootstrap: variável de ambiente mestra** (`FRAUS_CHAVE_MESTRA`) — não
   script local, não chave impressa no boot.
3. **Dashboard: proxy no servidor Next** — a chave nunca toca o navegador.
4. **Ativação condicionada:** a exigência liga quando `FRAUS_CHAVE_MESTRA`
   existe. Sem ela, a API roda aberta como hoje (uso local), com aviso
   explícito no boot.

## A) Dois tipos de chave, papéis distintos

| chave | prefixo | autoriza | gerenciada por |
|---|---|---|---|
| de **fonte** (existe) | `frs_` | só `POST /ingestao` | chave mestra |
| de **acesso** (nova) | `fra_` | todo o resto da API | chave mestra |
| **mestra** (env) | — | tudo, inclusive gerenciar chaves | o operador do host |

- A chave de acesso segue o desenho do `credencial.py`: segredo de 32 bytes,
  hash SHA-256 no banco, mostrada **uma única vez**, dica de 4 caracteres,
  revogável. Formato `fra_<id>_<segredo>` — o id localiza, o hash autoriza.
- Tabela nova `chaves_acesso`: `id`, `nome` (rótulo dado na criação, ex.
  "dashboard Vercel"), `dica`, `chave_hash`, `criada_em`.
- Rotas de gerenciamento (exigem a **mestra**, nunca uma chave de acesso):
  - `POST /acesso/chaves` `{nome}` → 201 com a chave em claro, uma vez;
  - `GET /acesso/chaves` → lista (id, nome, dica, criada_em — nunca hash);
  - `DELETE /acesso/chaves/{id}` → 204, revogação imediata.
- `POST /integracoes/fontes/{id}/chave` e o `DELETE` correspondente passam a
  exigir a mestra — hoje são o buraco: quem alcança a URL gera credencial
  para si.

## B) Ativação e comportamento

- `FRAUS_CHAVE_MESTRA` ausente → API aberta, boot imprime aviso ("API sem
  autenticação — uso local; defina FRAUS_CHAVE_MESTRA para exigir chave").
- Presente → dependency global: **todas** as rotas exigem
  `Authorization: Bearer <chave>` onde `<chave>` é a mestra (comparada em
  tempo constante) ou uma chave de acesso válida.
- Exceção única: `POST /ingestao` continua regida **só** pela chave de fonte —
  uma credencial por rota; exigir duas quebraria todo integrador já configurado
  sem comprar segurança (a rota só escreve, não lê).
- Recusa: 401 com `WWW-Authenticate: Bearer` e a mensagem uniforme
  `"chave invalida"` para malformada, inexistente e revogada — mesmo padrão já
  documentado em `_fonte_autorizada`. Mestra errada é indistinguível de chave
  de acesso errada, de propósito.

## C) Dashboard vira proxy

- `lib/api.ts` chama `/api/fraus/...` (mesma origem) em vez da API direto.
- Route handler catch-all `app/api/fraus/[...caminho]/route.ts` repassa
  método, corpo (inclusive multipart de `/analisar`), query string, status e
  content-type para `FRAUS_API_URL` (env **server-side**, padrão
  `http://localhost:8000`), anexando `Authorization: Bearer
  ${FRAUS_CHAVE_ACESSO}` quando definida.
- O handler **não** repassa o header `Authorization` vindo do navegador: a
  credencial do deploy é a do servidor, não a que o cliente mandar.
- `NEXT_PUBLIC_API_URL` morre (a URL da API deixa de ser assunto do browser).
  CORS na API permanece como defesa em profundidade, mas o caminho normal é
  servidor→servidor.
- Sem `FRAUS_CHAVE_ACESSO` definida, o proxy repassa sem header — o dev local
  contra API aberta continua funcionando com zero configuração.

## D) Erros e casos de borda

- API exigindo chave + proxy sem chave → o 401 da API atravessa o proxy e a
  dashboard mostra o estado de erro existente, nomeando o que falta
  (regra 3.6 do handoff: estado vazio nomeia o próximo passo).
- Chave de acesso revogada no meio de uma sessão → próxima chamada é 401; sem
  cache de autorização em lugar nenhum.
- `FRAUS_CHAVE_MESTRA` definida como string vazia → tratada como ausente
  (aviso no boot), nunca como "qualquer Bearer vazio autoriza".

## E) Testes

Back (TDD, `tests/test_autenticacao.py`):

1. sem env → rotas respondem como hoje (regressão zero);
2. com env → `GET /conversas` sem header é 401 com `WWW-Authenticate`;
3. mestra autentica qualquer rota;
4. chave de acesso criada via mestra autentica leitura;
5. chave de acesso **não** autoriza gerenciar chaves (403);
6. revogação: 401 na chamada seguinte;
7. `POST /ingestao` continua exigindo chave de **fonte** e recusando mestra;
8. `POST /integracoes/fontes/{id}/chave` sem mestra é 401;
9. mestra vazia = ausente;
10. listagem nunca expõe hash.

Front: `npm run build` + fumaça manual do proxy (a dashboard não tem suíte de
unit; o proxy é repasse fino e o contrato dele é coberto pelos testes da API).

## F) Documentação a atualizar

- `README.md` — a limitação "API sem autenticação" vira descrição do modelo de
  chaves; pendência P0 sai da lista.
- `docs/hospedagem.md` — o passo a passo ganha `FRAUS_CHAVE_MESTRA` e
  `FRAUS_CHAVE_ACESSO`/`FRAUS_API_URL` no lado da Vercel.
- `docs/handoff.md` — estado.
- `Dockerfile`/exemplos — mencionar a variável.

## Fora de escopo (declarado)

- Login com usuário/senha, sessões, cookies.
- Escopos por chave (leitura vs escrita) — toda chave de acesso vê tudo.
- Rate limiting e auditoria de acesso.
