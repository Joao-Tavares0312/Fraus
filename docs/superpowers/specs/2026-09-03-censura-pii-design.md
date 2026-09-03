# Censura de dados sensíveis (PII) antes de gravar e antes de inferir

Data: 2026-09-03
Status: aprovado para plano de implementação
Parte de uma sessão única com `2026-09-03-incongruencia-ironia-design.md` e
`2026-09-03-leitura-de-estilo-design.md`.

## Contexto e motivação

Hoje nenhum dado sensível é detectado ou mascarado em lugar nenhum do
pipeline. O texto do cliente entra cru em `Conversa`/`Mensagem`, é gravado
assim no banco e é o que os sete sinais leem. Em sessão anterior (24/08/2026)
o banco de demonstração acabou com 3 conversas reais contendo nome, e-mail e
valor de dívida — risco concreto, não hipotético.

Prioridade declarada: mascarar **antes de gravar** (o texto original nunca
chega ao disco) e, por decorrência, **antes de qualquer inferência** (nenhum
classificador vê o CPF cru). Escopo dos dados: CPF, e-mail, telefone,
número de cartão, endereço.

## Arquitetura

Novo módulo `fraus/seguranca/pii.py` (pasta nova, paralela a `fraus/sinais/`
e `fraus/ingest/` — não é um sinal de satisfação nem um adapter de entrada,
é uma etapa de higienização). Função pública:

```python
def censurar_pii(texto: str) -> str:
    """Mascara CPF, e-mail, telefone, cartao e endereco. Deterministico."""
```

Detecção por família, cada uma com sua própria função privada testável:

- **CPF**: regex de formato (`\d{3}\.?\d{3}\.?\d{3}-?\d{2}`) + validação do
  dígito verificador — só mascara o que É um CPF válido, não qualquer
  sequência de 11 dígitos (evita falso positivo em número de pedido/protocolo,
  o mesmo cuidado que `estilo.py` já documenta para dígito puro).
- **Cartão de crédito**: regex de formato (13-19 dígitos, com ou sem
  separador) + validação de Luhn, mesmo raciocínio de evitar falso positivo
  em número de protocolo.
- **E-mail**: regex padrão `usuario@dominio`.
- **Telefone BR**: regex para formatos com DDD (fixo e celular, com/sem
  `+55`, com/sem separador).
- **Endereço**: heurística — token de tipo de logradouro ("rua", "av",
  "avenida", "alameda", "travessa") seguido de número. Limitação
  metodológica declarada: regex de endereço tem falso-negativo alto
  (endereço sem essas palavras não é pego) e algum falso-positivo é
  aceitável aqui porque o custo de over-masking é baixo comparado ao de
  vazar um endereço real.

Cada família mascara substituindo o trecho por um marcador do tipo
`[CPF]`, `[EMAIL]`, `[TELEFONE]`, `[CARTAO]`, `[ENDERECO]` — não por asterisco
genérico, para o texto mascarado continuar informativo para leitura humana
("cliente informou [CPF] e [TELEFONE]") sem expor o valor.

## Ponto de integração

`censurar_pii` é chamado uma única vez por mensagem, no ponto mais cedo
comum às duas entradas, espelhando o padrão que `fraus/api/registro.py` já
usa para não duplicar regra entre `/ingestao` e o webhook:

- em `registrar_conversa` (`fraus/api/registro.py`), sobre `pedido.mensagens`
  antes de montar `Conversa`;
- em `fraus/ingest/csv_driver.py`, sobre o texto de cada linha antes de
  montar `Mensagem`.

Isso garante que `Conversa.mensagens` já chega mascarada em todo o resto do
sistema — sinais, banco, dashboard — sem precisar espalhar a chamada em mais
lugares. O simulador sintético (`fraus/ingest/simulador.py`) não passa por
`censurar_pii`: não gera PII real, mascarar dado sintético seria trabalho
sem função.

## Testes

TDD por família: casos positivos (CPF válido mascarado, CPF com dígito
verificador errado NÃO mascarado — é só uma sequência de dígitos, não um
CPF), negativos (número de pedido de 11 dígitos não confundido com CPF),
mistura de mais de um tipo na mesma mensagem, mensagem sem PII inalterada.

Teste de integração: `registrar_conversa` e o driver de CSV gravam o texto
JÁ mascarado — consulta direta ao banco depois de uma chamada com CPF/e-mail
no corpo não deve conter o valor original em nenhuma coluna.

## Limitação metodológica a declarar

Detecção de endereço por regex tem cobertura parcial (mesma limitação de
qualquer heurística lexical fixa do projeto — ver `SIGLAS` e
`LETRAS_DE_RISO` em `estilo.py`). CPF e cartão usam validação de dígito
verificador para reduzir falso positivo, mas nomes próprios sozinhos
(sem CPF/e-mail/telefone junto) **não** são cobertos nesta spec — mascarar
nome exigiria NER, que é modelo adicional fora do escopo aqui definido
(mascaramos o que é identificável por padrão determinístico, não entidade
nomeada genérica).
