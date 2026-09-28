# Integração com o Tars

Os projetos continuam independentes. O Tars é o **produtor** das conversas e o
Fraus é o **consumidor** analítico; nenhum acessa o banco ou importa código do
outro.

## Contrato

1. No Fraus, crie uma fonte do tipo `webhook` e gere sua chave `frs_...`.
2. No servidor do Tars, configure:

   ```env
   FRAUS_API_URL=https://api-fraus.exemplo.com
   FRAUS_FONTE_CHAVE=frs_...
   ```

3. Autenticado no Tars, chame:

   ```http
   POST /api/integracoes/fraus/sincronizar
   Content-Type: application/json

   {"instancia_id":"...","desde":"2026-09-01T00:00:00Z","limite":100}
   ```

O Tars agrupa mensagens por instância, canal e chat, envia timestamps e informa
se houve handoff. Quando existe “Resolveu/Não resolveu”, o rótulo segue como
`feedback_declarado`; ele **não altera a nota**, apenas mede concordância com a
inferência em `GET /indicadores`.

## Idempotência e privacidade

O ID externo usa `instancia:canal:sha256(chat)`: o identificador do visitante
não atravessa a fronteira em claro. No Fraus ele recebe ainda o namespace da
fonte (`fonte:<id>:...`), portanto fontes diferentes nunca se sobrescrevem.
Repetir a sincronização atualiza o mesmo atendimento. Antes de persistir, o
Fraus aplica sua censura de PII ao texto e ao comentário do feedback.

A sincronização é explícita e fica fora do caminho de resposta do chatbot: se o
Fraus estiver indisponível, o atendimento do Tars continua funcionando. A rota
retorna `207` quando apenas parte do lote falha, com o resultado por conversa.

## Automação opcional

Um agendador pode chamar a rota com uma janela sobreposta (por exemplo, as
últimas 24 horas). Como o envio é idempotente, a sobreposição é preferível a
perder conversas na fronteira entre duas execuções.
