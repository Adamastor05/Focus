import discord
from discord import app_commands


def registrar_comando_cargo_call(bot, valentes_id, chat_logs_id):

    @bot.tree.command(
        name="cargo_call",
        description="Adiciona um cargo a todos que estão em uma call."
    )
    @app_commands.describe(
        cargo="Cargo que será adicionado",
        call="Call onde estão os membros"
    )
    async def cargo_call(
        interaction: discord.Interaction,
        cargo: discord.Role,
        call: discord.VoiceChannel
    ):

        # ============================================================
        # VERIFICAR SE FOI USADO EM UM SERVIDOR
        # ============================================================

        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em um servidor.",
                ephemeral=True
            )
            return

        # ============================================================
        # VERIFICAR PERMISSÃO — CARGO VALENTES
        # ============================================================

        if not any(
            role.id == valentes_id
            for role in interaction.user.roles
        ):
            await interaction.response.send_message(
                "❌ Você não possui o cargo **Valentes**.",
                ephemeral=True
            )
            return

        # ============================================================
        # VERIFICAR HIERARQUIA DO BOT
        # ============================================================

        bot_member = interaction.guild.me

        if bot_member is None:
            await interaction.response.send_message(
                "❌ Não consegui identificar o bot no servidor.",
                ephemeral=True
            )
            return

        if cargo >= bot_member.top_role:
            await interaction.response.send_message(
                "❌ Não posso adicionar esse cargo porque ele está "
                "acima ou no mesmo nível do meu cargo.",
                ephemeral=True
            )
            return

        # ============================================================
        # PEGAR MEMBROS DA CALL
        # ============================================================

        membros = list(call.members)

        if not membros:
            await interaction.response.send_message(
                f"❌ Não há ninguém na call **{call.name}**.",
                ephemeral=True
            )
            return

        # ============================================================
        # AVISAR AO DISCORD QUE O BOT VAI PROCESSAR
        # ============================================================

        await interaction.response.defer(ephemeral=True)

        adicionados = 0
        ja_possuem = 0
        erros = 0

        # ============================================================
        # ADICIONAR O CARGO
        # ============================================================

        for membro in membros:

            # Já possui o cargo
            if cargo in membro.roles:
                ja_possuem += 1
                continue

            try:

                await membro.add_roles(
                    cargo,
                    reason=(
                        f"/cargo_call usado por "
                        f"{interaction.user} "
                        f"({interaction.user.id})"
                    )
                )

                adicionados += 1

            except discord.Forbidden:
                erros += 1

            except discord.HTTPException:
                erros += 1

        # ============================================================
        # EMBED DE LOG
        # ============================================================

        embed_log = discord.Embed(
            title="🎖️ Cargo distribuído em call",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )

        # Quem executou
        embed_log.add_field(
            name="👤 Executor",
            value=(
                f"{interaction.user.display_name}\n"
                f"`{interaction.user.id}`"
            ),
            inline=False
        )

        # Cargo
        embed_log.add_field(
            name="🎖️ Cargo",
            value=(
                f"{cargo.mention}\n"
                f"`{cargo.id}`"
            ),
            inline=True
        )

        # Call
        embed_log.add_field(
            name="🔊 Call",
            value=(
                f"**{call.name}**\n"
                f"`{call.id}`"
            ),
            inline=True
        )

        # Resultado
        embed_log.add_field(
            name="📊 Resultado",
            value=(
                f"👥 Pessoas na call: **{len(membros)}**\n"
                f"➕ Cargo adicionado: **{adicionados}**\n"
                f"☑️ Já possuíam: **{ja_possuem}**\n"
                f"❌ Erros: **{erros}**"
            ),
            inline=False
        )

        # Servidor
        embed_log.add_field(
            name="🏠 Servidor",
            value=(
                f"{interaction.guild.name}\n"
                f"`{interaction.guild.id}`"
            ),
            inline=False
        )

        embed_log.set_thumbnail(
            url=interaction.user.display_avatar.url
        )

        embed_log.set_footer(
            text="Sistema de distribuição de cargos"
        )

        # ============================================================
        # ENVIAR LOG
        # ============================================================

        canal_logs = interaction.guild.get_channel(chat_logs_id)

        if canal_logs is None:
            try:
                canal_logs = await bot.fetch_channel(chat_logs_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                canal_logs = None

        if canal_logs is not None:

            try:
                await canal_logs.send(
                    embed=embed_log
                )

            except discord.Forbidden:
                print(
                    "[CARGO_CALL] Não tenho permissão "
                    "para enviar mensagem no canal de logs."
                )

            except discord.HTTPException as e:
                print(
                    f"[CARGO_CALL] Erro ao enviar log: {e}"
                )

        # ============================================================
        # RESPOSTA PARA QUEM USOU
        # ============================================================

        mensagem = (
            f"✅ **Cargo distribuído!**\n\n"
            f"**Cargo:** {cargo.mention}\n"
            f"**Call:** **{call.name}**\n\n"
            f"👥 Pessoas na call: **{len(membros)}**\n"
            f"➕ Cargo adicionado: **{adicionados}**\n"
            f"☑️ Já possuíam o cargo: **{ja_possuem}**"
        )

        if erros > 0:
            mensagem += (
                f"\n❌ Não foi possível adicionar: **{erros}**"
            )

        await interaction.followup.send(
            mensagem,
            ephemeral=True
        )