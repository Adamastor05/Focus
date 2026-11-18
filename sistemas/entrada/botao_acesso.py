"""
botao_acesso.py

Comando slash /acesso_servidor_focus: envia a mensagem com o botão "Acessar".
Ao clicar, aciona o acesso_ao_servidor para quem clicou.

No main (dentro do setup_hook, pois a view persistente precisa de loop rodando):

    from botao_acesso import registrar_botao_acesso

    async def setup_hook():
        await registrar_botao_acesso(bot)
        await bot.tree.sync()   # ou o sync que você já usa
"""

import logging

import discord
from discord import app_commands

from sistemas.entrada.acesso_ao_servidor import acesso_ao_servidor
from config.IDs import CARGO_ADM, CARGO_FOCUS_ADM, CARGO_TRIAGEM

logger = logging.getLogger(__name__)

TEXTO_MENSAGEM = "Clique no botão abaixo para acessar o servidor."
CUSTOM_ID_BOTAO = "acesso_ao_servidor:acessar"
CARGOS_PERMITIDOS = {CARGO_TRIAGEM, CARGO_ADM, CARGO_FOCUS_ADM}


class AcessoView(discord.ui.View):
    """View persistente (timeout=None): o botão continua funcionando após reiniciar o bot."""

    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="Acessar",
        style=discord.ButtonStyle.primary,  # azul
        custom_id=CUSTOM_ID_BOTAO,
    )
    async def acessar(self, interaction: discord.Interaction, button: discord.ui.Button):
        membro = interaction.user
        if not isinstance(membro, discord.Member):
            await interaction.response.send_message(
                "Isso só pode ser usado dentro do servidor.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        try:
            await acesso_ao_servidor(self.bot, membro)
        except Exception as e:
            logger.exception("Erro ao acionar acesso_ao_servidor para %s", membro.id)
            await interaction.followup.send(
                f"❌ Ocorreu um erro ao liberar o acesso: `{type(e).__name__}`",
                ephemeral=True,
            )
            return

        # a mensagem do botão costuma ser apagada pelo acesso_ao_servidor, por isso a resposta é feita pelo followup (efêmero)
        await interaction.followup.send("✅ Siga para https://discord.com/channels/1347727626088878151/1347727626910826550", ephemeral=True)


@app_commands.command(
    name="acesso_servidor_focus",
    description="Envia a mensagem com o botão para acessar o servidor.",
)
@app_commands.guild_only()
async def botao_acesso(interaction: discord.Interaction):
    membro = interaction.user
    if not isinstance(membro, discord.Member) or not any(
        r.id in CARGOS_PERMITIDOS for r in membro.roles
    ):
        await interaction.response.send_message(
            "Você não tem permissão para usar este comando.", ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)
    await interaction.channel.send(TEXTO_MENSAGEM, view=AcessoView(interaction.client))
    await interaction.followup.send("Mensagem enviada.", ephemeral=True)


async def registrar_botao_acesso(bot):
    """Registra o comando e a view persistente. Chamar uma vez (ex.: no setup_hook)."""
    bot.add_view(AcessoView(bot))
    bot.tree.add_command(botao_acesso)