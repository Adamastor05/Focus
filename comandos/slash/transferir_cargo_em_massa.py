import discord
from discord import app_commands
from discord.ext import commands


def registrar_comando_transferir_cargo_em_massa(
    bot: commands.Bot,
    cargo_administrador_id: int,
    chat_logs_id: int,
) -> None:
    @bot.tree.command(
        name="transferir_cargo_em_massa",
        description="Remove um cargo e adiciona outro em todos os membros.",
    )
    @app_commands.describe(
        cargo_base="Cargo que será removido",
        cargo_destino="Cargo que será adicionado",
        exceto_1="Quem possuir este cargo será ignorado",
        exceto_2="Quem possuir este cargo será ignorado",
        exceto_3="Quem possuir este cargo será ignorado",
        exceto_4="Quem possuir este cargo será ignorado",
    )
    async def transferir_cargo_em_massa(
        interaction: discord.Interaction,
        cargo_base: discord.Role,
        cargo_destino: discord.Role,
        exceto_1: discord.Role | None = None,
        exceto_2: discord.Role | None = None,
        exceto_3: discord.Role | None = None,
        exceto_4: discord.Role | None = None,
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

        excecoes = {
            role
            for role in (exceto_1, exceto_2, exceto_3, exceto_4)
            if role is not None
        }

        transferidos = 0
        ignorados = 0
        erros = 0

        for membro in interaction.guild.members:
            if cargo_base not in membro.roles:
                continue

            if any(role in membro.roles for role in excecoes):
                ignorados += 1
                continue

            try:
                await membro.remove_roles(
                    cargo_base,
                    reason=(
                        "Transferência em massa realizada por "
                        f"{interaction.user}"
                    ),
                )

                if cargo_destino not in membro.roles:
                    await membro.add_roles(
                        cargo_destino,
                        reason=(
                            "Transferência em massa realizada por "
                            f"{interaction.user}"
                        ),
                    )

                transferidos += 1
            except (discord.Forbidden, discord.HTTPException):
                erros += 1

        canal_logs = interaction.guild.get_channel(chat_logs_id)
        if canal_logs is not None:
            embed_logs = discord.Embed(
                title="📦 Transferência de cargos em massa",
                color=discord.Color.orange(),
                timestamp=discord.utils.utcnow(),
            )
            embed_logs.add_field(
                name="Executado por",
                value=f"{interaction.user} (`{interaction.user.id}`)",
                inline=False,
            )
            embed_logs.add_field(
                name="Cargo base",
                value=f"`{cargo_base.name}`",
                inline=True,
            )
            embed_logs.add_field(
                name="Cargo destino",
                value=f"`{cargo_destino.name}`",
                inline=True,
            )

            excecoes_texto = (
                "\n".join(f"`{role.name}`" for role in excecoes)
                if excecoes
                else "Nenhuma"
            )
            embed_logs.add_field(
                name="Cargos de exceção",
                value=excecoes_texto,
                inline=False,
            )
            embed_logs.add_field(
                name="Resultado",
                value=(
                    f"**Transferidos:** {transferidos}\n"
                    f"**Ignorados:** {ignorados}\n"
                    f"**Erros:** {erros}"
                ),
                inline=False,
            )
            await canal_logs.send(embed=embed_logs)

        embed = discord.Embed(
            title="Transferência concluída",
            color=discord.Color.green(),
        )
        embed.add_field(
            name="Transferidos",
            value=str(transferidos),
            inline=True,
        )
        embed.add_field(
            name="Ignorados",
            value=str(ignorados),
            inline=True,
        )
        embed.add_field(
            name="Erros",
            value=str(erros),
            inline=True,
        )

        await interaction.followup.send(embed=embed, ephemeral=True)
