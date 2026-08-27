# Webhook de integração — design

**Data:** 27/08/2026
**Estado:** aprovado, aguardando plano de implementação

---

## 1. O problema

A tela de Integrações oferece cadastrar uma fonte do tipo **Webhook**. O tipo
não faz nada. Não há um `if tipo == "webhook"` em lugar nenhum do código: uma
fonte webhook e uma fonte CSV são bit a bit a mesma coisa — as duas ganham
chave `frs_` e as duas usam `POST /ingestao`. O que a tela oferece é uma
promessa.

Junto dela, três defeitos que só aparecem quando alguém tenta integrar de
verdade:

1. **`variavel_segredo` é enfeite.** É lido em exatamente um lugar
   (`fraus/api/rotas/integracoes.py:33`), para pintar o rótulo "variável
   definida". Nunca entra num HMAC, nunca compara nada. O campo tem aparência
   de segurança e não é segurança.

2. **Nenhuma plataforma real consegue chamar `POST /ingestao`.** Ela exige
   `Authorization: Bearer frs_...`, e o padrão de mercado é URL única por
   endpoint com assinatura sobre o corpo — não header customizado.

3. **Não há registro de entrega.** O histórico da tela cobre só importação de
   CSV. Uma chamada de webhook recusada não deixa rastro em lugar nenhum, e
   falha silenciosa é o modo de falha número um dessa integração.

## 2. O que foi decidido, e o que foi recusado

### 2.1 Contrato publicado, não adapter por plataforma

O Fraus **publica o formato dele** e a tela mostra o contrato com exemplo
copiável. Quem integra manda no formato do Fraus, direto ou com um
transformador (n8n, Zapier, uma função própria) no meio.

Recusado: uma família de adapters (`zendesk.py`, `meta.py`, `twilio.py`)
escolhida pelo campo `tipo`. Ficaria plug-and-play para as plataformas
suportadas e viraria dívida permanente — cada API que muda de formato quebra
em silêncio, e não há conta em nenhuma delas para testar contra.

Recusado também: mapeamento declarado pelo operador (JSONPath por campo).
Genérico de verdade, e o mais caro de todos: motor de mapeamento, interface de
mapeamento, validação, e um estado de erro novo para quando o caminho não bate.

Consequência honesta, que a tela precisa dizer: **o Fraus recebe eventos
assinados num contrato documentado.** Não é plug-and-play com nenhuma
plataforma nomeada.

### 2.2 Standard Webhooks, não formato próprio

Os três cabeçalhos vêm da [especificação Standard
Webhooks](https://github.com/standard-webhooks/standard-webhooks/blob/main/spec/standard-webhooks.md),
que é onde o mercado convergiu:

| Cabeçalho | Papel |
|---|---|
| `webhook-id` | identificador do evento, **estável entre reentregas** — é a chave de idempotência |
| `webhook-timestamp` | epoch em segundos; é o que fecha a janela contra replay |
| `webhook-signature` | `v1,<base64>` do HMAC-SHA256 de `{id}.{timestamp}.{corpo}` |

Inventar um formato próprio custaria o mesmo trabalho e entregaria menos: com
o padrão, quem integra pode usar uma biblioteca de prateleira em vez de ler a
nossa documentação.

### 2.3 O segredo mora na variável de ambiente que a fonte já nomeia

HMAC exige o segredo **em claro** no servidor — ele precisa recomputar a
assinatura. Isso bate de frente com a decisão do `credencial.py`, que guarda
só o hash justamente para que um `fraus.db` vazado não leve credencial junto.

A saída reusa a estrutura que já existe: o banco continua guardando **o nome**
da variável, e o valor mora no ambiente da máquina onde a API roda.

```
banco:     variavel_segredo = "FRAUS_WEBHOOK_ZENDESK"
ambiente:  FRAUS_WEBHOOK_ZENDESK=whsec_a3f...
conferência: os.environ[fonte["variavel_segredo"]]
```

O campo morto ganha função real, e o rótulo "variável definida" passa a
significar uma coisa verificável: *esta fonte consegue conferir assinatura*.

Recusado: segredo cifrado no banco com chave mestra do ambiente (traria uma
dependência de criptografia nova e um mecanismo de rotação, contra o "nada de
dependência nova sem motivo declarado" do CLAUDE.md) e segredo em claro no
banco (contradiz frontalmente o que `credencial.py` e a própria legenda da tela
afirmam em voz alta hoje).

**Limite declarado:** HMAC prova origem e integridade, não confidencialidade. O
corpo trafega legível para quem estiver no caminho. Quem publica a API atrás do
túnel Cloudflare (`docs/hospedagem.md`) tem TLS terminado ali; isso precisa
estar escrito, não presumido.

## 3. A rota

```
POST /integracoes/webhook/{fonte_id}
```

Uma URL por fonte, que é o que plataforma nenhuma dispensa.

### 3.1 O corpo é lido cru

O corpo é lido em bytes (`await request.body()`), **nunca por um modelo
Pydantic no parâmetro da função**. HMAC é byte-exato: deixar o FastAPI
desserializar e depois re-serializar para conferir muda a assinatura por
reordenação de chave ou por diferença de espaço. A validação Pydantic acontece
depois, sobre os mesmos bytes, e só depois de a assinatura passar.

### 3.2 Ordem de porteiro

Identidade, depois autoridade, depois parse. Nada de desserializar JSON, tocar
no banco ou pontuar antes de a assinatura passar.

| # | Confere | Falha | Veredito registrado |
|---|---|---|---|
| 1 | a fonte existe | 404 | *(nenhum — sem fonte, não há de quem registrar)* |
| 2 | `variavel_segredo` nomeado **e** presente no ambiente | **503**, nomeando a variável ausente | `sem_segredo` |
| 3 | os três cabeçalhos presentes e bem formados | 400 | `corpo_invalido` |
| 4 | `webhook-timestamp` dentro de ±5 min | 400 | `fora_da_janela` |
| 5 | HMAC-SHA256 confere por `hmac.compare_digest` | 401 | `assinatura` |
| 6 | a fonte está ativa | 403 | `fonte_inativa` |
| 7 | `webhook-id` inédito — consultado em `entregas_webhook` para aquela fonte | **200** | `duplicada` |
| 8 | o corpo bate `PedidoIngestao` | 400 | `corpo_invalido` |
| — | aceito | 201 | `aceita` |

Dois passos parecem errados e não são:

**O passo 2 é 503, não 401.** Variável ausente é defeito da máquina que
hospeda, não da requisição. Responder 401 mandaria quem integra caçar um
problema que não é dele — e o corpo do 503 nomeia a variável que falta, porque
quem opera a máquina precisa saber qual.

**O passo 7 é 200, não erro.** O Standard Webhooks manda a plataforma retentar
diante de qualquer resposta fora da faixa 2xx. Responder erro a uma reentrega
legítima colocaria a integração em laço infinito por conta própria. Reentrega
é o comportamento correto do remetente; o receptor responde "já tenho esse" e
encerra.

O passo 6 vem **depois** da assinatura de propósito: informar que a fonte está
desativada a quem não provou identidade conta a um desconhecido o estado
interno do sistema.

### 3.3 A rota precisa entrar em `ISENTAS`

`fraus/api/seguranca.py:37` lista as rotas que o middleware de chave de acesso
não cobre. **A rota nova precisa entrar nessa lista**, pelo mesmo motivo que
`/ingestao` está nela: ela tem credencial própria, e a plataforma externa não
tem — nem pode ter — uma chave de acesso `fra_`.

Sem isso, o defeito é silencioso e só aparece em produção: com
`FRAUS_CHAVE_MESTRA` definida, toda chamada de webhook levaria 401 do
middleware antes de a assinatura ser sequer olhada, e o log de entregas ficaria
vazio — dizendo "não chegou nada" enquanto a plataforma recebe 401 em cada
tentativa.

A comparação usa `rstrip("/")`, como a lista já faz, para que a URL cadastrada
com barra final não caia no 401 do middleware.

### 3.4 O miolo é compartilhado com `POST /ingestao`

Montar a `Conversa`, ler a curadoria uma vez, pontuar, derivar a categoria e
gravar já existe em `fraus/api/rotas/ingestao.py`. Esse trecho sai para uma
função compartilhada, chamada pelas duas rotas.

Não é arrumação de estilo: duas cópias da regra de derivação divergem, e a
invariante 3 do CLAUDE.md nasceu exatamente dessa divergência. Uma das duas
cópias envelheceria, e seria a que ninguém olha.

Continuam valendo, nas duas rotas: o canal vem da **fonte cadastrada**, e
`score`, `nota` e `categoria` são derivados no servidor e ignorados se vierem
no corpo.

## 4. O segredo, na prática

```
POST /integracoes/fontes/{fonte_id}/segredo
```

Gera um `whsec_...` com o mesmo CSPRNG do `credencial.py`, devolve **em claro
uma única vez** — pelo `ChaveEmClaro`, o mesmo componente da chave `frs_` e da
mestra — e **não grava nada**. O banco continua sabendo apenas o nome da
variável.

Privilégio da mestra (`exigir_mestra`), como as demais rotas de credencial:
uma chave que emite outra chave não seria um posto menor.

O fluxo do operador tem três passos, e a tela precisa mostrar os três juntos:
gerar o segredo, pôr o valor na variável de ambiente da máquina da API, entregar
a cópia à plataforma.

## 5. O registro de entregas

Tabela nova:

```sql
CREATE TABLE entregas_webhook (
  id          INTEGER PRIMARY KEY,
  fonte_id    INTEGER NOT NULL,
  webhook_id  TEXT,
  recebida_em TEXT NOT NULL,
  veredito    TEXT NOT NULL,
  motivo      TEXT,
  conversa_id TEXT
);
```

**O corpo nunca é guardado.** Seria PII de cliente real parada em disco sem
propósito — e o propósito de depurar é servido pelo veredito e pelo motivo.

**Toda tentativa vira linha, aceita e recusada.** Guardar só as recusas parece
econômico e quebra o diagnóstico central: sem as aceitas, "não chegou nada" e
"chegou e foi tudo recusado" viram a mesma tela vazia.

**Poda no insert: 200 entregas por fonte, as mais antigas caem.** Registrar
recusa de assinatura é exatamente o que o operador precisa ver — alguém está
batendo com o segredo errado — e é também como um atacante enche o SQLite. A
poda é o que permite manter a primeira propriedade sem pagar a segunda.

**A poda é também a memória do dedupe, e isso tem um custo.** O passo 7 consulta
esta tabela, então uma fonte que receba 200 recusas seguidas perde a lembrança
das entregas aceitas antes delas — e uma reentrega antiga passaria a ser
tratada como nova. O efeito prático é limitado: a conversa é gravada com
`INSERT OR REPLACE` pelo id dela (`fraus/db.py:159`), então reprocessar não
duplica atendimento, só o repontua. É por isso que a poda pode ser simples;
não é por acidente que ela não quebra nada.

Leitura: `GET /integracoes/fontes/{fonte_id}/entregas`, mais recente primeiro.

## 6. A tela

Hoje são três painéis empilhados, cada um com legenda longa e rodapé longo. O
webhook somaria quatro blocos por fonte, e a tabela de fontes já é gorda.

O layout passa a ser **mestre-detalhe**:

```
+----------------+---------------------------------+
| FONTES      [+]| Suporte — Zendesk      [ativa]  |
|                |---------------------------------|
| >Suporte-Zend. | Chave frs_ ...abcd     [gerar]  |
|  WhatsApp      | URL   /webhook/3      [copiar]  |
|  Loja CSV      | Segredo FRAUS_WH_ZEN   ok       |
|                |                                 |
|                | Contrato       [curl] [copiar]  |
|                | Entregas  18 ok / 2 assinatura  |
|                |  11:42 aceita     conv-8812     |
|                |  11:39 assinatura inválida      |
+----------------+---------------------------------+
| Importar CSV: [arquivo v] [importar]  histórico   |
+---------------------------------------------------+
```

A lista de fontes vira coluna estreita — nome, canal, estado. Escolher uma abre
à direita tudo que é dela: chave, URL, segredo, contrato copiável e as últimas
entregas. A fonte número doze não piora a tela.

**A prosa de honestidade não é cortada, é realocada.** Ela sai dos três rodapés
empilhados e vai para o ponto onde é lida, ao lado do controle que ela explica.
Regra 3.7 do handoff: ressalva repetida vira ruído — e ressalva empilhada em
rodapé é ressalva não lida. Qualquer texto do lote que o João declarou
intocável fica onde está.

A importação de CSV desce para uma faixa própria no rodapé da tela: ela é uma
ação de arquivo local, não uma integração de rede, e hoje ocupa o topo por
ordem histórica.

## 7. O que fica de fora, de propósito

**Handshake de verificação de URL** (`hub.challenge` do Meta,
`url_verification` do Slack). Só faz sentido junto de um adapter da plataforma,
e a seção 2.1 recusou adapters.

**Fila de retry própria.** A plataforma remetente já retenta — o Standard
Webhooks assume isso e é por isso que `webhook-id` é estável entre tentativas.
Uma fila nossa duplicaria a responsabilidade e criaria um segundo relógio para
manter.

**Assinatura de saída.** O Fraus recebe webhook; não emite. Emitir é outro
projeto.

## 8. Testes

Cada linha da tabela do passo 3.2 é um teste, mais:

- assinatura válida é aceita e grava a conversa;
- **corpo alterado em um único byte é recusado** — é o teste que prova que a
  conferência é sobre os bytes crus, e o único que pega a regressão de
  re-serialização;
- `webhook-id` repetido responde 200 e **não** grava uma segunda conversa;
- `score`, `nota` e `categoria` vindos no corpo são ignorados (invariante 3);
- o canal gravado é o da fonte, não o do corpo;
- com `FRAUS_CHAVE_MESTRA` definida, a rota responde sem exigir `fra_`
  (regressão de `ISENTAS`, seção 3.3);
- a poda mantém 200 entregas por fonte e descarta as mais antigas;
- o corpo da requisição não aparece em nenhuma coluna de `entregas_webhook`.

## 9. Referências

- [Standard Webhooks — especificação](https://github.com/standard-webhooks/standard-webhooks/blob/main/spec/standard-webhooks.md)
- [webhooks.fyi — esforços de padronização](https://webhooks.fyi/learn-more/standards)
- [Hooklistener — fundamentos de segurança de webhook](https://www.hooklistener.com/learn/webhook-security-fundamentals)
