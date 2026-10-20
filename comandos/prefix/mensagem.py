
def registrar_comando_mensagem(
    bot,
    discord,
    re,
    cargo_moderador,
    cargo_recepcionista,
    chat_logs,
):
    @bot.command(name="mensagem", aliases=["m"])
    async def mensagem(ctx, *, texto=None):
        if not any(role.id in (cargo_moderador, cargo_recepcionista) for role in ctx.author.roles):
            await ctx.reply(
                "Você não tem permissão para usar este comando.",
                mention_author=False,
            )
            return
        if texto is None:
            await ctx.reply("Uso: `;m [id_do_chat ou #canal] mensagem`")
            return

        canal_destino = ctx.channel
        mensagem = texto

        partes = texto.split(maxsplit=1)

        if partes:
            primeiro = partes[0]

            # Caso seja um ID de canal
            if primeiro.isdigit():
                canal = bot.get_channel(int(primeiro))
                if canal:
                    canal_destino = canal
                    mensagem = partes[1] if len(partes) > 1 else ""

            # Caso seja uma menção de canal (<#id>)
            else:
                match = re.match(r"<#(\d+)>", primeiro)
                if match:
                    canal = bot.get_channel(int(match.group(1)))
                    if canal:
                        canal_destino = canal
                        mensagem = partes[1] if len(partes) > 1 else ""

        if not mensagem.strip():
            await ctx.reply("Você não informou a mensagem.")
            return

        # Envia a mensagem
        await canal_destino.send(mensagem)

        # Registra nos logs
        canal_logs = bot.get_channel(chat_logs)
        if canal_logs:
            await canal_logs.send(
                f"📨 **Mensagem enviada pelo comando ;m**\n"
                f"**Autor:** {ctx.author} ({ctx.author.id})\n"
                f"**Canal de origem:** {ctx.channel.mention} ({ctx.channel.id})\n"
                f"**Canal de destino:** {canal_destino.mention} ({canal_destino.id})\n"
                f"**Mensagem:**\n```{mensagem}```"
            )

        # Apaga a mensagem do comando
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass