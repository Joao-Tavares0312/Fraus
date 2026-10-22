# Integração com o Tars

Os projetos continuam independentes. O Tars é o **produtor** das conversas e o
Fraus é o **consumidor** analítico; nenhum acessa o banco ou importa código do
outro. O único contrato entre os dois é `POST /ingestao`, a mesma rota que
qualquer sistema externo usa.

Em produção desde 19/10/2026 (Fraus #97 e #98; Tars #28, #29 e #30).

## Conectar, em dois passos

1. **No Fraus**, menu da conta → **Integrações** → cartão **TARS** →
   **Conectar o TARS**. A tela cria a fonte de canal `tars`, gera a chave
   `frs_…` (mostrada **uma única vez**) e mostra o endereço
   `https://fraus-api.vercel.app/ingestao`.
2. **No Tars**, **Integrações → Fraus** do assistente: cole o endereço e a
   chave e clique em **Conectar e enviar**. O Tars guarda a chave cifrada (como o
   token do Zendesk) e já manda as conversas da última semana — é o teste de
   verdade, porque só o Fraus sabe se a chave vale.

Gerar chave e segredo de fonte exige conta `dev` no Fraus
(`exigir_mestra_ou_dev`, em `fraus/api/seguranca.py`). Antes de 19/10 a rota
exigia a chave mestra, que o proxy da dashboard nunca manda — o botão dava 403
para o próprio desenvolvedor. A chave de **acesso** continua só com a mestra.

## O que é um atendimento

Um chat do Telegram dura semanas; um atendimento, não. **30 minutos sem fala
encerram o atendimento**, e a próxima mensagem abre outro, com a data dela
(`dividirEmSessoes`, em `lib/integracoes/fraus-pedido.mjs` do Tars).

O id que chega ao Fraus é `tars:<instância>:<canal>:<chat>:<início>`, e o Fraus
ainda o prefixa com a fonte (`fonte:<id>:…`). O mesmo id **substitui** a versão
anterior (upsert), então reenviar nunca duplica.

O Tars poda o histórico em 40 mensagens por chat. Recalcular o id pelo primeiro
horário que sobrou criaria um atendimento novo a cada poda; por isso o id do
atendimento em curso fica guardado em `fraus_envios.sessao_id` e é herdado
enquanto a conversa não pausa 30 minutos.

## Quando o envio acontece

Depois de cada resposta gravada (`registrarResposta`/`registrarTurno`), o Tars
agenda o envio com `after()` — **nunca atrasa a resposta ao cliente**. O envio
espera **5 segundos** e só segue se nenhuma fala mais nova chegou; se chegou, o
envio da fala mais nova é que manda. Uma rajada de mensagens vira um envio só, e
a última versão do atendimento sempre chega.

> Até 19/10, 17h30, o Tars usava um freio de um envio por chat por minuto. Duas
> mensagens no mesmo minuto deixavam a última fala para o cron do dia seguinte:
> o atendimento terminava em "péssimo" e o Fraus o mostrava como neutro.

A **repescagem** manda o que falhou: o botão **Enviar conversas pendentes** e o
cron diário do Tars, que só reenviam atendimentos com fala depois do último
envio. Na 10ª falha seguida o envio desliga e o operador recebe um alerta;
salvar a conexão de novo religa.

## O pedido

```json
{
  "id": "tars:inst_x:telegram:8624457065:1792441687",
  "mensagens": [
    {"autor": "cliente", "texto": "...", "enviada_em": "2026-10-19T20:28:07.000Z"},
    {"autor": "bot", "texto": "...", "enviada_em": "2026-10-19T20:28:09.000Z"}
  ],
  "escalou_para_humano": false
}
```

- `user` vira `cliente`; `assistant` vira `bot`; resposta escrita pela equipe no
  painel vira `humano` e marca `escalou_para_humano`.
- Horário em ISO com fuso — o Fraus recusa data sem fuso (invariante 6).
- O corpo cabe no teto de 32 KB do `chamarApiSegura`: se não couber, só as
  respostas longas do bot são encurtadas; a fala do cliente nunca é cortada.
- Score, nota e categoria **nunca** vão no pedido: o Fraus deriva no servidor
  (invariante 3). O canal vem da fonte cadastrada, não do corpo.

## Privacidade — o que vale e o que falta

- O Fraus aplica a censura de PII ao texto antes de persistir.
- **O id leva o `chat_id` do Telegram em claro.** É um identificador de conta,
  não conteúdo, mas atravessa a fronteira. Trocar por um hash estável (com sal
  da instância) é a próxima mudança de privacidade; como o id novo não colide
  com o antigo, a troca pede remover antes os atendimentos do Tars no Fraus.
- Os botões "Resolveu / Não resolveu" do Tars ainda **não** são enviados como
  `feedback_declarado`.

## Limpeza

Atendimentos que nunca deveriam ter entrado (o datado de 2243, duplicatas de
teste, o chat inteiro no formato anterior a 19/10) saem pelo botão **Remover
atendimento**, no detalhe do atendimento — só conta `dev`, com confirmação, e
registrado na auditoria (`DELETE /conversas/{id}`).
