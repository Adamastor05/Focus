import discord
from discord import app_commands
from discord.ext import commands


def registrar_comando_limpar_dm(
    bot: commands.Bot,
    cargo_moderador_id: int,
) -> None:
    @bot.tree.command(
        name="limpar_dm",
        description="Apaga as mensagens do bot na DM de um usuário.",
    )
    @app_commands.describe(
        membro="Selecione o usuário.",
    )
    async def limpar_dm(
        interaction: discord.Interaction,
        membro: discord.Member,
    ) -> None:
        if not any(
            cargo.id == cargo_moderador_id
            for cargo in interaction.user.roles
        ):
            await interaction.response.send_message(
                "❌ Você não possui permissão para usar este comando.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            dm = await membro.create_dm()
            apagadas = 0

            async for mensagem in dm.history(limit=None):
                if mensagem.author.id != bot.user.id:
                    continue

                try:
                    await mensagem.delete()
                    apagadas += 1
                except discord.HTTPException:
                    continue

            await interaction.followup.send(
                f"✅ Apaguei {apagadas} mensagens da DM de {membro.mention}.",
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Não foi possível acessar a DM desse usuário.",
                ephemeral=True,
            )
