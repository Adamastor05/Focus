import discord

from config.IDs import chat_logs, ping_staff


def registrar_evento_on_message(bot):
    @bot.event
    async def on_message(message: discord.Message):
        if message.author.bot:
            return

        # !!!!!!!DESATIVADA POR ENQUNTO!!!!!!!!!
        # ANÁLISE AUTOMÁTICA DE IMAGENS -------------------------------
        #   await analisar_mensagem_de_imagem(
        #       bot,
        #       message
        #   )

        # PING STAFF ------------------------------------------------------------
        # Verifica se o cargo foi mencionado
        if any(role.id == ping_staff for role in message.role_mentions):

            cargo = message.guild.get_role(ping_staff)
            canal_logs = message.guild.get_channel(chat_logs)

            if cargo:
                link = message.jump_url

                texto = (
                    f"🚨 **O cargo {cargo.name} foi marcado no servidor Bíblia em Foco.**\n\n"
                    f"**Quem marcou:** {message.author.mention} ({message.author})\n"
                    f"**Canal:** {message.channel.mention}\n\n"
                    f"**Mensagem:**\n"
                    f"{message.content}\n\n"
                    f"**Ir para a mensagem:**\n{link}"
                )

                for membro in cargo.members:
                    if membro.bot:
                        continue

                    try:
                        await membro.send(texto)
                    except (discord.Forbidden, discord.HTTPException):
                        pass

                if canal_logs:
                    await canal_logs.send(texto)

        # MENSAGEM NA DM ----------------------------------------------------
        # Ignora mensagens do próprio bot
        if message.author.bot:
            return

        # Verifica se é uma mensagem privada
        if isinstance(message.channel, discord.DMChannel):

            canal_logs = bot.get_channel(chat_logs)

            if canal_logs:
                embed = discord.Embed(
                    title="📩 Mensagem privada recebida",
                    color=discord.Color.blue()
                )
                embed.set_thumbnail(url=message.author.display_avatar.url)
                embed.add_field(
                    name="Usuário",
                    value=f"{message.author.mention}\n`{message.author.id}`",
                    inline=False
                )
                embed.add_field(
                    name="Mensagem",
                    value=message.content or "*Sem texto*",
                    inline=False
                )
                if message.attachments:
                    arquivos = "\n".join(anexo.url for anexo in message.attachments)
                    embed.add_field(
                        name="Anexos",
                        value=arquivos,
                        inline=False
                    )
                await canal_logs.send(embed=embed)
        # Mantém os comandos por prefixo funcionando
        await bot.process_commands(message)
