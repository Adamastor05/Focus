import asyncio
import json

import discord
from google import genai
from google.genai import types

from config.IDs import cargo_moderador, chat_logs_thread_fotos
from gemini_manager import proxima_api, marcar_api_como_indisponivel


GEMINI_MODEL = "gemini-3.6-flash"

CATEGORIAS = {
    "conteudo_sugestivo": "Conteúdo sugestivo",
    "lgbtismo": "LGBTismo",
    "satanismo_ocultismo": "Satanismo/ocultismo",
    "racismo": "Racismo",
    "violencia": "Violência",
    "drogas": "Drogas",
    "crimes": "Crimes",
}


async def analisar_foto_com_gemini(
    image_bytes: bytes,
    mime_type: str
):
    """
    Envia a imagem para o Gemini e retorna as pontuações.
    """

    prompt = """
        Analise a imagem fornecida como foto de perfil de um membro de um servidor
        Discord.

        A imagem NÃO deve promover, fazer apologia ou incentivar nenhuma das
        categorias abaixo:

        1. Conteúdo sugestivo
        2. LGBTismo
        3. Satanismo/ocultismo
        4. Racismo
        5. Violência
        6. Drogas
        7. Crimes

        Para CADA categoria, atribua uma pontuação inteira de 0 a 100.

        IMPORTANTE:

        - 0 significa que praticamente não há indício de violação daquela categoria.
        - 100 significa que há evidência muito forte de que a imagem promove, faz
        apologia ou incentiva aquela categoria.
        - A pontuação deve representar a força da evidência visual.
        - Não dê pontuação alta simplesmente porque algo poderia ser interpretado de
        forma remota como relacionado à categoria.
        - Contexto ambíguo deve receber uma pontuação menor.
        - Não confunda simplesmente "representar" algo com "promover, fazer apologia
        ou incentivar" algo.
        - Não invente elementos que não estão visíveis na imagem.
        - Para racismo, considere símbolos, textos ou imagens claramente
        discriminatórios ou de supremacia racial.
        - Para violência, não marque alto apenas porque existe uma arma ou uma cena
        fictícia; avalie se a imagem promove ou glorifica violência.
        - Para crimes, avalie apologia, incentivo ou glorificação de atividades
        criminosas.
        - Para drogas, avalie principalmente promoção, apologia ou incentivo.
        - Para satanismo/ocultismo, avalie símbolos ou conteúdo claramente
        relacionado à promoção/apologia dessas práticas.
        - Para conteúdo sugestivo, considere sexualização, nudez, poses ou imagens
        sexualmente explícitas/sugestivas.

        Retorne SOMENTE o objeto JSON solicitado pelo schema.
        """

    image_part = types.Part.from_bytes(
        data=image_bytes,
        mime_type=mime_type
    )

    # TENTAR ATÉ 3 VEZES
    for tentativa in range(3):

        api_key = proxima_api()
        client = genai.Client(api_key=api_key)

        try:
            
            response = await client.aio.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    image_part,
                    prompt
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={
                        "type": "object",
                        "properties": {
                            "conteudo_sugestivo": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 100
                            },
                            "lgbtismo": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 100
                            },
                            "satanismo_ocultismo": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 100
                            },
                            "racismo": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 100
                            },
                            "violencia": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 100
                            },
                            "drogas": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 100
                            },
                            "crimes": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 100
                            }
                        },
                        "required": [
                            "conteudo_sugestivo",
                            "lgbtismo",
                            "satanismo_ocultismo",
                            "racismo",
                            "violencia",
                            "drogas",
                            "crimes"
                        ]
                    }
                )
            )

            # SUCESSO
            return json.loads(response.text)

        except Exception as e:

            # Se for erro 429, coloca essa API em cooldown
            if "429" in str(e):
                marcar_api_como_indisponivel(api_key)
            
            # Ainda há tentativas
            if tentativa < 2:

                espera = 5 * (tentativa + 1)

                print(
                    f"[FOTOS] Gemini falhou "
                    f"(tentativa {tentativa + 1}/3): {e}"
                )

                await asyncio.sleep(espera)

            # Última tentativa também falhou
            else:

                print(
                    f"[FOTOS] Gemini falhou após "
                    f"3 tentativas: {e}"
                )

                raise


def registrar_evento_on_user_update(bot):
    @bot.event
    async def on_user_update(
        before: discord.User,
        after: discord.User
    ):
        # Ignora bots
        if after.bot:
            return
        # Verifica se o avatar realmente mudou
        if before.avatar == after.avatar:
            return
        # Se removeu a foto, não há imagem para analisar
        if after.avatar is None:
            return

        try:
            # PEGAR O SERVIDOR
            guild = bot.get_guild(1347727626088878151)

            if guild is None:
                print("[FOTOS] Servidor não encontrado.")
                return

            # PEGAR O MEMBRO
            membro = guild.get_member(after.id)

            if membro is None:
                print(
                    f"[FOTOS] {after} não está no servidor."
                )
                return

            # BAIXAR AVATAR
            image_bytes = await after.avatar.read()

            # O Discord normalmente entrega PNG/JPEG/WebP.
            # A análise recebe os bytes diretamente.
            mime_type = "image/png"

            # ANALISAR COM IA
            resultado = await analisar_foto_com_gemini(
                image_bytes,
                mime_type
            )

            # LIMITAR OS VALORES POR SEGURANÇA
            pontuacoes = {}

            for chave in CATEGORIAS:
                valor = resultado.get(chave, 0)

                try:
                    valor = int(valor)
                except (TypeError, ValueError):
                    valor = 0

                valor = max(0, min(100, valor))
                pontuacoes[chave] = valor

            # VERIFICAR SE ALGUMA CATEGORIA PASSOU DE 60
            categorias_suspeitas = {
                chave: valor
                for chave, valor in pontuacoes.items()
                if valor > 60
            }

            precisa_moderador = (
                len(categorias_suspeitas) > 0
            )

            # PEGAR O CARGO DE MODERADOR
            role = guild.get_role(cargo_moderador)

            # PEGAR O CANAL/THREAD DE LOG
            canal_logs = guild.get_thread(
                chat_logs_thread_fotos
            )

            if canal_logs is None:
                print(
                    f"[FOTOS] Não encontrei o canal/thread "
                    f"{chat_logs_thread_fotos}"
                )
                return

            # CRIAR EMBED
            embed = discord.Embed(
                title="🖼️ Análise de foto de perfil",
                description=(
                    f"**Membro:** {membro.mention}\n"
                    f"**ID:** `{after.id}`"
                ),
                color=(
                    discord.Color.red()
                    if precisa_moderador
                    else discord.Color.green()
                )
            )

            # ADICIONAR CADA PONTUAÇÃO
            for chave, nome in CATEGORIAS.items():

                valor = pontuacoes[chave]

                if valor > 60:
                    indicador = "🔴"
                elif valor >= 40:
                    indicador = "🟡"
                else:
                    indicador = "🟢"

                embed.add_field(
                    name=f"{indicador} {nome}",
                    value=f"`{valor}/100`",
                    inline=True
                )

            # STATUS
            if precisa_moderador:
                embed.add_field(
                    name="⚠️ Status",
                    value=(
                        "Uma ou mais categorias ultrapassaram "
                        "o limite de `60` e precisam de revisão."
                    ),
                    inline=False
                )
            else:
                embed.add_field(
                    name="✅ Status",
                    value=(
                        "Nenhuma categoria ultrapassou `60`."
                    ),
                    inline=False
                )

            # COLOCAR A FOTO NO EMBED
            embed.set_image(
                url=after.display_avatar.url
            )

            # RODAPÉ
            embed.set_footer(
                text="Análise automática de foto de perfil"
            )

            # ENVIAR PARA OS MODERADORES SE NECESSÁRIO
            if precisa_moderador and role is not None:
                await canal_logs.send(
                    content=role.mention,
                    embed=embed
                )
            else:
                await canal_logs.send(
                    embed=embed
                )

        except Exception as e:
            print(
                f"[FOTOS] Erro ao analisar avatar de "
                f"{after} ({after.id}): {e}"
            )
