import json
import re
from datetime import datetime
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands


def registrar_comando_salvar_ids_cargo(
    bot: commands.Bot,
    cargo_administrador: int,
    chat_logs: int,
) -> None:
    @bot.tree.command(
        name="salvar_ids_cargo",
        description="Salva os IDs de todos os membros de um cargo.",
    )
    @app_commands.describe(
        cargo="Cargo cujos membros serão salvos",
    )
    async def salvar_ids_cargo(
        interaction: discord.Interaction,
        cargo: discord.Role,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "Este comando só pode ser usado em um servidor.",
                ephemeral=True,
            )
            return

        if not any(
            role.id == cargo_administrador
            for role in interaction.user.roles
        ):
            await interaction.response.send_message(
                "❌ Você não tem permissão para usar este comando.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "💾 Estou salvando os IDs...",
            ephemeral=True,
        )

        pasta_dados = Path("dados")
        pasta_dados.mkdir(exist_ok=True)

        nome_cargo = re.sub(r'[<>:"/\\|?*]', "_", cargo.name).replace(" ", "_")
        data = datetime.now().strftime("%d-%m-%Y")
        caminho = pasta_dados / f"{nome_cargo}_{data}.json"
        ids = [membro.id for membro in cargo.members]

        with caminho.open("w", encoding="utf-8") as arquivo:
            json.dump(ids, arquivo, indent=4)

        await interaction.followup.send(
            f"✅ Salvei todos os IDs do cargo **{cargo.name}** "
            f"({len(ids)} membros).",
            ephemeral=True,
        )

        canal_logs = interaction.guild.get_channel(chat_logs)
        if canal_logs is not None:
            await canal_logs.send(
                f"🗂️ {interaction.user.mention} salvou os IDs do cargo "
                f"**{cargo.name}** ({len(ids)} membros)."
            )
