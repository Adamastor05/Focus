
def registrar_comando_prefix_registro(
    bot,
    cargo_moderador,
    chat_registro
):
    @bot.command(name="registro", aliases=["r"])
    async def registro(ctx, user_id: str):
        if cargo_moderador not in [role.id for role in ctx.author.roles]:
            return
        forum = bot.get_channel(chat_registro)

        if forum is None:
            await ctx.reply("Não encontrei o fórum de registros.")
            return

        encontrados = []

        # Threads ativas
        for thread in forum.threads:
            if user_id in thread.name:
                encontrados.append(thread)

        # Threads arquivadas
        async for thread in forum.archived_threads(limit=None):
            if user_id in thread.name:
                encontrados.append(thread)

        if not encontrados:
            await ctx.reply("Nenhum registro encontrado para esse ID.")
            return

        links = "\n".join(thread.jump_url for thread in encontrados)

        await ctx.reply(
            f"Encontrei {len(encontrados)} registro(s):\n{links}",
            mention_author=False
        )