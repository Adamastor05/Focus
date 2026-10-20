import os
import base64

from groq import AsyncGroq


# ============================================================
# CONFIGURAÇÃO DA GROQ
# ============================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError(
        "A variável GROQ_API_KEY não foi encontrada no arquivo .env"
    )


groq_client = AsyncGroq(
    api_key=GROQ_API_KEY
)


# ============================================================
# FUNÇÃO GENÉRICA PARA ANÁLISE DE IMAGEM
# ============================================================

async def analisar_imagem(
    image_bytes: bytes,
    prompt: str,
    mime_type: str = "image/jpeg"
):
    """
    Envia uma imagem para a Groq junto com um prompt.

    Esta função é propositalmente genérica.
    O prompt NÃO fica neste arquivo.

    Assim, futuramente outras partes do bot podem
    utilizar a Groq para outras funções.
    """

    imagem_base64 = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    imagem_url = (
        f"data:{mime_type};base64,{imagem_base64}"
    )

    resposta = await groq_client.chat.completions.create(
        model="qwen/qwen3.6-27b",

        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": imagem_url
                        }
                    }
                ]
            }
        ],

        temperature=0,

        #max_completion_tokens=500,

        response_format={
            "type": "json_object"
        }
    )

    return resposta.choices[0].message.content