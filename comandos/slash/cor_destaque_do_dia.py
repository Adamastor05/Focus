import discord
from discord.ext import commands


def converter_hex(valor: str) -> discord.Color | None:
    valor = valor.strip().replace("#", "")
    if len(valor) != 6:
        return None

    try:
        numero = int(valor, 16)
    except ValueError:
        return None

    return discord.Color(numero)


class ModalCoresDestaque(discord.ui.Modal, title="Configurar cores"):
    primeira_cor = discord.ui.TextInput(
        label="Primeira cor",
        placeholder="#FF0000",
        required=True,
        max_length=7,
    )
    segunda_cor = discord.ui.TextInput(
        label="Segunda cor",
        placeholder="#0000FF (opcional)",
        required=False,
        max_length=7,
    )

    def __init__(self, cargo: discord.Role):
        super().__init__()
        self.cargo = cargo

    async def on_submit(self, interaction: discord.Interaction) -> None:
        cor1 = converter_hex(self.primeira_cor.value)
        if cor1 is None:
            await interaction.response.send_message(
                "❌ A primeira cor não é um código hexadecimal válido.\n"
                "Use o formato `#RRGGBB`, por exemplo: `#FF0000`.",
                ephemeral=True,
            )
            return

        valor_segunda = self.segunda_cor.value.strip()
        cor2 = None
        if valor_segunda:
            cor2 = converter_hex(valor_segunda)
            if cor2 is None:
                await interaction.response.send_message(
                    "❌ A segunda cor não é um código hexadecimal válido.\n"
                    "Use o formato `#RRGGBB`, por exemplo: `#0000FF`.",
                    ephemeral=True,
                )
                return

        try:
            await self.cargo.edit(
                color=cor1,
                reason=f"Cor do cargo alterada por {interaction.user}",
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Não tenho permissão para alterar esse cargo.\n"
                "Verifique se o meu cargo está acima de "
                "`cargo_destaque_do_dia`.",
                ephemeral=True,
            )
            return
        except discord.HTTPException as erro:
            await interaction.response.send_message(
                "❌ O Discord recusou a alteração do cargo.\n"
                f"Erro: `{erro}`",
                ephemeral=True,
            )
            return

        if cor2:
            await interaction.response.send_message(
                f"✅ **Primeira cor salva:** `{self.primeira_cor.value}`\n"
                f"🎨 **Segunda cor salva:** `{self.segunda_cor.value}`\n\n"
                "⚠️ A primeira cor do cargo foi alterada.\n"
                "A segunda cor foi registrada, mas o degradê "
                "deve ser aplicado pelo sistema do `/cor`.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "✅ **Cor salva com sucesso!**\n\n"
                f"🎨 Cor do cargo: `{self.primeira_cor.value}`\n"
                "ℹ️ Nenhuma segunda cor foi informada.",
                ephemeral=True,
            )


class ViewConfigurarDestaque(discord.ui.View):
    def __init__(
        self,
        cargo: discord.Role,
        cargo_destaque_id: int,
        cargo_administrador_id: int,
    ):
        super().__init__(timeout=None)
        self.cargo = cargo
        self.cargo_destaque_id = cargo_destaque_id
        self.cargo_administrador_id = cargo_administrador_id

    @discord.ui.button(
        label="Salvar",
        style=discord.ButtonStyle.success,
        emoji="💾",
        custom_id="destaque_salvar",
    )
    async def salvar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "❌ Este botão só pode ser usado em um servidor.",
                ephemeral=True,
            )
            return

        cargo_destaque_role = guild.get_role(self.cargo_destaque_id)
        cargo_adm_role = guild.get_role(self.cargo_administrador_id)
        cargos_usuario = interaction.user.roles
        autorizado = (
            cargo_destaque_role in cargos_usuario
            or cargo_adm_role in cargos_usuario
        )
        if not autorizado:
            await interaction.response.send_message(
                "❌ Você não tem permissão para usar este botão.",
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(
            ModalCoresDestaque(self.cargo)
        )


def registrar_comando_cor_destaque_do_dia(
    bot: commands.Bot,
    cargo_destaque_do_dia_id: int,
    cargo_administrador_id: int,
) -> None:
    @bot.tree.command(
        name="cor_destaque_do_dia",
        description="Configura as cores do cargo Destaque do Dia.",
    )
    async def cor_destaque_do_dia(
        interaction: discord.Interaction,
    ) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em um servidor.",
                ephemeral=True,
            )
            return

        cargo_destaque_role = guild.get_role(cargo_destaque_do_dia_id)
        cargo_adm_role = guild.get_role(cargo_administrador_id)

        if cargo_destaque_role is None:
            await interaction.response.send_message(
                "❌ Não encontrei o cargo `cargo_destaque_do_dia`.",
                ephemeral=True,
            )
            return

        cargos_usuario = interaction.user.roles
        autorizado = (
            cargo_destaque_role in cargos_usuario
            or cargo_adm_role in cargos_usuario
        )
        if not autorizado:
            await interaction.response.send_message(
                "❌ Você precisa possuir o cargo "
                "`cargo_destaque_do_dia` ou "
                "`cargo_administrador` para usar este comando.",
                ephemeral=True,
            )
            return

        cor_atual = cargo_destaque_role.color
        hex_atual = f"#{cor_atual.value:06X}"
        embed1 = discord.Embed(
            title="🎨 Primeira cor",
            description=f"Cor atual do cargo:\n`{hex_atual}`",
            color=cor_atual,
        )
        embed2 = discord.Embed(
            title="🎨 Segunda cor",
            description=(
                "Nenhuma segunda cor está configurada atualmente.\n\n"
                "Você poderá informar uma segunda cor ao clicar "
                "em **Salvar**."
            ),
            color=discord.Color.dark_grey(),
        )
        view = ViewConfigurarDestaque(
            cargo_destaque_role,
            cargo_destaque_do_dia_id,
            cargo_administrador_id,
        )
        await interaction.response.send_message(
            embeds=[embed1, embed2],
            view=view,
        )
