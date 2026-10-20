import discord
from discord import app_commands


def registrar_comando_mensagem_do_dia(
    bot,
    cargo_focus_adm_id,
    cargo_administrador_id,
    chat_mensagem_do_dia_id,
    chat_logs_id
):

    @bot.tree.command(
        name="mensagem_do_dia",
        description="Envia a mensagem do dia."
    )
    @app_commands.describe(
        ping_pregacoes="Ativa ou desativa o ping de pregações."
    )
    async def mensagem_do_dia(
        interaction: discord.Interaction,
        ping_pregacoes: bool = False
    ):

        # ============================================================
        # VERIFICAR SE É SERVIDOR
        # ============================================================

        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em um servidor.",
                ephemeral=True
            )
            return

        # ============================================================
        # VERIFICAR PERMISSÃO
        # ============================================================

        cargos_usuario = [
            cargo.id for cargo in interaction.user.roles
        ]

        if (
            cargo_focus_adm_id not in cargos_usuario
            and cargo_administrador_id not in cargos_usuario
        ):
            await interaction.response.send_message(
                "❌ Você não possui permissão para usar este comando.",
                ephemeral=True
            )
            return

        # ============================================================
        # VERIFICAR CANAL
        # ============================================================

        if interaction.channel_id != chat_mensagem_do_dia_id:
            await interaction.response.send_message(
                "❌ Este comando só pode ser usado no canal "
                "de mensagem do dia.",
                ephemeral=True
            )
            return

        # ============================================================
        # AVISAR AO DISCORD QUE VAI PROCESSAR
        # ============================================================

        await interaction.response.defer(ephemeral=True)

        canal = interaction.channel

        # ============================================================
        # APAGAR MENSAGENS ANTERIORES DO BOT
        # ============================================================

        mensagens_do_bot = []

        async for mensagem in canal.history(limit=None):

            if mensagem.author.id == bot.user.id:
                mensagens_do_bot.append(mensagem)

        for mensagem in mensagens_do_bot:

            try:
                await mensagem.delete()

            except discord.NotFound:
                pass

            except discord.Forbidden:
                print(
                    "[MENSAGEM DO DIA] "
                    "Não tenho permissão para apagar uma mensagem."
                )

            except discord.HTTPException as e:
                print(
                    f"[MENSAGEM DO DIA] "
                    f"Erro ao apagar mensagem: {e}"
                )

        # ============================================================
        # PEGAR A ÚLTIMA MENSAGEM DO CHAT
        # ============================================================

        ultima_mensagem = None

        async for mensagem in canal.history(limit=1):
            ultima_mensagem = mensagem
            break

        # ============================================================
        # DEFINIR MENSAGEM
        # ============================================================

        if ping_pregacoes:

            conteudo = (
                "<@&1479934468277141596> "
                "<@&1408502391615262730>"
            )

        else:

            conteudo = (
                "<@&1479934468277141596>"
            )

        # ============================================================
        # ENVIAR NOVA MENSAGEM
        # ============================================================

        if ultima_mensagem is not None:

            nova_mensagem = await canal.send(
                conteudo,
                reference=ultima_mensagem,
                allowed_mentions=discord.AllowedMentions(
                    roles=True
                )
            )

        else:

            nova_mensagem = await canal.send(
                conteudo,
                allowed_mentions=discord.AllowedMentions(
                    roles=True
                )
            )

        # ============================================================
        # LOG
        # ============================================================

        embed_log = discord.Embed(
            title="📅 Mensagem do Dia atualizada",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )

        embed_log.add_field(
            name="👤 Quem usou",
            value=(
                f"{interaction.user.display_name}\n"
                f"`{interaction.user.id}`"
            ),
            inline=False
        )

        embed_log.add_field(
            name="📍 Canal",
            value=(
                f"<#{chat_mensagem_do_dia_id}>\n"
                f"`{chat_mensagem_do_dia_id}`"
            ),
            inline=True
        )

        embed_log.add_field(
            name="📢 Ping de pregações",
            value=(
                "🟢 Ativado"
                if ping_pregacoes
                else "🔴 Desativado"
            ),
            inline=True
        )

        embed_log.add_field(
            name="💬 Mensagem enviada",
            value=conteudo,
            inline=False
        )

        embed_log.add_field(
            name="🗑️ Mensagens do bot apagadas",
            value=str(len(mensagens_do_bot)),
            inline=False
        )

        embed_log.set_thumbnail(
            url=interaction.user.display_avatar.url
        )

        embed_log.set_footer(
            text="Sistema de Mensagem do Dia"
        )

        # ============================================================
        # ENCONTRAR CANAL DE LOGS
        # ============================================================

        canal_logs = interaction.guild.get_channel(
            chat_logs_id
        )

        if canal_logs is None:

            try:
                canal_logs = await bot.fetch_channel(
                    chat_logs_id
                )

            except (
                discord.NotFound,
                discord.Forbidden,
                discord.HTTPException
            ):
                canal_logs = None

        # ============================================================
        # ENVIAR LOG
        # ============================================================

        if canal_logs is not None:

            try:

                await canal_logs.send(
                    embed=embed_log,
                    allowed_mentions=discord.AllowedMentions.none()
                )

            except discord.Forbidden:

                print(
                    "[MENSAGEM DO DIA] "
                    "Não tenho permissão para enviar "
                    "mensagens no canal de logs."
                )

            except discord.HTTPException as e:

                print(
                    f"[MENSAGEM DO DIA] "
                    f"Erro ao enviar log: {e}"
                )

        # ============================================================
        # RESPOSTA EFÊMERA
        # ============================================================

        await interaction.followup.send(
            (
                "✅ **Mensagem do Dia atualizada com sucesso!**\n\n"
                f"📢 Ping de pregações: "
                f"**{'Ativado' if ping_pregacoes else 'Desativado'}**"
            ),
            ephemeral=True
        )