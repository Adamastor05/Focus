import re

import discord
from discord import app_commands
from discord.ext import commands


def converter_hex(codigo: str) -> discord.Colour | None:
    codigo = codigo.strip()

    if codigo.startswith("#"):
        codigo = codigo[1:]

    if not re.fullmatch(r"[0-9A-Fa-f]{6}", codigo):
        return None

    return discord.Colour(int(codigo, 16))


def registrar_comando_cor(
    bot: commands.Bot,
    cargo_booster_id: int,
    chat_logs_thread_boosters_id: int,
) -> None:
    @bot.tree.command(
        name="cor",
        description="Define a cor do seu cargo de booster.",
    )
    @app_commands.describe(
        codigo="Código hexadecimal da cor principal. Ex: #FF0000",
        degradê="Código hexadecimal da segunda cor. Ex: #0000FF",
    )
    async def cor(
        interaction: discord.Interaction,
        codigo: str,
        degradê: str | None = None,
    ) -> None:
        guild = interaction.guild
        member = interaction.user

        if guild is None or not isinstance(member, discord.Member):
            await interaction.response.send_message(
                "❌ Este comando só pode ser usado dentro de um servidor.",
                ephemeral=True,
            )
            return

        role_booster = guild.get_role(cargo_booster_id)
        if role_booster is None:
            await interaction.response.send_message(
                "❌ O cargo de booster configurado no bot não foi encontrado.",
                ephemeral=True,
            )
            return
        if role_booster not in member.roles:
            await interaction.response.send_message(
                "❌ Você precisa ter o cargo de booster para usar este comando.",
                ephemeral=True,
            )
            return

        bot_member = guild.me
        if bot_member is None:
            await interaction.response.send_message(
                "❌ Não consegui identificar o cargo do bot neste servidor.",
                ephemeral=True,
            )
            return
        if not bot_member.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "❌ Eu preciso da permissão **Gerenciar Cargos** para fazer isso.",
                ephemeral=True,
            )
            return

        cor_principal = converter_hex(codigo)
        if cor_principal is None:
            await interaction.response.send_message(
                "❌ O código hexadecimal da cor principal é inválido.\n"
                "Use o formato `#FFFFFF` ou `FFFFFF`.",
                ephemeral=True,
            )
            return

        cor_secundaria = None
        if degradê is not None:
            cor_secundaria = converter_hex(degradê)
            if cor_secundaria is None:
                await interaction.response.send_message(
                    "❌ O código hexadecimal do degradê é inválido.\n"
                    "Use o formato `#FFFFFF` ou `FFFFFF`.",
                    ephemeral=True,
                )
                return

            if "ENHANCED_ROLE_STYLES" not in guild.features:
                await interaction.response.send_message(
                    "❌ Este servidor não possui a opção de cargos com "
                    "degradê ativada atualmente.",
                    ephemeral=True,
                )
                return

        nome_cargo = f"🎨 {member.name}"
        role = discord.utils.get(guild.roles, name=nome_cargo)

        if role is not None:
            if role.is_default():
                role = None
            elif role.managed:
                await interaction.response.send_message(
                    "❌ Encontrei um cargo com esse nome, mas ele é "
                    "gerenciado pelo Discord e não pode ser alterado.",
                    ephemeral=True,
                )
                return
            elif role >= bot_member.top_role:
                await interaction.response.send_message(
                    "❌ O cargo de cor está acima ou no mesmo nível do "
                    "meu cargo. Não consigo editá-lo.",
                    ephemeral=True,
                )
                return

        acao = None
        if role is None:
            try:
                role = await guild.create_role(
                    name=nome_cargo,
                    colour=cor_principal,
                    secondary_colour=cor_secundaria,
                    reason=f"Cargo de cor do booster {member} ({member.id})",
                )
            except discord.Forbidden:
                await interaction.response.send_message(
                    "❌ Não tenho permissão para criar cargos.",
                    ephemeral=True,
                )
                return
            except discord.HTTPException:
                await interaction.response.send_message(
                    "❌ O Discord recusou a criação do cargo. Tente novamente.",
                    ephemeral=True,
                )
                return

            try:
                await guild.edit_role_positions(
                    positions={role: bot_member.top_role.position - 1},
                    reason=f"Posicionando cargo de cor de {member}",
                )
            except discord.Forbidden:
                await interaction.response.send_message(
                    "⚠️ O cargo foi criado, mas não consegui posicioná-lo "
                    "abaixo do meu cargo. Verifique minha hierarquia.",
                    ephemeral=True,
                )
                return
            except discord.HTTPException:
                await interaction.response.send_message(
                    "⚠️ O cargo foi criado, mas ocorreu um erro ao "
                    "posicioná-lo.",
                    ephemeral=True,
                )
                return

            acao = "Cargo criado"
        else:
            try:
                role = await role.edit(
                    colour=cor_principal,
                    secondary_colour=cor_secundaria,
                    reason=(
                        f"Alteração de cor pelo booster {member} ({member.id})"
                    ),
                )
            except discord.Forbidden:
                await interaction.response.send_message(
                    "❌ Não tenho permissão para editar esse cargo.",
                    ephemeral=True,
                )
                return
            except discord.HTTPException:
                await interaction.response.send_message(
                    "❌ O Discord recusou a alteração do cargo.",
                    ephemeral=True,
                )
                return

            acao = "Cargo atualizado"

        if role not in member.roles:
            try:
                await member.add_roles(
                    role,
                    reason=f"Cargo de cor do booster {member} ({member.id})",
                )
            except discord.Forbidden:
                await interaction.response.send_message(
                    "⚠️ A cor foi configurada, mas não consegui "
                    "adicionar o cargo a você.",
                    ephemeral=True,
                )
                return
            except discord.HTTPException:
                await interaction.response.send_message(
                    "⚠️ A cor foi configurada, mas ocorreu um erro "
                    "ao adicionar o cargo.",
                    ephemeral=True,
                )
                return

        if cor_secundaria is not None:
            mensagem = (
                f"🎨 Sua cor foi atualizada!\n\n"
                f"**Cor principal:** `{codigo.upper()}`\n"
                f"**Degradê:** `{degradê.upper()}`\n"
                f"**Cargo:** {role.mention}"
            )
            tipo_cor = "Degradê"
        else:
            mensagem = (
                f"🎨 Sua cor foi atualizada!\n\n"
                f"**Cor:** `{codigo.upper()}`\n"
                f"**Cargo:** {role.mention}"
            )
            tipo_cor = "Cor única"

        await interaction.response.send_message(mensagem, ephemeral=True)

        log_thread = guild.get_thread(chat_logs_thread_boosters_id)
        if log_thread is None:
            canal = guild.get_channel(chat_logs_thread_boosters_id)
            if isinstance(canal, discord.Thread):
                log_thread = canal

        if log_thread is not None:
            embed = discord.Embed(
                title="🎨 Alteração de cor de Booster",
                colour=cor_principal,
            )
            embed.add_field(
                name="Usuário",
                value=f"{member.mention}\n`{member.name}`\n`{member.id}`",
                inline=False,
            )
            embed.add_field(
                name="Cargo",
                value=f"{role.mention}\n`{role.name}`\n`{role.id}`",
                inline=False,
            )
            embed.add_field(name="Tipo", value=tipo_cor, inline=True)
            embed.add_field(
                name="Cor principal",
                value=f"`{codigo.upper()}`",
                inline=True,
            )
            embed.add_field(
                name="Degradê",
                value=f"`{degradê.upper()}`" if degradê else "Nenhum",
                inline=True,
            )
            embed.add_field(name="Ação", value=acao, inline=False)
            embed.set_footer(text=f"ID do usuário: {member.id}")

            try:
                await log_thread.send(embed=embed)
            except discord.Forbidden:
                pass
            except discord.HTTPException:
                pass
