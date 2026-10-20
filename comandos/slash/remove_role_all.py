import asyncio
import time

import discord
from discord import app_commands
from discord.ext import commands


def registrar_comando_remove_role_all(
    bot: commands.Bot,
    cargo_administrador_id: int,
) -> None:
    @bot.tree.command(
        name="remove_role_all",
        description="Remove um cargo de todos os membros.",
    )
    @app_commands.describe(
        cargo="Cargo que será removido de todos.",
    )
    async def remove_role_all(
        interaction: discord.Interaction,
        cargo: discord.Role,
    ) -> None:
        if not any(
            role.id == cargo_administrador_id
            for role in interaction.user.roles
        ):
            await interaction.response.send_message(
                "Você não possui permissão para usar este comando.",
                ephemeral=True,
            )
            return

        if interaction.guild is None:
            await interaction.response.send_message(
                "Este comando só pode ser usado em um servidor.",
                ephemeral=True,
            )
            return

        membros = [
            membro
            for membro in interaction.guild.members
            if cargo in membro.roles
        ]

        if not membros:
            await interaction.response.send_message(
                "Ninguém possui esse cargo.",
                ephemeral=True,
            )
            return

        estimativa = len(membros) * 0.4
        minutos = int(estimativa // 60)
        segundos = int(estimativa % 60)

        if minutos:
            tempo_texto = f"{minutos} min {segundos} s"
        else:
            tempo_texto = f"{segundos} s"

        await interaction.response.send_message(
            f"Removendo **{cargo.name}** de **{len(membros)}** membros.\n"
            f"⏳ Tempo estimado: **{tempo_texto}**."
        )

        inicio = time.perf_counter()
        removidos = 0
        falhas = 0

        for membro in membros:
            try:
                await membro.remove_roles(
                    cargo,
                    reason=f"Remoção em massa por {interaction.user}",
                )
                removidos += 1
            except (discord.Forbidden, discord.HTTPException):
                falhas += 1

            await asyncio.sleep(0.4)

        tempo_real = round(time.perf_counter() - inicio, 1)
        await interaction.followup.send(
            f"✅ Processo concluído!\n"
            f"Cargo removido de **{removidos}** membro(s).\n"
            f"❌ Falhas: **{falhas}** membro(s).\n"
            f"⏱️ Tempo gasto: **{tempo_real} segundos**."
        )
