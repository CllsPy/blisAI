from dotenv import dotenv_values

# Lê DIRETO do arquivo, ignora variáveis da sessão
values = dotenv_values(".env")
key = values.get('OPENAI_API_KEY')

if not key:
    print("ERRO: OPENAI_API_KEY nao encontrada no .env")
else:
    print("Inicio:", repr(key[:20]))
    print("Fim:   ", repr(key[-10:]))
    print("Tamanho:", len(key))