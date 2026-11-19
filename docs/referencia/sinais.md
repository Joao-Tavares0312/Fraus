# Os sinais

Oito famílias observadas; sete fornecem as 39 entradas do fusor. Texto,
emoção, ironia, emoji, léxico, estilo e incongruência analisam a fala do
cliente. **Tempo não é texto:** deriva latências, duração, turnos, escalação
e abandono da estrutura e dos timestamps, inclusive respostas do bot/humano.
Isso não autoriza pontuar atendentes. Emoção em texto não implica
enquadramento automático como reconhecimento biométrico de emoção; a
fronteira de produto continua sendo não avaliar trabalhadores. Ver
[Conformidade](../conformidade.md).

Algumas docstrings preservam o histórico de treino e de quantidade de
features. O contrato vigente é `NOMES_FEATURES`, em
[Fusor](fusor.md): incongruência tem seis entradas, ironia nenhuma.

## Texto — o único que pontua sozinho

::: fraus.sinais.texto

## Emoção

::: fraus.sinais.emocao

## Tempo

::: fraus.sinais.tempo

## Léxico

::: fraus.sinais.lexico

## Emoji

::: fraus.sinais.emoji

## Ironia — leitura por mensagem, fora do vetor

::: fraus.sinais.ironia

## Estilo

::: fraus.sinais.estilo

## Incongruência

::: fraus.sinais.incongruencia

## Curadoria

Termos e emojis curados vencem os léxicos base; não sobrescrevem diretamente a
nota e não são retreino. A versão acompanha a pontuação.

::: fraus.sinais.curadoria

## Executor ONNX

Executa grafos locais por `CPUExecutionProvider`, sem importar Torch. O
backend é declarado, não detectado pela presença de arquivos; grafo ausente
ou ilegível é falha explícita. As classes seguem a ordem do checkpoint.
O executor lê a precisão do grafo fornecido (FP32 ou quantizado); não quantiza
pesos durante a predição. As descrições históricas de INT8 nas docstrings não
significam que toda cabeça deva ser quantizada.

::: fraus.sinais.onnx
