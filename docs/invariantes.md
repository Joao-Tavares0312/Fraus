# As dez invariantes

Não são preferências de estilo. **Cada uma nasceu de um defeito real**, e
violá-la é reintroduzir o defeito — por isso cada regra aqui vem com a cicatriz
que a produziu. Documentação que explica cicatriz é a que não dá para copiar de
tutorial.

O formato é sempre o mesmo: **a regra**, *por que ela existe*, **o que quebra se
alguém a violar**, e onde ela mora no código.

---

## 1. Sem LLM em runtime

**A regra.** Inferência local em CPU. Nenhuma chamada de rede no caminho de
predição.

**Por que existe.** É requisito do trabalho, não otimização de custo. A tese é
que dá para medir satisfação com modelos pequenos, fine-tunados e
interpretáveis — chamar uma API de LLM não deixaria o sistema mais rápido, e
invalidaria o que ele se propõe a demonstrar.

**O que quebra.** O trabalho inteiro. Nenhum teste pega isso: o código
funcionaria melhor e a defesa cairia.

**Onde mora.** Três BERTimbau em `fraus/sinais/` e um `LogisticRegression` em
`fraus/fusor.py`.

---

## 2. Ausência de dado não é insatisfação

**A regra.** Conversa sem fala do cliente tem `score: None` e aparece como "sem
sinal" — nunca `0`, em lugar nenhum: célula, gráfico, ordenação, export,
agregado.

**Por que existe.** `None` e `0` significam coisas diferentes e não podem se
confundir. Zero numa coluna de tempo de resposta se lê como "respondeu na hora",
e a conversa que nunca teve atendente humano apareceria como **a mais ágil da
operação**. Zero num NPS se lê como um número que alguém mediu.

**O que quebra.** Silenciosamente, tudo: o pior valor da escala aparece onde a
verdade era "não medi". Em 10/09/2026 essa regra ainda estava furada dentro do
próprio arquivo que mais a defende — `containment_rate` devolvia `0.0` no
conjunto vazio, e o front tinha uma guarda para não acreditar nele.

**Onde mora.** Em toda parte. Procure `?? 0` e `|| 0` antes de commitar — e
**também `return 0` no Python**, que é o mesmo defeito disfarçado de
inicialização.

---

## 3. Score, nota e categoria são derivados no servidor

**A regra.** Nunca aceitos do corpo da requisição, nunca recalculados no
cliente.

**Por que existe.** O `round` do Python é bancário (`round(6.5) == 6`) e o
`Math.round` do JavaScript arredonda meio para cima (`Math.round(6.5) == 7`).

**O que quebra.** Já quebrou: a tabela exibia **nota 7 ao lado da etiqueta
"Detrator"**, nas fronteiras 6/7 e 8/9. Duas fontes da verdade para o mesmo
número, discordando na tela do usuário.

**Onde mora.** `fraus/indicadores.py::nota_0_10`. O front consome; não
recalcula.

---

## 4. Faixas de NPS: 0–6 detrator, 7–8 neutro, 9–10 promotor

**A regra.** Padrão de fábrica em `FAIXAS_NPS`, configurável por
`PUT /configuracoes` — e só se as faixas cobrirem 0..10 de forma contígua. A
faixa vigente é passada **por parâmetro**, nunca lida de estado global.

**Por que existe.** Estado global mutável muda sob os pés de quem já calculou. E
faixa com buraco ou sobreposição não é preferência de gosto: é nota sem
categoria, ou com duas.

**O que quebra.** Já quebrou: `categoriaDaNota` no front tinha `<= 6` e `<= 8`
digitados no corpo, e isso rodava no caminho feliz. Um operador que mexesse em
Configurações via a **mesma tela dar dois vereditos** para o mesmo atendimento —
a etiqueta da linha com as faixas novas, a cor da barra com as antigas.

**Onde mora.** `fraus/indicadores.py::FAIXAS_NPS`, `categoria_nps`,
`validar_faixas_nps`.

---

## 5. Latência nunca é persistida

**A regra.** Sempre derivada dos timestamps, na leitura.

**Por que existe.** Latência gravada é latência que envelhece: qualquer correção
na definição de "espera" deixaria o banco cheio de números calculados pela
regra antiga, indistinguíveis dos novos.

**O que quebra.** Duas definições de latência convivendo — uma para a lista,
outra para o detalhe — e as duas telas discordando sobre o mesmo atendimento.

**Onde mora.** `fraus/sinais/tempo.py::latencias_da_conversa`.

---

## 6. Timestamps timezone-aware

**A regra.** `datetime` naive é erro de validação, não conversão silenciosa.

**Por que existe.** Data sem fuso é data que muda de significado conforme quem
lê.

**O que quebra.** A armadilha já paga: **a data da Totalk é `MM/DD/YYYY`**, não
`DD/MM`. Lida como brasileira, espalha as mensagens por cinco meses e a latência
sai absurda **em silêncio**.

**Onde mora.** `fraus/modelos.py`.

---

## 7. Modelo ausente é falha alta e explícita

**A regra.** Sem fallback, sem motor dublê silencioso. A API não sobe sem os
três modelos treinados.

**Por que existe.** Servir predição sem modelo carregado é **pior que estar fora
do ar**: a interface não distingue número real de número sintético.

**O que quebra.** Já quebrou, e custou um dia: o `scripts/api_demo.py` estava no
ar por causa do diretório de onde foi lançado, e a dashboard escreveu "API no
ar" durante um dia inteiro enquanto **todo número da tela era sintético** — os
pesos por feature saíam numa progressão 0,2 / 0,25 / 0,3 e passavam por
coeficiente de regressão logística.

**Onde mora.** `Fusor.carregar` (valida `n_features_in_`), `GET /saude`
(`"motor": "real" | "duble"`), e `GET /saude/deriva`, que recusa diagnosticar
com dublê pela mesma lógica.

---

## 8. A ordem das classes é 0 insatisfeito, 1 neutro, 2 satisfeito

**A regra.** No notebook, no sinal de texto, no fusor e nos indicadores.

**Por que existe.** É a única convenção que amarra quatro lugares que não se
importam por código.

**O que quebra.** **Nada estoura.** O sistema pontua ao contrário, em silêncio,
com a mesma confiança de sempre. É a invariante mais barata de violar e a mais
cara de descobrir.

**Onde mora.** `fraus/sinais/texto.py` (`INSATISFEITO`, `NEUTRO`,
`SATISFEITO`).

---

## 9. As 39 chaves de feature batem exatamente com `NOMES_FEATURES`

**A regra.** As sete famílias do vetor produzem exatamente 39 chaves.
`vetorizar` levanta `KeyError` na falta — nunca zero silencioso.

**Por que existe.** Zero numa feature ausente não é neutro: o modelo aprendeu
o que zero significa naquela dimensão, e a conversa entraria como se tivesse
sido medida.

**O que quebra.** Já quebrou de outro jeito: o `CLAUDE.md` chegou a declarar
"38" na invariante e "(35)" no mapa — dois números de duas revisões, nenhum o
vigente. A documentação que governa toda sessão de agente envelhecendo em
silêncio. Hoje há teste amarrando o número do `CLAUDE.md` a
`len(NOMES_FEATURES)`.

**Onde mora.** `fraus/fusor.py::NOMES_FEATURES` — e o comentário dele conta a
história inteira: 40 − 2 (a ironia saiu) + 1 (`incongruencia_situacao_negativa`
entrou) = 39.

---

## 10. O corpus de treino não pode entregar o rótulo

**A regra.** Distribuição por rótulo se sobrepõe; feature constante no treino
nasce com peso zero. **Acurácia alta demais é sintoma, não vitória.**

**Por que existe.** Faixa de latência disjunta por classe fez o primeiro fusor
marcar **99,3% lendo só o relógio**, com o BERTimbau apagado.

**O que quebra.** Um número excelente que não mede nada. E ela não para no
treino: em 08/09/2026 a mesma invariante apareceu **em runtime** — numa conversa
com 3 h de espera, a latência contribuiu −85,4 contra +4,6 do texto inteiro, e o
score saiu em `4,4e-24`. O corpus nunca passou de minutos, então a guarda de
vazamento, que olha o corpus, não tinha o que dizer.

**Onde mora.** `docs/treinamento.md`, e agora também
[`GET /saude/deriva`](referencia/diagnostico.md), que transforma a regra de
disciplina de notebook em alarme de runtime.
