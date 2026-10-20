import discord
from discord import app_commands


def registrar_comando_criar_convite(
    bot,
    cargo_administrador: int
):
    @bot.tree.command(name="criar_convite", description="Cria um convite permanente para um canal.")
    @app_commands.describe(canal="Canal onde o convite será criado")
    async def criar_convite(interaction: discord.Interaction, canal: discord.TextChannel):

        if cargo_administrador not in [cargo.id for cargo in interaction.user.roles]:
            await interaction.response.send_message(
                "❌ Você não tem permissão para usar este comando.",
                ephemeral=True
            )
            return

        try:
            convite = await canal.create_invite(
                max_age=0,      # Nunca expira
                max_uses=0,     # Usos ilimitados
                unique=True,
                reason=f"Criado por {interaction.user}"
            )

            await interaction.response.send_message(
                f"✅ Convite criado:\n{convite.url}",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Não tenho permissão para criar convites nesse canal.",
                ephemeral=True
            )