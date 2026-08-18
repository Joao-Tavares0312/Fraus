# Subir a API pela dashboard — modo local

Data: 2026-08-18

## O problema

Com a API fora do ar, **toda** tela da dashboard mostra o mesmo erro seco. O
indicador da barra lateral diz "API fora do ar", e é só: quem está na frente do
produto precisa sair da interface, achar o terminal e lembrar do comando.

Na banca isso é um risco concreto — um `uv run uvicorn` esquecido vira uma
apresentação que começa com tela de erro.

## O que se constrói

1. Um **aviso de API fora do ar** no topo de qualquer tela, com o comando
   pronto e um botão de tentar de novo.
2. Nesse aviso, quando — e **somente** quando — o modo local estiver
   habilitado, um botão **Iniciar API** que sobe `uv run uvicorn
   fraus.api.main:app` como processo filho do servidor Next, mostra "subindo…"
   e libera a tela quando `GET /saude` responde.

## A rota que executa processo, e como ela é contida

Uma rota HTTP que dispara um comando é execução remota de código. Ela existe
sob quatro travas simultâneas:

1. **Desligada por padrão.** Só existe com `FRAUS_MODO_LOCAL=1` no ambiente do
   servidor Next. Sem a variável, a rota responde **404** — não 403: quem não
   deveria saber que ela existe não descobre que existe. Num deploy (Vercel e
   afins) ela simplesmente não está lá, e o botão não é desenhado.
2. **Comando fixo, zero entrada do cliente.** O argv é literal no código-fonte
   (`uv run uvicorn fraus.api.main:app --host 127.0.0.1 --port <porta>`).
   Nada do corpo, da query ou dos cabeçalhos entra nele — não há string de
   comando a injetar, e o `spawn` roda sem shell.
3. **Uma instância.** Antes de subir, a rota consulta `GET /saude`; se a API
   responde, devolve 200 "já está no ar" sem spawnar. Um processo já iniciado
   por ela é lembrado e não é duplicado.
4. **Escuta só em `127.0.0.1`.** A API subida pelo botão não aceita conexão de
   fora da máquina, mesmo que o `FRAUS_API_URL` aponte para outro lugar.

O que **não** é feito: derrubar a API pela web (matar processo é irreversível e
não tem contrapartida), escolher comando/porta/argumentos pela interface, e
subir qualquer coisa quando `FRAUS_API_URL` aponta para um host que não é
local — se a API mora em outra máquina, o botão não tem o que iniciar e não
aparece.

## O estado da saúde deixa de ser duplicado

Hoje `EstadoSaude` faz o próprio polling de 20s. Com o aviso precisando do
mesmo dado, dois pollings independentes discordariam entre si por até 20
segundos — o indicador dizendo "no ar" com o aviso ainda na tela.

A saúde passa a viver num **provider** no layout: uma consulta, dois
consumidores. O provider também expõe `reconsultar()`, que o botão "tentar de
novo" e o fim do "subindo…" chamam.

## O contrato da rota

`GET /api/fraus/iniciar` → `{"disponivel": bool, "motivo": string|null}`
Se o modo local está habilitado E a API é local. `motivo` explica a recusa
("modo local desligado", "a API não é local: http://…").

`POST /api/fraus/iniciar` →
- **200** `{"estado": "ja-no-ar"}` — nada foi iniciado.
- **202** `{"estado": "subindo", "pid": 1234}` — o processo nasceu. A tela
  então faz polling de `GET /saude` até responder, com teto de 90 s (a API real
  carrega três BERTimbau do disco).
- **404** — modo local desligado.
- **409** `{"detail": "…"}` — já há um processo subindo.
- **500** `{"detail": "…"}` — o `spawn` falhou (o `uv` não está no PATH, por
  exemplo), com a mensagem do erro.

O `stdout`/`stderr` do processo vão para `dashboard/.fraus-api.log`, e a
mensagem de falha aponta esse arquivo — sem ele, "não subiu" seria um beco sem
saída.

## O aviso

Client component no layout, acima do conteúdo, visível quando a saúde está
`fora-do-ar`:

- **Sem modo local:** o comando `uv run uvicorn fraus.api.main:app` num
  `<code>` com botão de copiar, e "Tentar de novo".
- **Com modo local:** o mesmo, mais **Iniciar API**. Durante a subida, o botão
  vira "subindo… (Ns)" e desabilita; ao responder, o aviso some e a tela
  recarrega (`router.refresh()`).
- **Se estourar o teto de 90 s:** o aviso passa a mostrar o caminho do log e a
  instrução de olhar o terminal. Nunca "falhou" sem dizer onde olhar.

## Testes

- **Rota (vitest ou script node):** a suíte do front não existe hoje, e criá-la
  não é escopo desta feature. A verificação é manual e roteirizada: sem
  `FRAUS_MODO_LOCAL` a rota é 404; com ela e a API no ar, 200 `ja-no-ar`; com
  ela e a API fora, 202 e a API responde em seguida; segunda chamada durante a
  subida, 409.
- **API (pytest):** nada muda no back-end. A suíte continua em 336 e serve de
  regressão.

## Critério de pronto

- Com a API fora e `FRAUS_MODO_LOCAL=1`: abrir qualquer tela, clicar em
  Iniciar API, e a tela carregar sozinha quando a API sobe.
- Sem a variável: o aviso aparece com o comando, e `POST /api/fraus/iniciar`
  responde 404.
- `npm run build` verde e `uv run pytest -q` em 336.
- README com a variável documentada e a ressalva de não habilitá-la em deploy.
