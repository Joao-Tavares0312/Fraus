# Integração com o Tars

Os projetos continuam independentes. O Tars é o **produtor** das conversas e o
Fraus é o **consumidor** analítico; nenhum acessa o banco ou importa código do
outro. O único contrato entre os dois é `POST /ingestao`, a mesma rota que
qualquer sistema externo usa.

Revisão do contrato no código em **16/11/2026**, incluindo o produtor Tars.
A publicação de 19/10/2026 consta do registro histórico desta integração
(Fraus #97 e #98; Tars #28, #29 e #30); **não foi revalidada nesta revisão**.

## Conectar, em dois passos

1. **No Fraus**, menu da conta → **Integrações** → cartão **TARS** →
   **Conectar o TARS**. A tela cria ou reutiliza a fonte de canal `tars` e
   gera a chave `frs_…`, mostrada **uma única vez**. Copie o **Endereço no
   TARS** exibido: ele usa a base pública da API desta instalação, com
   `/ingestao`, não o proxy da dashboard. Se houver mais de uma fonte `tars`,
   o conector usa a mais antiga.
2. **No Tars**, **Integrações → Fraus** do assistente: cole o endereço e a
   chave e clique em **Conectar e enviar** (ou **Salvar e enviar** numa conexão
   existente). O Tars guarda a chave cifrada e solicita o envio dos chats
   pendentes da última semana. Confira o resultado do envio; salvar a
   configuração sozinho não prova que havia conversas nem que foram recebidas.

O conector exige conta `dev` no Fraus; proprietário ou gestor de equipe não
recebe esse papel automaticamente. No Tars, configurar a integração exige
permissão administrativa sobre a instância.

Se perder a chave, **Gerar nova chave** invalida a anterior: atualize-a no Tars.
O texto **Conectado — chave terminando em…** no Fraus indica chave cadastrada,
não uma verificação ponta a ponta. A fonte precisa estar ativa e os modelos
compatíveis disponíveis para a ingestão pontuar.
Uma resposta de `/saude` não confirma que `POST /ingestao` está disponível nem
que os modelos foram carregados. Confira o resultado de um envio autorizado
e o atendimento recebido; não use a saúde como prova de integração concluída.

## O que é um atendimento

Um chat do Telegram dura semanas; um atendimento, não. Uma pausa de **30 minutos
ou mais entre falas** separa os atendimentos; a próxima mensagem abre outro, com
a data dela (`dividirEmSessoes`, em `lib/integracoes/fraus-pedido.mjs` do Tars).

O id que chega ao Fraus é `tars:v2:<instância>:<canal>:<chat>:<início>`, e o
Fraus ainda o prefixa com a fonte (`fonte:<id>:…`). Desde o Tars #33
(19/11/2026), `<chat>` é um HMAC-SHA256 de 32 caracteres hexadecimais do
`chat_id`, com segredo derivado da chave do cofre do Tars (`chatAnonimo`); o
número do Telegram não sai do Tars. Girar essa chave muda os ids e cria
atendimentos novos. **A mesma fonte e o mesmo id** atualizam o registro
anterior; um id diferente cria outro atendimento. Esse contrato de reenvio é
coberto por `tests/test_ingestao_tars.py`, com motor falso: o teste verifica
persistência e deduplicação, não a qualidade da inferência.

O produtor conserva o id do atendimento em curso em `fraus_envios.sessao_id`
e o herda enquanto a conversa não pausa 30 minutos. Isso evita criar outro id
quando o histórico disponível perde o começo, e foi o que segurou a troca de
formato: o atendimento em curso no deploy do #33 manteve o id antigo; só o
próximo, depois de uma pausa, nasceu `v2`. A integração envia o histórico
disponível, não garante que todo o chat original atravesse a fronteira.

## Quando o envio acontece

Depois de uma resposta gravada, o Tars agenda o envio com `after()`, fora da
resposta ao cliente. Espera **5 segundos** e só envia se aquela ainda for a fala
mais recente; caso contrário, o envio mais novo assume a tentativa. Isso reduz
envios numa rajada, **não garante entrega** se houver falha.

A **repescagem** tenta enviar o que ficou pendente: **Enviar conversas
pendentes** e a rotina de sondas do Tars consultam chats com fala posterior ao
último envio. As janelas e os limites diferem: o botão usa, por padrão, sete
dias e até 50 chats; a rotina consulta um dia e até 30. A frequência configurada
no ambiente não foi conferida. Na **10ª falha seguida**, o código desativa o
envio e alerta o operador; salvar a conexão de novo a reativa.

O envio espera a resposta do Fraus por **30 segundos** (eram 10 até
20/11/2026). `POST /ingestao` cai na função que carrega os três modelos; fria,
ela levou cerca de 11 s só para ficar pronta, medidos em produção nesse dia.
Como o envio não tem retentativa, o primeiro atendimento depois de um tempo
parado estourava o prazo e só voltava na repescagem diária. Essa relação é
inferida das duas medidas; não há registro de chegada anterior a 20/11 que a
comprove caso a caso.

No Fraus, cada atendimento gravado passa a ter `recebida_em`: a hora em que o
servidor o gravou ou viu o conteúdo mudar. Reenvio idêntico não mexe nela, e
repontuar também não. A dashboard aberta pergunta a `GET /conversas/assinatura`
a cada 15 segundos, só com a aba visível, e relê a tela quando a resposta muda;
em **Atendimentos**, o que chegou depois da última visita daquele navegador
leva o selo **novo**. Atendimento gravado antes de 20/11/2026 não tem essa
hora e nunca é marcado.

Confira último envio, último erro e o resumo da tentativa no Tars. No Fraus,
procure o canal `tars` em **Atendimentos**, no período das conversas. O bloco
**Entregas** das fontes registra webhook assinado, não chamadas a `/ingestao`.

## O pedido

```json
{
  "id": "tars:v2:inst_exemplo:telegram:0f1e2d3c4b5a69788796a5b4c3d2e1f0:1792441687",
  "mensagens": [
    {"autor": "cliente", "texto": "...", "enviada_em": "2026-10-19T20:28:07.000Z"},
    {"autor": "bot", "texto": "...", "enviada_em": "2026-10-19T20:28:09.000Z"}
  ],
  "escalou_para_humano": false,
  "feedback_declarado": -1,
  "comentario_feedback": "..."
}
```

O id acima é ilustrativo. `feedback_declarado` e `comentario_feedback` só
existem quando o cliente votou numa resposta daquele atendimento. No envio
direto, a chave da fonte vai em `Authorization: Bearer <chave-da-fonte>`.

- `user` vira `cliente`; resposta com identificador de agente vira `humano` e
  marca `escalou_para_humano`; as demais respostas viram `bot`.
- Horário em ISO com fuso — o Fraus recusa data sem fuso. O encerramento, se
  informado, não pode anteceder a última mensagem.
- O produtor mira **30 KiB**, abaixo do teto de 32 KB de seu cliente HTTP.
  Primeiro encurta respostas longas que não são do cliente; se ainda exceder,
  remove mensagens mais antigas, inclusive do cliente. Portanto, não há
  garantia de transcrição integral. Uma única mensagem que ainda ultrapasse o
  teto pode impedir o envio.
- Score, nota e categoria **não são entradas** do contrato: o Fraus deriva no
  servidor e ignora esses campos extras. O canal vem da fonte cadastrada.
- A API aceita id de até 256 caracteres e de 1 a 500 mensagens. Uma fonte
  desativada recebe **403**; o limite de vazão é por fonte e pode retornar
  **429**. O sucesso retorna **201**, inclusive quando atualiza o mesmo id.

## Privacidade — o que vale e o que falta

- O Fraus censura padrões de PII no texto das mensagens antes de inferir e
  persistir. Isso reduz exposição; não é garantia de anonimização completa nem
  autorização para transmitir dados.
- **Ids anteriores a 19/11/2026 contêm o `chat_id` em claro** e continuam
  gravados assim: não foram renomeados nem apagados, porque trocar o id de um
  registro existente cria outro atendimento. É limitação declarada. Quem
  decidir removê-los usa **Remover atendimento** (abaixo), um a um, auditado.

### Voto do cliente: ciclo fechado no código

O contrato de `POST /ingestao` aceita `feedback_declarado: 1` ou `-1`, ou
ausência (`null`), e `comentario_feedback` opcional de até 1.000 caracteres.
O modelo canônico e o registro guardam esse dado separado: ele **não muda o
score**. Não transforme ausência de voto em zero nem em resposta negativa.

Desde o Tars #33, os botões **Resolveu / Não resolveu** (Telegram e webchat)
entram no pedido. O Tars escolhe o voto mais recente dado numa resposta do
atendimento enviado (`votoDaSessao`); voto numa resposta de atendimento
anterior não é reenviado. Votar ou comentar agenda um envio, sem esperar a
próxima fala. Como o Fraus **substitui o payload inteiro** a cada envio, o Tars
relê o voto do próprio banco em todo envio: um reenvio sem o campo apagaria o
voto aqui, e `tests/test_ingestao_tars.py` fixa esse contrato.

`GET /indicadores` retorna `feedback_declarado_total` e
`concordancia_com_feedback`. O denominador é o número de conversas do recorte
que têm **feedback e score**; não é todo voto recebido. A concordância conta
`1` junto de promotor ou `-1` junto de detrator pelas faixas vigentes; sem pares,
a taxa é `null`. Um neutro não é contado como concordante.

A dashboard mostra a concordância numa linha **Voto do cliente** abaixo dos
quatro indicadores, com o denominador, e o voto e o comentário no resumo do
atendimento. Sem votos no período, a linha nomeia a ausência; nunca exibe 0%.
“Resolveu” é uma resposta de resolução, não uma nota NPS declarada nem prova
causal de satisfação, e poucos votos não validam o modelo com clientes reais.
Completar esse fluxo não alterou os pesos; modelos permanecem congelados por
decisão de 16/11/2026.

## Limpeza

Para dados que não deveriam ter entrado, **Remover atendimento** no detalhe
exige `dev` e **Confirmar remoção**. A ação sai dos indicadores, não tem desfazer
e é auditada (`DELETE /conversas/{id}`). Revise autorização e consequências
antes de remover; trocar o identificador da integração não autoriza apagar o
histórico.

## Fontes desta revisão

No Fraus: `dashboard/components/integracoes/ConectarTars.tsx`,
`dashboard/lib/tars.ts`, `fraus/api/rotas/ingestao.py`,
`fraus/api/esquemas.py`, `fraus/modelos.py`, `fraus/api/registro.py`,
`fraus/api/rotas/indicadores.py` e `tests/test_ingestao_tars.py`.
No produtor Tars: `lib/integracoes/fraus-pedido.mjs`,
`lib/integracoes/fraus.ts`, `lib/db/integracoes-fraus.ts`, `lib/cripto.ts`,
`app/api/telegram/[instanciaId]/route.ts`, `app/api/webchat/[instanciaId]/route.ts`,
`components/telas/IntegracaoFraus.tsx`, `app/api/integracoes/fraus/route.ts` e
`app/api/cron/sondas/route.ts`. A leitura do código não executou envios nem
conferiu configuração ou publicação dos dois serviços.
