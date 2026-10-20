import discord
from discord import app_commands
from discord.ext import commands


def registrar_comando_criar_ticket(
    bot: commands.Bot,
    cargo_moderador: int,
    criar_ticket_entrada,
) -> None:
    @bot.tree.command(
        name="criar_ticket",
        description="Cria manualmente o ticket de entrada de um membro.",
    )
    @app_commands.describe(
        usuario="Membro que receberá o ticket",
    )
    async def criar_ticket(
        interaction: discord.Interaction,
        usuario: discord.Member,
    ) -> None:
        if not any(
            cargo.id == cargo_moderador
            for cargo in interaction.user.roles
        ):
            await interaction.response.send_message(
                "❌ Você não tem permissão.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)
        await criar_ticket_entrada(usuario)

        await interaction.followup.send(
            f"✅ Ticket criado para {usuario.mention}.",
            ephemeral=True,
        )
