# Guia de uso

O Fraus ajuda a examinar atendimentos de chatbot e **estima satisfação** a
partir das conversas. Não pergunta a nota ao cliente, não revela seu estado
real e **não avalia o desempenho de atendentes**. Para entender a evidência e
seus limites, consulte o [cartão do modelo](cartao-do-modelo.md) e as
[limitações](limitacoes.md).

## Acesso e permissões

Acesse a dashboard da sua instalação. Quando o login estiver habilitado,
entre com sua conta; o cadastro pode exigir um código ou convite fornecido
pela organização. Um convite de equipe precisa ser aceito com uma sessão de
usuário válida. Não envie senhas ou chaves junto com arquivos de atendimento.

Existem duas permissões diferentes:

- **Papel global:** `usuario` (analista) ou `dev` (desenvolvedor). Ambos têm as
  tarefas de acompanhamento e análise. **Modelo**, **Integrações** e
  **Configurações** são destinos de `dev`; gerar a chave do Tars e remover um
  atendimento também exigem esse papel.
- **Papel na equipe:** proprietário, gestor ou membro. Essa hierarquia governa
  ações sobre a equipe; **ser proprietário não transforma a conta em `dev`**.
  Controles de gestão dependem do papel informado pelo servidor, não apenas de
  conseguir abrir Operação.

Os canais autorizados também delimitam quais conversas cada pessoa pode ver.
Uma conta criada por convite começa sem acesso às conversas; aceitar o convite
atribui os canais cadastrados na equipe, respeitando políticas administrativas
explícitas. Equipe sem canais não libera todo o histórico. Se faltar acesso,
peça a quem administra a instalação que confira a equipe e os canais — não é
motivo para reenviar os mesmos dados.

Na lateral ficam **Visão geral**, **Atendimentos**, **Analisar**, **Grafo** e,
para `dev`, **Modelo**. Abra o **menu da conta**, no rodapé, para **Operação**,
Integrações e Configurações conforme sua permissão, tema claro/escuro e saída.
O link da documentação aparece quando configurado pela instalação.

## Analisar um arquivo

1. Abra **Analisar** e arraste o arquivo à área de envio ou use **Escolher
   arquivo**. O seletor aceita CSV/TSV, planilhas XLSX/XLSM, JSON/JSONL, TXT,
   DOCX e PDF; a identificação do conteúdo depende do formato real do arquivo.
   Conversas exportadas do WhatsApp entram como arquivo de texto.
2. Aguarde a leitura. Há limite de **200.000 bytes por arquivo**; se a tela
   informar excesso, divida o conteúdo em partes menores preservando as
   conversas e seus horários.
3. Se a associação das colunas for confiável para o servidor, a análise segue
   automaticamente. **Com horários válidos, a tela solicita também a gravação**.
   Não existe uma segunda confirmação manual antes dessa tentativa de salvar.
4. Se houver dúvida, aparece **Conferir colunas**. Nada foi gravado nessa
   etapa. Confira **Fala** e **Quem falou**; em **Mais colunas — data, conversa e
   canal**, ajuste os campos disponíveis. Sem identificador de conversa, o
   arquivo é tratado como uma conversa só. Confira também a ordem dia/mês ou
   mês/dia quando perguntada, a amostra e os avisos de linhas rejeitadas.
5. Use **Analisar** para confirmar a conferência. Depois do resultado, a opção
   **Ajustar colunas**, quando disponível, permite revisar a associação;
   **Trocar arquivo** abre outro envio.

!!! warning "Arquivo sem horário: leitura avulsa"
    Sem horário das mensagens não há latência, **nota da conversa nem gravação
    nos indicadores**. A leitura por mensagem continua disponível. Não invente
    datas para obter uma nota; prefira exportar novamente com os horários reais.

A confiabilidade da leitura de colunas não é confiança estatística na
classificação. Confira os avisos mesmo quando o fluxo seguir automaticamente.
O tratamento de dados pessoais reduz exposição, mas não dispensa autorização
para enviar os arquivos nem revisão das regras da organização.

## Confirmar o que foi salvo

A confirmação **“atendimento(s) salvo(s) nos indicadores”** informa a quantidade
salva e oferece **Ver indicadores**, **Ver atendimentos** e **Ver grafo** já no
período do lote. Reenviar a mesma conversa é deduplicado pelo contrato de
registro; isso não substitui conferir o resultado e o período.

**“Gravação não confirmada”** significa que a resposta não confirmou a
persistência. Não apresente esses atendimentos como já incorporados aos
indicadores. **“Análise concluída sem salvar nos indicadores”**, acompanhada do
aviso de ausência de horários, é o resultado avulso esperado, não um zero de
satisfação.

O resumo e a conversa vêm primeiro. A inspeção de sinais, probabilidades e
contribuições pode ser expandida: probabilidades por mensagem e contribuições
do fusor são objetos diferentes. O destaque de uma fala não demonstra a causa
da nota nem a influência causal de palavras isoladas.

## Encontrar o período e os atendimentos

Use os campos **De** e **até**, **Últimos 7 dias**, **Últimos 30 dias** ou
**Todo o período**. Os atalhos terminam no **último dia com dados disponível
na consulta, não em hoje**; as datas aparecem na tela. Isso permite trabalhar
com um arquivo histórico sem obter um recorte vazio por engano. O período
acompanha a navegação entre as telas pelos parâmetros da URL.

Se houver dados fora do recorte, **Limpar período** volta ao histórico
disponível. Se realmente não houver atendimentos acessíveis, a orientação
oferece analisar o primeiro arquivo e, para quem pode configurar, conectar uma
fonte. **Falha da API não é banco vazio**: a tela deve mostrar a falha, não
concluir que não existe histórico.

Na lista **Atendimentos**, abra um caso para ler a conversa e seus sinais.
Use o **Grafo** como outra forma de explorar os registros, não como validação
independente da classificação. A remoção de atendimento é ação administrativa
de `dev`, exige confirmação e fica auditada.

## Interpretar os números sem inventar certeza

- **Score, nota e categoria** vêm do servidor. As faixas de fábrica são
  0–6 detrator, 7–8 neutro e 9–10 promotor; a instalação pode configurar outras
  faixas válidas. Não recalcule categorias por uma regra própria na planilha.
- **Sem sinal não é zero.** Ausência de fala informativa do cliente pode deixar
  score e nota ausentes, inclusive em encerramentos de mera cortesia. Esses
  casos não pertencem a uma categoria nem devem ser somados como detratores.
- **NPS inferido é estimativa**, não resposta a uma pesquisa. O cartão oculta o
  ponto com menos de **30 atendimentos com sinal**. O intervalo **AW(3,T)** mede
  incerteza amostral, **não o erro do classificador** nem uma garantia de acerto.
- Emoção é uma classificação textual auxiliar; não é leitura biométrica nem
  prova do estado real da pessoa. A ironia é exibida por mensagem, mas não
  entra no vetor que calcula a nota.
- Compare NPS e latência no conjunto, e leia casos individuais antes de agir.
  Associação entre tema, espera e satisfação não demonstra causalidade.
  O sinal de tempo foi treinado em conversas sintéticas, não em atendimentos
  reais rotulados com satisfação.

## Quando algo não responde

Se aparecer um aviso de indisponibilidade, aguarde e use a tentativa de
reconsulta oferecida. Um serviço pode responder à sondagem de saúde e ainda
não conseguir carregar seus modelos para analisar; isso não confirma uma
inferência bem-sucedida. Não troque ausência de resultado por nota zero.

No erro de arquivo, leia a causa e use **Tentar de novo** para reenviar o
último arquivo ou **Escolher outro arquivo**. Quando oferecido, **Ajustar
colunas** recupera a conferência. Se o erro persistir, encaminhe a mensagem de
erro e o formato do arquivo ao responsável, sem compartilhar conversas ou
credenciais fora dos canais autorizados.

## Receber conversas do Tars

Quem tem papel `dev` pode abrir menu da conta → **Integrações** → **TARS** →
**Conectar o TARS**. A chave é mostrada uma única vez: use-a na configuração do
Tars, não em um arquivo de atendimento. Siga os passos e os limites de
privacidade em [Integração com o Tars](integracao-tars.md). Se esse destino não
aparece, solicite a configuração a uma pessoa autorizada; o papel de equipe
sozinho não concede essa permissão.

## Escopo deste guia

Este guia descreve os controles e contratos do código local de 26/10/2026.
A dashboard e a API publicam separadamente: uma mudança documentada ou presente
na interface local **não prova publicação em produção**. A inspeção local com
dados sintéticos e motor dublê não comprova inferência nem gravação reais; nesta
sessão, uma tentativa de upload TXT nessa demonstração retornou erro, não uma
prova de análise bem-sucedida. Resultados científicos e pendências da campanha
ficam em [Generalização e evidências](generalizacao.md).
