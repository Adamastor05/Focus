import discord
from discord import app_commands
import asyncio



def registrar_comando_desligar_focus(
    bot,
    cargo_focus_adm_id,
    cargo_administrador_id,
    chat_logs
):

    @bot.tree.command(
        name="desligar_focus",
        description="Desliga o bot Focus."
    )
    async def desligar_focus(interaction: discord.Interaction):

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
                "❌ Você não possui permissão para desligar o Focus.",
                ephemeral=True
            )
            return

        # ============================================================
        # RESPONDER AO USUÁRIO
        # ============================================================

        await interaction.response.send_message(
            "🔴 **Focus está sendo desligado...**",
            ephemeral=False
        )

        # ============================================================
        # LOG
        # ============================================================

        embed_log = discord.Embed(
            title="🔴 Focus sendo desligado",
            description=(
                "O bot está sendo desligado através do comando "
                "`/desligar_focus`."
            ),
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )

        embed_log.add_field(
            name="👤 Desligado por",
            value=(
                f"{interaction.user.display_name}\n"
                f"`{interaction.user.id}`"
            ),
            inline=False
        )

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
            text="Sistema de desligamento do Focus"
        )

        # ============================================================
        # ENVIAR LOG
        # ============================================================

        canal_logs = interaction.guild.get_channel(chat_logs)

        if canal_logs is None:
            try:
                canal_logs = await bot.fetch_channel(chat_logs)
            except (
                discord.NotFound,
                discord.Forbidden,
                discord.HTTPException
            ):
                canal_logs = None

        if canal_logs is not None:

            try:
                await canal_logs.send(
                    embed=embed_log
                )

            except discord.Forbidden:
                print(
                    "[DESLIGAR] Não tenho permissão "
                    "para enviar mensagens no canal de logs."
                )

            except discord.HTTPException as e:
                print(
                    f"[DESLIGAR] Erro ao enviar log: {e}"
                )

        # ============================================================
        # LOG NO TERMINAL
        # ============================================================

        print(
            f"[DESLIGAR] Focus desligado por "
            f"{interaction.user} ({interaction.user.id})"
        )

        # ============================================================
        # DESLIGAR O BOT
        # ============================================================
        await asyncio.sleep(2)
        await bot.close()