# Modelo canônico

`Conversa` e `Mensagem`. Toda fonte de entrada desemboca aqui, e o resto do
sistema não sabe de onde o dado veio.

Timestamps precisam ter fuso. `feedback_declarado` aceita `-1`, `1` ou ausência;
é separado da estimativa e não muda o score. Não é uma nota NPS declarada.
`tem_fala_cliente` e `tem_sinal_cliente` são contratos diferentes: fala vazia
ou composta apenas por cortesia não sustenta nota.

::: fraus.modelos

## Cortesia e ausência de sinal

A lista é fechada e conservadora. As propostas de retreino nas docstrings
registram a origem histórica da limitação; modelos estão congelados por
decisão de 16/11/2026.

::: fraus.cortesia
