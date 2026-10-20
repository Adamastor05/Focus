import asyncio
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands


def registrar_comando_adicionar_cargo_3d(
    bot: commands.Bot,
    cargo_administrador_id: int,
    chat_logs_id: int,
) -> None:
    @bot.tree.command(
        name="adicionar_cargo_3d",
        description="Adiciona um cargo a quem enviou mensagem nos últimos 3 dias.",
    )
    @app_commands.describe(
        cargo="Cargo que será adicionado",
    )
    async def adicionar_cargo_3d(
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
            role.id == cargo_administrador_id
            for role in interaction.user.roles
        ):
            await interaction.response.send_message(
                "Você não possui permissão para usar este comando.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)
        limite = datetime.now(timezone.utc) - timedelta(days=3)
        membros_ativos = set()
        canais_com_erro = 0

        for canal in interaction.guild.text_channels:
            try:
                async for mensagem in canal.history(after=limite, limit=None):
                    if mensagem.author.bot:
                        continue

                    membro = interaction.guild.get_member(mensagem.author.id)
                    if membro is not None:
                        membros_ativos.add(membro)

                await asyncio.sleep(0.5)
            except discord.HTTPException:
                canais_com_erro += 1

        adicionados = 0
        erros = 0

        for membro in membros_ativos:
            if cargo in membro.roles:
                continue

            try:
                await membro.add_roles(
                    cargo,
                    reason="Enviou mensagem nos últimos 3 dias.",
                )
                adicionados += 1
            except discord.HTTPException:
                erros += 1

        canal_logs = interaction.guild.get_channel(chat_logs_id)
        erro_log = False

        if canal_logs is not None:
            embed = discord.Embed(
                title="📋 Cargo adicionado aos membros ativos",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow(),
            )
            embed.add_field(
                name="Executado por",
                value=f"{interaction.user} (`{interaction.user.id}`)",
                inline=False,
            )
            embed.add_field(
                name="Cargo adicionado",
                value=f"`{cargo.name}`",
                inline=False,
            )
            embed.add_field(
                name="Período analisado",
                value="Últimos **3 dias**",
                inline=False,
            )
            embed.add_field(
                name="Resultado",
                value=(
                    f"**Membros ativos encontrados:** {len(membros_ativos)}\n"
                    f"**Cargo adicionado:** {adicionados}\n"
                    f"**Erros ao adicionar:** {erros}\n"
                    f"**Canais não analisados:** {canais_com_erro}"
                ),
                inline=False,
            )

            try:
                await canal_logs.send(embed=embed)
            except discord.HTTPException:
                erro_log = True
        else:
            erro_log = True

        resultado = (
            f"Concluído!\n\n"
            f"👥 Membros ativos encontrados: **{len(membros_ativos)}**\n"
            f"✅ Cargo adicionado: **{adicionados}**\n"
            f"❌ Erros ao adicionar: **{erros}**\n"
            f"⚠️ Canais não analisados: **{canais_com_erro}**"
        )
        if erro_log:
            resultado += "\n⚠️ Não foi possível enviar o registro ao canal de logs."

        await interaction.followup.send(resultado, ephemeral=True)
