import discord
from discord.ext import commands

from config.IDs import (
    cargo_administrador,
    cargo_moderador,
    chat_conversas,
    chat_logs,
    conquista_a_fundacao,
)


def embed_chat(usuario: discord.Member) -> discord.Embed:
    embed = discord.Embed(
        title="Boas-vindas! É uma alegria ter você conosco.",
        description=(
            "Nosso objetivo é que este servidor seja um espaço de "
            "**comunhão** e **crescimento** na sua caminhada com Cristo. "
            "Embora nossa base teológica seja **protestante**, nossas "
            "portas estão abertas para todos que buscam aprender mais "
            "sobre Deus. Você pode se apresentar em "
            "<#1363009444111188129>."
        ),
        color=discord.Color.blue(),
    )
    embed.set_thumbnail(url=usuario.display_avatar.url)
    embed.set_image(url="https://i.imgur.com/Xwjxew6.jpg")
    embed.set_footer(text="Bíblia em Foco")
    return embed


async def procurar_topico(
    guild: discord.Guild,
    usuario: discord.Member,
) -> discord.Thread | None:
    canal = guild.get_channel(chat_conversas)
    if canal is None:
        return None

    usuario_id = str(usuario.id)

    for thread in canal.threads:
        if usuario_id in thread.name:
            return thread

    async for thread in canal.archived_threads(limit=None):
        if usuario_id in thread.name:
            if thread.archived:
                await thread.edit(archived=False)
            return thread

    return None


async def registrar_log(
    guild: discord.Guild,
    titulo: str,
    descricao: str,
    cor: discord.Colour = discord.Color.blurple(),
) -> None:
    canal = guild.get_channel(chat_logs)
    if canal is None:
        return

    embed = discord.Embed(
        title=titulo,
        description=descricao,
        color=cor,
    )
    await canal.send(embed=embed)


async def criar_topico(
    guild: discord.Guild,
    usuario: discord.Member,
    moderador: discord.Member | None = None,
) -> discord.Thread:
    canal = guild.get_channel(chat_conversas)
    if canal is None:
        raise RuntimeError(
            f"Não encontrei o canal de conversas ({chat_conversas})."
        )

    thread = await canal.create_thread(
        name=f"{usuario.display_name} | {usuario.id}",
        type=discord.ChannelType.private_thread,
        invitable=False,
        auto_archive_duration=60,
    )

    await thread.send("Criando chat...")
    await thread.send(embed=embed_chat(usuario))
    await thread.send(usuario.mention)

    if moderador is not None:
        await thread.send(moderador.mention)

    descricao = (
        f"**Usuário:** {usuario} ({usuario.id})\n"
        f"**Tópico:** {thread.mention}\n"
        f"**Link:** {thread.jump_url}"
    )
    if moderador is not None:
        descricao += (
            f"\n**Solicitado por:** {moderador} ({moderador.id})"
        )

    await registrar_log(
        guild,
        "🆕 Chat criado",
        descricao,
        discord.Color.green(),
    )
    return thread


async def obter_ou_criar_chat(
    guild: discord.Guild,
    usuario: discord.Member,
    moderador: discord.Member | None = None,
) -> discord.Thread:
    thread = await procurar_topico(guild, usuario)
    if thread is None:
        return await criar_topico(guild, usuario, moderador)

    descricao = (
        f"**Usuário:** {usuario} ({usuario.id})\n"
        f"**Tópico:** {thread.mention}\n"
        f"**Link:** {thread.jump_url}"
    )
    await thread.send(embed=embed_chat(usuario))

    if moderador is not None:
        descricao += (
            f"\n**Solicitado por:** {moderador} ({moderador.id})"
        )
        await thread.send(moderador.mention)
    else:
        await thread.send(usuario.mention)

    await registrar_log(
        guild,
        "📂 Chat localizado",
        descricao,
        discord.Color.gold(),
    )
    return thread


def eh_staff(membro: discord.Member) -> bool:
    cargos_staff = {cargo_moderador, cargo_administrador}
    return any(cargo.id in cargos_staff for cargo in membro.roles)


def registrar_comando_prefix_chat(bot: commands.Bot) -> None:
    @bot.command(name="chat")
    async def chat(ctx: commands.Context, argumento: str | None = None) -> None:
        if ctx.guild is None:
            await ctx.reply(
                "❌ Este comando só pode ser usado em um servidor.",
                mention_author=False,
            )
            return

        if argumento is None:
            usuario = ctx.author
            thread = await procurar_topico(ctx.guild, usuario)

            if thread is not None:
                await thread.send(usuario.mention)
                await ctx.reply(
                    f"Seu chat: {thread.jump_url}",
                    mention_author=False,
                )
                await registrar_log(
                    ctx.guild,
                    "📂 Chat localizado",
                    (
                        f"**Dono do chat:** {usuario} (`{usuario.id}`)\n"
                        f"**Tópico:** {thread.name}\n"
                        f"**Link:** {thread.jump_url}\n"
                        f"**Comando usado por:** "
                        f"{ctx.author} (`{ctx.author.id}`)"
                    ),
                    discord.Color.gold(),
                )
                return

            thread = await criar_topico(ctx.guild, usuario)
            await ctx.reply(
                f"Seu chat: {thread.jump_url}",
                mention_author=False,
            )
            return

        if ctx.message.mentions:
            usuario = ctx.message.mentions[0]
        else:
            try:
                usuario_id = int(argumento)
            except ValueError:
                await ctx.reply(
                    "❌ Você precisa mencionar um usuário ou informar um ID válido.",
                    mention_author=False,
                )
                return

            usuario = ctx.guild.get_member(usuario_id)
            if usuario is None:
                try:
                    usuario = await ctx.guild.fetch_member(usuario_id)
                except discord.NotFound:
                    await ctx.reply(
                        "❌ Não encontrei esse membro no servidor.",
                        mention_author=False,
                    )
                    return
                except discord.HTTPException:
                    await ctx.reply(
                        "❌ Não foi possível encontrar esse membro.",
                        mention_author=False,
                    )
                    return

        if not eh_staff(ctx.author):
            await ctx.reply(
                "❌ Você não tem permissão para abrir o chat de outra pessoa.",
                mention_author=False,
            )
            return

        cargo_conquista = ctx.guild.get_role(conquista_a_fundacao)
        if (
            cargo_conquista is not None
            and cargo_conquista in usuario.roles
            and cargo_conquista not in ctx.author.roles
        ):
            await ctx.reply(
                "❌ Você não tem permissão para abrir o chat desta pessoa.",
                mention_author=False,
            )
            return

        thread = await procurar_topico(ctx.guild, usuario)
        if thread is not None:
            await thread.send(ctx.author.mention)
            await ctx.reply(
                f"Chat de {usuario.mention}: {thread.jump_url}",
                mention_author=False,
            )
            await registrar_log(
                ctx.guild,
                "📂 Chat localizado",
                (
                    f"**Dono do chat:** {usuario} (`{usuario.id}`)\n"
                    f"**Tópico:** {thread.name}\n"
                    f"**Link:** {thread.jump_url}\n"
                    f"**Solicitado por:** "
                    f"{ctx.author} (`{ctx.author.id}`)"
                ),
                discord.Color.gold(),
            )
            return

        thread = await criar_topico(
            ctx.guild,
            usuario,
            moderador=ctx.author,
        )
        await ctx.reply(
            f"Chat de {usuario.mention}: {thread.jump_url}",
            mention_author=False,
        )
