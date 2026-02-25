```md
# API REST Multi-Agent com LangGraph

## Sumário
- Objetivo  
- Como usei IA no desenvolvimento  
- Como rodar localmente (Docker)

# Objetivo

Desenvolvimento de uma **API REST com arquitetura multi-agent usando LangGraph**, onde **dois agentes colaboram** para responder perguntas sobre viagens.

# Como usei IA no desenvolvimento

## TL;DR

- Uso IA com **Question Driven Development**, começando com muitas perguntas e modelos menores.  
- Quebro o problema com **GPT-5**, uso LLMs para estruturar o projeto e gerar prompts (**APE, CoT**).  
- Sempre reviso o código por causa do problema de **“Lost in the Middle”**.  
- Uso **Claude** para debugar (Docker/Redis).  
- Ferramentas: **Claude Code, ChatGPT e DeepSeek**.  
- Funcionou para: entender conceitos, alterar código, debugar, criar testes e rodar localmente.  
- Não funcionou: debugar sem acesso à codebase.  
- MCP usado: **sequentialthinking**.  
- Comandos no Claude Code: `#`, `/init`.

## Quebre em um milhão de partes

Uso **Question Driven Development**: muitas perguntas antes de implementar.  

Primeiro passo: decompor o problema com **GPT-5** em partes menores.  
Isso organizou o documento e preparou a etapa dos agentes.

## Backbone

Antes: **Cookiecutter**.  
Hoje: **LLMs geram toda a estrutura do projeto**.

## Engenharia de Prompt (CoT, Auto-CoT, APE)

Escrever prompt manualmente é repetitivo.  
Uso LLMs para gerar exemplos e estruturar meu prompt base com **APE**.

Base padrão:

```

Como um AIE Sênior, como você construiria X?

exemplo 1 - input

###

exemplos gerados por LLMs

###

exemplo 2 - output

###

outputs esperados

###

````

## Quem vigia o vigilante?

Modelos degradam com contexto longo.  
O trabalho **“Lost In The Middle”** mostra essa limitação.

Por isso:
- Sempre reviso código gerado.  
- Evito continuar chats com erros acumulados.  
- Reinicio a abordagem quando necessário.

## I can’t understand, mate

Problemas com **Docker e Redis** exigiram debug mais profundo.  
Usei **Claude** para interpretar logs e entender persistência.

Mesmo fora do escopo de IA, pedi explicações para avançar.

## Na natureza nada se cria

Ideias vieram de:
- Colegas dev  
- Relatório da **Anthropic** sobre produtividade com IA  

Após bugs, o mais importante foi pedir **direcionamento estratégico**.

### MCP é inútil?

**Limitações atuais:**
- Uso apenas API da OpenAI  
- Apenas uma ferramenta externa (WEB)  

**Quando faria sentido?**
- Muitas ferramentas integradas  
- Abordagem unificada em vez de criar uma API por caso de uso  

Optei por usar **MCPs populares já consolidados**.  
Para maximizar reasoning no Claude, usei **sequentialthinking (CoT)**.

# Como rodar localmente (com Docker)

## Pré-requisitos

- **Python 3.11+**  
- **Docker**

## 1. Ambiente virtual

```bash
python3 -m venv venv
````

Linux/macOS:

```bash
source venv/bin/activate
```

Instalar dependências:

```bash
pip install -e .
```

## 2. Variáveis de ambiente

Crie `.env`:

```
OPENAI_API_KEY=sk-sua-chave-aqui
TAVILY_API_KEY=tvly-sua-chave-aqui
REDIS_URL=redis://localhost:6379
APP_ENV=production
LOG_LEVEL=INFO
FAISS_INDEX_PATH=./data/faiss_index
DOCS_PATH=./docs/faq_data
```

## 3. Subir Redis

```bash
docker compose up --build
```

## 4. Acessar API

API: [http://localhost:8000](http://localhost:8000)
Health: [http://localhost:8000/health](http://localhost:8000/health)

Resposta esperada:

```json
{"status":"ok","version":"1.0.0","redis_connected":true,"faiss_loaded":true}
```

Docs interativa:

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

Os testes usam **mocks**.
Não precisam de chaves reais.

```
```
