
def registrar_comando_prefix_registrom(
        bot,
        cargo_moderador,
        chat_registro,
        asyncio,
):
    @bot.command(name="registrom", aliases=["rm"])
    async def registrom(ctx, user_id: str):
        if cargo_moderador not in [role.id for role in ctx.author.roles]:
            return
        forum = bot.get_channel(chat_registro)

        if forum is None:
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

        # Apaga a mensagem do comando
        try:
            await ctx.message.delete()
        except:
            pass

        if not encontrados:
            msg = await ctx.send("Nenhum registro encontrado.")
            await asyncio.sleep(7)
            await msg.delete()
            return

        # Quem usou o comando
        autor = ctx.author

        for thread in encontrados:
            try:
                mensagem = await thread.send(autor.mention)
                await asyncio.sleep(7)
                await mensagem.delete()
            except:
                pass