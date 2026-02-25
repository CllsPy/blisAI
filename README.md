# Objetivo
Desenvolvimento de uma API REST com arquitetura multi-agent usando LangGraph, onde dois agentes colaboram para responder perguntas sobre viagens.

# Como usei IA no desenvolvimento?
## TL;DR
- Eu uso IA com abordagem Question Driven Development, começando com muitas perguntas e modelos menores.
- Quebro o problema em partes com GPT-5, uso LLMs para montar a estrutura do projeto e gerar prompts (APE, CoT).
- Sempre reviso o código porque os modelos perdem contexto (“Lost in the Middle”) e evito continuar chats com muitos erros acumulados.
- Uso Claude para debugar (ex: Docker/Redis) e me inspiro em colegas e no relatório da Anthropic para evoluir minha produtividade.
- Usei Claude Code, ChatGPT e DeepSeek.
- Funcionou para compreender conceitos minimamente, alterar código conforme o teste, debugar, criar testes e entender como rodar o projeto localmente.
- Não funcionou tentar debugar sem acesso à codebase é complexo e quase impossível. Por isso, exceto o Claude, os outros modelos foram usados apenas para perguntas pontuais.
- MCP usado: sequentialthinking
- Comandos usados com Claude Code (#, /init)

## Quebre em um milhão de partes

Quando inicio um projeto novo eu uso a abordagem Question Driven Development. Isso significa fazer muitas perguntas: como conectar os agentes? Como criar um nó de decisão? Para essa primeira etapa uso modelos menores e mais rápidos, evitando Agentes ou Reasoning.
A primeira coisa que fiz foi usar o GPT-5 para decompor o desafio em partes menores. Isso me ajudou a organizar o documento e será fundamental na etapa dos Agentes.

## Backbone
Antes dos modelos de linguagem eu usava Cookiecutter para gerar a estrutura dos projetos. Hoje isso é feito estritamente com LLMs.

## Engenharia de Prompt (CoT, Auto-CoT, APE)

Minhas experiências passadas mostram que escrever prompt é chato  e repetir isso várias vezes é pior ainda.  
Por isso uso outros modelos para gerar exemplos para meu prompt base, aplicando a estratégia APE.

```
Todo prompt que escrevo segue esta base:

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

## Quem vigia o vigilante?

Modelos degradam quando o contexto aumenta. O trabalho “Lost In The Middle” mostra que, mesmo com mais de 128k tokens, eles tendem a esquecer informações no meio. Por isso sempre reviso o código gerado, mesmo quando os testes passam.  
Evito continuar chats onde erros foram acumulados — nesses casos, tento outra abordagem.

## I can’t understand, mate

Especialmente nas etapas com Docker e Redis, apesar de familiaridade, minha falta de prática dificultou entender alguns logs.  
Nesses casos usei Claude para debugar.

À medida que a complexidade aumentava, também pedi explicações sobre implementações fora do escopo de IA, como persistência.  
Isso me ajudou a avançar mesmo sem domínio total da ferramenta.

## Na natureza nada se cria

Grande parte das ideias veio de colegas de desenvolvimento web e de um relatório da Anthropic sobre como seus engenheiros usam IA para produtividade. Busquei me alinhar ao relatório. Depois de resolver bugs, o que mais precisei fazer foi pedir direcionamento após cometer erros.

### MCP é inútil
**Um MCP do projeto, tem algumas limitações,** a primeira é que eu usei a api da Openai, a segunda é que eu estou usando apenas uma ferramenta externa que é o acesso a WEB.

**Em que situação faria sentido usar?** Bem, se houvesse uma quantidade maior de ferramentas, como ocorre na BLIS faria sentido centralizar as ferramentas dessa forma teríamos outra abordagem mais unificada em oposição a **criar uma API para cada caso de uso.**

Então, **eu optei por usar ÚTEIS MCPs populares e escrito para pessoas, certamente, melhores que eu.  Porque eu adoro CoT (Chain Of Thoughts) e para maximizar o reasoning do Claude eu usei o sequentialthinking**

# Como rodar localmente (com Docker)

## Pré-requisitos
* Python 3.11 ou superior
* Docker

## 1. Criar e ativar o ambiente virtual

```bash
python3 -m venv venv
```

Linux/macOS:

```bash
source venv/bin/activate
```

Instale as dependências:

```bash
pip install -e .
```

## 2. Configurar variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto:

```
OPENAI_API_KEY=sk-sua-chave-aqui
TAVILY_API_KEY=tvly-sua-chave-aqui
REDIS_URL=redis://localhost:6379
APP_ENV=production
LOG_LEVEL=INFO
FAISS_INDEX_PATH=./data/faiss_index
DOCS_PATH=./docs/faq_data
```

## 3. Subir o Redis

```bash
docker compose up --build
```

## 4. Acessar a API

* API: [http://localhost:8000](http://localhost:8000)
* Health check: [http://localhost:8000/health](http://localhost:8000/health)

Resposta esperada:

```json
{"status":"ok","version":"1.0.0","redis_connected":true,"faiss_loaded":true}
```

Documentação interativa:

[http://localhost:8000/docs](http://localhost:8000/docs)

## 5. Testar via terminal

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "user-1", "message": "Qual a franquia de bagagem da LATAM?"}'
```

## 6. Rodar testes

```bash
pytest
```

Os testes usam mocks. Não precisam de chaves reais.
