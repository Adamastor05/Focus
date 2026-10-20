import discord
import json
import io

chat_logs_thread_analise_de_imagens = 1549257351285182604
from groq_manager import analisar_imagem


# ============================================================
# CONFIGURAÇÕES
# ============================================================

# COLOQUE AQUI O ID DA THREAD
# "chat_logs_thread_analise_de_imagens"



# Canal onde as imagens serão analisadas
CHAT_CONVERSAS = 1347727626910826550
#CHAT_CONVERSAS = 1523110468124803204

# Canal/thread usado para logs gerais
CHAT_LOGS = 1523110468124803204


# Link para onde o usuário pode enviar uma imagem
# para avaliação manual.
LINK_AVALIACAO = (
    "https://discord.com/channels/"
    "1347727626088878151/"
    "1347727626910826551"
)


# ============================================================
# PROMPT DA MODERAÇÃO
# ============================================================

PROMPT_ANALISE = """
Você é o sistema de moderação visual de um servidor
cristão no Discord chamado Bíblia em Foco.

Sua função é analisar imagens enviadas pelos membros
e determinar se elas são apropriadas para permanecer
em um ambiente cristão e familiar.

Analise a imagem cuidadosamente.

A imagem deve ser considerada INADEQUADA quando
apresentar claramente qualquer uma das situações abaixo:

1. Nudez.
2. Semi-nudez.
3. Pornografia.
4. Conteúdo sexual.
5. Conteúdo excessivamente sensual ou provocativo.
6. Exposição inadequada do corpo.
7. Homem sem camisa.
8. Mulher com pouca roupa ou semi-nua.
9. Roupas extremamente reveladoras.
10. Pose claramente sexualizada.
11. Conteúdo sexualmente sugestivo.
12. Violência gráfica ou extremamente explícita.
13. Qualquer outro conteúdo visual claramente incompatível
    com um ambiente cristão e familiar.

REGRA IMPORTANTE SOBRE HOMENS SEM CAMISA:

Um homem sem camisa deve ser considerado INADEQUADO,
mesmo que não exista nudez explícita.

REGRA IMPORTANTE SOBRE MULHERES:

Mulheres usando roupas normais NÃO devem ser consideradas
inadequadas apenas por serem mulheres ou por aparecer
alguma parte normal do corpo.

Entretanto, imagens com pouca roupa, semi-nudez,
roupas extremamente reveladoras ou sexualização evidente
devem ser consideradas inadequadas.

CONTEXTO:

- Não considere uma imagem inadequada apenas porque
  existe alguma pele aparecendo.
- Pessoas usando roupas normais são permitidas.
- Não invente elementos que não aparecem na imagem.
- Considere o contexto geral da imagem.
- Imagens religiosas, históricas ou artísticas devem ser
  analisadas considerando seu contexto.
- Uma imagem não deve ser marcada como inadequada
  simplesmente por mostrar uma estátua, pintura ou
  representação histórica sem conteúdo sexual explícito.
- O objetivo é manter um ambiente cristão, familiar
  e apropriado para a comunidade.

SE HOUVER DÚVIDA:

Se você não conseguir determinar claramente que a imagem
é inadequada, prefira classificá-la como PERMITIDA.

Retorne SOMENTE um JSON válido.

Para imagem inadequada:

{
    "inadequada": true,
    "categoria": "semi_nudez",
    "motivo": "A imagem apresenta uma pessoa com grande parte do corpo exposta."
}

Para imagem permitida:

{
    "inadequada": false,
    "categoria": "permitida",
    "motivo": "A imagem não apresenta conteúdo inadequado."
}

Categorias possíveis:

- permitida
- nudez
- semi_nudez
- sexual
- sensual
- ofensiva
- violencia_grafica
- outra
"""


# ============================================================
# ENCONTRAR A THREAD DE ANÁLISE
# ============================================================

async def obter_thread_analise(bot):

    thread = bot.get_channel(
        chat_logs_thread_analise_de_imagens
    )

    if thread is not None:
        return thread

    try:
        thread = await bot.fetch_channel(
            chat_logs_thread_analise_de_imagens
        )

        return thread

    except (
        discord.NotFound,
        discord.Forbidden,
        discord.HTTPException
    ):
        return None


# ============================================================
# VERIFICAR SE O ANEXO É UMA IMAGEM
# ============================================================

def eh_imagem(attachment: discord.Attachment):

    if attachment.content_type:

        return attachment.content_type.startswith(
            "image/"
        )

    extensoes = (
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".bmp"
    )

    return attachment.filename.lower().endswith(
        extensoes
    )


# ============================================================
# COPIAR IMAGEM PARA A THREAD DE ANÁLISE
# ============================================================

async def encaminhar_imagem_para_analise(
    thread,
    message,
    attachment,
    image_bytes
):

    try:

        embed = discord.Embed(
            title="🖼️ Imagem recebida para análise",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="Usuário",
            value=(
                f"{message.author.mention}\n"
                f"`{message.author.id}`"
            ),
            inline=False
        )

        embed.add_field(
            name="Canal",
            value=(
                f"{message.channel.mention}\n"
                f"`{message.channel.id}`"
            ),
            inline=False
        )

        embed.add_field(
            name="Mensagem",
            value=(
                f"[Ir para a mensagem]({message.jump_url})"
            ),
            inline=False
        )

        embed.add_field(
            name="Arquivo",
            value=attachment.filename,
            inline=False
        )

        if message.content:
            embed.add_field(
                name="Texto da mensagem",
                value=message.content[:1024],
                inline=False
            )

        embed.set_footer(
            text=f"ID da mensagem: {message.id}"
        )

        arquivo = discord.File(
            io.BytesIO(image_bytes),
            filename=attachment.filename
        )

        await thread.send(
            embed=embed,
            file=arquivo
        )

        return True

    except (
        discord.Forbidden,
        discord.HTTPException
    ):
        return False


# ============================================================
# REGISTRAR REMOÇÃO NO CHAT_LOGS
# ============================================================

async def registrar_remocao_chat_logs(
    bot,
    message,
    attachment,
    categoria,
    motivo
):

    canal_logs = bot.get_channel(
        CHAT_LOGS
    )

    if canal_logs is None:

        try:
            canal_logs = await bot.fetch_channel(
                CHAT_LOGS
            )
        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException
        ):
            return

    embed = discord.Embed(
        title="🚨 Imagem removida automaticamente",
        color=discord.Color.red()
    )

    embed.set_thumbnail(
        url=message.author.display_avatar.url
    )

    embed.add_field(
        name="Usuário",
        value=(
            f"{message.author.mention}\n"
            f"`{message.author.id}`"
        ),
        inline=False
    )

    embed.add_field(
        name="Canal",
        value=(
            f"{message.channel.mention}\n"
            f"`{message.channel.id}`"
        ),
        inline=False
    )

    embed.add_field(
        name="Categoria",
        value=f"`{categoria}`",
        inline=True
    )

    embed.add_field(
        name="Motivo",
        value=motivo[:1024],
        inline=False
    )

    embed.add_field(
        name="Mensagem",
        value=(
            f"[Ir para a mensagem]({message.jump_url})"
        ),
        inline=False
    )

    embed.add_field(
        name="Imagem",
        value=attachment.url,
        inline=False
    )

    embed.set_footer(
        text=f"ID da mensagem: {message.id}"
    )

    try:
        await canal_logs.send(
            embed=embed
        )
    except (
        discord.Forbidden,
        discord.HTTPException
    ):
        pass


# ============================================================
# AVISAR O USUÁRIO
# ============================================================

async def avisar_usuario(
    message
):

    texto = (
        "Sua imagem foi removida porque foi considerada "
        "**inadequada para este servidor**.\n\n"
        "Caso você não tenha certeza se uma imagem pode "
        "ser publicada, você pode enviá-la para avaliação em:\n"
        f"{LINK_AVALIACAO}\n\n"
        "Se você acredita que a remoção foi um engano, "
        "procure a equipe de administração."
    )

    try:

        await message.author.send(
            texto
        )

    except (
        discord.Forbidden,
        discord.HTTPException
    ):
        pass


# ============================================================
# ANALISAR UMA IMAGEM
# ============================================================

async def analisar_uma_imagem(
    bot,
    message,
    attachment,
    thread_analise
):

    # --------------------------------------------------------
    # Baixar a imagem
    # --------------------------------------------------------

    try:

        image_bytes = await attachment.read()

    except (
        discord.HTTPException,
        discord.NotFound
    ):

        return False


    # --------------------------------------------------------
    # Encaminhar a imagem para a thread de análise
    # --------------------------------------------------------

    await encaminhar_imagem_para_analise(
        thread_analise,
        message,
        attachment,
        image_bytes
    )


    # --------------------------------------------------------
    # MIME TYPE
    # --------------------------------------------------------

    mime_type = (
        attachment.content_type
        or "image/jpeg"
    )


    # --------------------------------------------------------
    # Enviar para a Groq
    # --------------------------------------------------------

    try:

        resposta = await analisar_imagem(
            image_bytes=image_bytes,
            prompt=PROMPT_ANALISE,
            mime_type=mime_type
        )

    except Exception as erro:

        try:

            await thread_analise.send(
                f"⚠️ **Erro ao analisar imagem**\n"
                f"Mensagem: `{message.id}`\n"
                f"Erro: `{erro}`"
            )

        except (
            discord.Forbidden,
            discord.HTTPException
        ):
            pass

        return False


    # --------------------------------------------------------
    # Converter resposta para JSON
    # --------------------------------------------------------

    try:

        resultado = json.loads(
            resposta
        )

    except (
        json.JSONDecodeError,
        TypeError
    ):

        try:

            await thread_analise.send(
                "⚠️ A Groq retornou uma resposta que "
                "não pôde ser convertida para JSON.\n\n"
                f"```text\n{resposta[:1800]}\n```"
            )

        except (
            discord.Forbidden,
            discord.HTTPException
        ):
            pass

        return False


    # --------------------------------------------------------
    # Resultado
    # --------------------------------------------------------

    inadequada = bool(
        resultado.get(
            "inadequada",
            False
        )
    )

    categoria = resultado.get(
        "categoria",
        "outra"
    )

    motivo = resultado.get(
        "motivo",
        "Nenhum motivo informado."
    )


    # ========================================================
    # IMAGEM PERMITIDA
    # ========================================================

    if not inadequada:

        embed = discord.Embed(
            title="🟢 Imagem permitida",
            color=discord.Color.green()
        )

        embed.add_field(
            name="Usuário",
            value=(
                f"{message.author.mention}\n"
                f"`{message.author.id}`"
            ),
            inline=False
        )

        embed.add_field(
            name="Categoria",
            value=f"`{categoria}`",
            inline=True
        )

        embed.add_field(
            name="Motivo",
            value=motivo[:1024],
            inline=False
        )

        try:

            await thread_analise.send(
                embed=embed
            )

        except (
            discord.Forbidden,
            discord.HTTPException
        ):
            pass

        return False


    # ========================================================
    # IMAGEM INADEQUADA
    # ========================================================

    embed = discord.Embed(
        title="🔴 Imagem considerada inadequada",
        color=discord.Color.red()
    )

    embed.add_field(
        name="Usuário",
        value=(
            f"{message.author.mention}\n"
            f"`{message.author.id}`"
        ),
        inline=False
    )

    embed.add_field(
        name="Categoria",
        value=f"`{categoria}`",
        inline=True
    )

    embed.add_field(
        name="Motivo",
        value=motivo[:1024],
        inline=False
    )

    embed.add_field(
        name="Ação",
        value="🗑️ Mensagem removida",
        inline=False
    )

    try:

        await thread_analise.send(
            embed=embed
        )

    except (
        discord.Forbidden,
        discord.HTTPException
    ):
        pass


    # --------------------------------------------------------
    # Tentar apagar a mensagem
    # --------------------------------------------------------

    try:

        await message.delete()

    except (
        discord.NotFound,
        discord.Forbidden,
        discord.HTTPException
    ):

        return False


    # --------------------------------------------------------
    # Registrar no chat_logs
    # --------------------------------------------------------

    await registrar_remocao_chat_logs(
        bot=bot,
        message=message,
        attachment=attachment,
        categoria=categoria,
        motivo=motivo
    )


    # --------------------------------------------------------
    # Avisar o usuário
    # --------------------------------------------------------

    await avisar_usuario(
        message
    )


    return True


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

async def analisar_mensagem_de_imagem(
    bot,
    message: discord.Message
):

    # --------------------------------------------------------
    # Só funciona em #chat_conversas
    # --------------------------------------------------------

    if message.channel.id != CHAT_CONVERSAS:
        return


    # --------------------------------------------------------
    # Verificar se existem anexos
    # --------------------------------------------------------

    if not message.attachments:
        return


    # --------------------------------------------------------
    # Encontrar thread de análise
    # --------------------------------------------------------

    thread_analise = await obter_thread_analise(
        bot
    )

    if thread_analise is None:
        return


    # --------------------------------------------------------
    # Analisar todas as imagens da mensagem
    # --------------------------------------------------------

    for attachment in message.attachments:

        if not eh_imagem(attachment):
            continue

        removida = await analisar_uma_imagem(
            bot=bot,
            message=message,
            attachment=attachment,
            thread_analise=thread_analise
        )

        # ----------------------------------------------------
        # Se a mensagem foi removida, não precisamos
        # continuar analisando os outros anexos.
        # ----------------------------------------------------

        if removida:
            break