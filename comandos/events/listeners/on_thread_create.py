import asyncio
import discord


def registrar_evento_on_thread_create(
    bot,
    chat_logs: int
):
      
    canais_ping_novo_forum = [
        1387612050917953676, #pedidos de oracao
        1432187527447711825, #pregações
        1417906970706579599, #leitura diária
        1367167818117681305, #dúvidas
        1353534352474247168, #temas gerais
        1387978457635356693, #debates
        1517362589385097326, #artes
        1347727626910826554, #divulgação
        1440861614025740308, #louvores
    ]
    canal_apresentacoes = 1363009444111188129
    cargo_apresentado = 1455035687156973788

    @bot.event
    async def on_thread_create(thread: discord.Thread):
        #region Detectar Threads
        await asyncio.sleep(1)

        if thread.parent is None:
            return

        if not isinstance(thread.parent, discord.ForumChannel):
            return

        autor = thread.owner

        # Caso owner ainda não esteja disponível
        if autor is None:
            try:
                autor = await bot.fetch_user(thread.owner_id)
            except:
                autor = None

        canal_logs = bot.get_channel(chat_logs)
        #endregion
        #region Marcar Ping Novo Fórum
        if thread.parent.id in canais_ping_novo_forum:

            msg = await thread.send(
                "<@&1455326865446408315>"
            )

            await asyncio.sleep(7)
            await msg.delete()

            if canal_logs:
                embed = discord.Embed(
                    title="🆕 Novo tópico criado",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="Criado por",
                    value=f"{autor.mention if autor else 'Desconhecido'}",
                    inline=False
                )
                embed.add_field(
                    name="Canal",
                    value=thread.parent.mention,
                    inline=False
                )
                embed.add_field(
                    name="Tópico",
                    value=f"[Clique aqui]({thread.jump_url})",
                    inline=False
                )
                embed.add_field(
                    name="Ação",
                    value="Mensagem temporária enviada e apagada após 7 segundos.",
                    inline=False
                )
                await canal_logs.send(embed=embed)
            return
        #endregion
        #region Marcar Ping Recepcionistas
        if thread.parent.id == canal_apresentacoes:

            await thread.send(
                "<@&1555543123638231120>"
            )

            membro = thread.guild.get_member(thread.owner_id)

            if membro:
                cargo = thread.guild.get_role(cargo_apresentado)

                if cargo:
                    await membro.add_roles(
                        cargo,
                        reason="Criou uma apresentação."
                    )

            if canal_logs:
                embed = discord.Embed(
                    title="👋 Nova apresentação",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="Criado por",
                    value=f"{autor.mention if autor else 'Desconhecido'}",
                    inline=False
                )
                embed.add_field(
                    name="Canal",
                    value=thread.parent.mention,
                    inline=False
                )
                embed.add_field(
                    name="Tópico",
                    value=f"[Clique aqui]({thread.jump_url})",
                    inline=False
                )
                embed.add_field(
                    name="Ações",
                    value=(
                        "• Mensagem enviada no tópico.\n"
                        "• Cargo de apresentado concedido."
                    ),
                    inline=False
                )
                await canal_logs.send(embed=embed)
                #endregion
    #endregion