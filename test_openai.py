from dotenv import load_dotenv
import os

load_dotenv()
key = os.getenv('OPENAI_API_KEY')

from openai import OpenAI
client = OpenAI(api_key=key)

try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "diga oi"}],
        max_tokens=10
    )
    print("SUCESSO! Resposta:", response.choices[0].message.content)
except Exception as e:
    print("ERRO:", str(e))