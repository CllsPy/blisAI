# Objetivo

Desenvolvimento de uma API REST com arquitetura multi-agent usando LangGraph, onde dois agentes colaboram para responder perguntas sobre viagens.

## Como usei IA no desenvolvimento?

### TL;DR:

- Eu uso IA com abordagem Question Driven Development, começando com muitas perguntas e modelos menores.
- Quebro o problema em partes com GPT-5, uso LLMs para montar a estrutura do projeto e gerar prompts (APE, CoT).
- Sempre reviso o código porque os modelos perdem contexto (“Lost in the Middle”) e evito continuar chats com muitos erros acumulados.
- Uso Claude para debugar (ex: Docker/Redis) e me inspiro em colegas e no relatório da Anthropic para evoluir minha produtividade.

Quando inicio um projeto novo eu uso a abordagem Question Driven Development, isso significa fazer muitas perguntas: como conectar os Agentes? Como criar um nó de decisão… Para essa primeira etapa eu uso modelos menores e mais rápido, evito Agentes ou Reasoning.

### Quebre em um milhão de partes

A primeira coisa que fiz foi usar o GPT-5 para decompor o desafio em partes menores para poder organizar esse documento também é fundamental para quando eu iniciar a etapa dos Agentes.

### Backbone

Antes dos modelos de linguagem eu usava uma uma ferramenta chamada Cookiecutter para gerar a estrutura dos projetos, hoje isso é feito estritamente com LLMs.

### Engenharia de Prompt (CoT, Auto-CoT, APE)

Minhas experiência passadas provam duas coisas, escrever Prompt é chato e ter que ficar fazendo isso muitas vezes é ainda pior. Então eu também uso outros modelos de linguagem para gerar exemplos para o meu prompt base, usando uma estratégia chamada APE.

Todo prompt que escrevo, tem como base, o que se segue:

```
Como um AIE Sênior, como você construiria X?

exemplo 1 - input

###

exemplos gerados por LLMs

###

exemplo 2 - output

###

outputs que eu espero

###
```

### Quem vigia o vigilante?

É sabido que modelos degradam no processo quando o contexto aumenta, há um trabalho sobre isso chamado “Lost In The Middle”, mesmo com contexto superior a 128k tokens, os modelos tendem a “esquecer” informações no meio. Então, eu sempre tive a preocupação de conferir o código gerado, mesmo que após os testes tudo parecesse certo. Mas, também sempre evitei continuar em um chat onde os erros foram acumulados, é um batalha perdida, nesses casos eu tentava outra abordagem.

### I can’ understand mate

Especialmente nas etapas com Docker e Redis, embora familiar a ambos, minha falta de prática me impediram de entender alguns logs, nesses casos eu usei o Claude sem nem pestanejar, tanto quanto para debugar o código, a medida que a complexidade aumentava eu também solicitei alguns vezes explicações das implementações feita fora do escopo da Inteligência Artificial, como a persistência. Isto me ajudou a progredir mesmo não dominando completamente a ferramenta.

### Na natureza nada se cria

A maior parte dessas ideias vieram de colegas que trabalham com desenvolvimento web e de um excelente relatório publicado pela Anthropic de como os engenheiros da empresa usam IA para aumentar a produtividade. Busquei me alinhar o máximo com o relatório e posso assegurar que o que mais precisei fazer depois de lidar com os bugs, foi solicitar direcionamento após cometer erros.
