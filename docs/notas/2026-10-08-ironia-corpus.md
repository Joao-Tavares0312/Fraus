# Ironia — o retreino de 08/10/2026 e o corpus que entrega o rótulo

Nota de sessão. A análise e o plano estão em [Ironia: corpus e Laya](../ironia.md).

## O que rodou

Notebook 04, branch `fix/notebooks-conta-do-drive`, Colab da conta da Unis
(janela anônima só com essa conta; o popup do `drive.mount` numa janela com a
conta @staff padrão deu `credential propagation was unsuccessful`). T4, fraus
instalado da `main` em `957056a`.

- **Trava de conta:** a célula 1 confirmou `Drive montado e o de
  joao.tavaresvicente@alunos.unis.edu.br`.
- **Backup:** o BERTimbau de ironia anterior foi copiado para
  `fraus/modelos/bertimbau-ironia-anterior-2026-10-02` no Drive. O
  `metricas_ironia.json` do Drive diz que ele foi treinado só no **sintético**
  (`gerador_ironia`, semente 42, 5.100 exemplos, F1 1,0).
- **Contaminação evitada:** havia um `sintetico_s42.csv` de 28/09 esquecido em
  `fraus/dados/ironia`. A célula 4 relia a pasta inteira e juntou 6.000 frases
  sintéticas ao IDPT (39.143 linhas em vez de 33.143). Quebrou por `fonte`
  nula. Consertado no commit `cf2a8f4`: a leitura usa só `encontrados`.
- **Divisão:** treino 28.365 (58,8% irônicas), teste 4.778 (59,2%), por autor,
  impressão do teste `c790ec86dc28af18`. Bate com o previsto.
- **Treino:** 3 épocas, 13 min. F1 macro por época: 0,9933 / 0,9942 / 0,9935.

## Resultado

| Recorte | n | F1-macro |
|---|---:|---:|
| Teste interno | 4.778 | 0,9942 |
| Só tweets | 2.030 | 0,9906 |
| Só notícias | 2.748 | 0,9931 |

Sondas de domínio, P(irônico):

| Frase | Esperado | Anterior (sintético) | Novo (IDPT) |
|---|---|---:|---:|
| otimo servico, so esperei 3 horas | irônico | 0,998 | 1,000 |
| parabens pelo atendimento, nota mil, so 5 dias sem resposta | irônico | 0,994 | 1,000 |
| qual o prazo de entrega do meu pedido | não | 0,001 | 1,000 |
| obrigado, resolveram rapido | não | 0,001 | 1,000 |
| meu cartao foi bloqueado e ninguem me responde | não | 0,001 | 1,000 |
| ok, obrigado | não | 0,005 | 1,000 |

Traços de superfície por fonte (médias): `tweets_ironicos` começam com
minúscula em 20,5% dos casos e terminam em ponto em 22,7%; `tweets_nao_ironicos`
em 1,6% e 4,8%. As amostras de não irônicos são manchetes de economia ("Banco
Central mantém ritmo de corte da Selic…"), uma delas em italiano.

## Decisão

O modelo novo **não foi exportado** (a célula 8 não rodou) e o notebook 07 não
rodou. Produção não muda: a ironia é o Laya sem treino (`laya-onnx`) e está
fora do Fusor.

Ressalva não consertada: o notebook 04 escolhe a melhor época
(`load_best_model_at_end`) avaliando no próprio teste.
