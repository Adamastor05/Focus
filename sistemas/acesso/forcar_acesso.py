"""
forcar_acesso.py

Comando slash /forçar_acesso: dá acesso ao servidor para uma pessoa, após confirmação.

- `pessoa` (opcional): id ou @ da pessoa. Se vazio, usa o id que está no título da
  thread onde o comando foi usado (ex.: "joao 123456789012345678").
- Pergunta (efêmero) "Você quer dar acesso a ...?" com botões Sim / Não.
- Sim: aciona o acesso_ao_servidor e avisa, no tópico da pessoa em CHAT_CONVITES,
  quem deu o acesso (embed, sem marcar quem deu).
- Não: edita a embed e registra em CHAT_LOGS_COMPOSTO.
"""

import logging
import re
from typing import Optional

import discord
from discord import app_commands

from config.IDs import CARGO_ADM, CARGO_FOCUS_ADM, CARGO_TRIAGEM, CHAT_CONVITES
from sistemas.acesso.acesso_ao_servidor import (
    acesso_ao_servidor,
    buscar_threads_por_id,
    enviar_logs,
    obter_canal,
)

logger = logging.getLogger(__name__)

CARGOS_PERMITIDOS = {CARGO_TRIAGEM, CARGO_FOCUS_ADM, CARGO_ADM}
TEMPO_LIMITE_CONFIRMACAO = 120  # segundos
SEM_MENCOES = discord.AllowedMentions.none()

_REGEX_ID = re.compile(r"\d{15,20}")


# ---------------------------------------------------------------------------
# EMBEDS
# ---------------------------------------------------------------------------

def _embed(membro: discord.Member, descricao: str, cor: discord.Color) -> discord.Embed:
    embed = discord.Embed(title="Forçar acesso", description=descricao, color=cor)
    embed.set_thumbnail(url=membro.display_avatar.url)
    return embed


def _embed_pergunta(membro: discord.Member) -> discord.Embed:
    return _embed(
        membro, f"Você quer dar acesso a **{membro.display_name}**?", discord.Color.blue()
    )


# ---------------------------------------------------------------------------
# VIEW DE CONFIRMAÇÃO
# ---------------------------------------------------------------------------

class ConfirmarAcessoView(discord.ui.View):
    def __init__(self, bot, solicitante: discord.Member, membro: discord.Member):
        super().__init__(timeout=TEMPO_LIMITE_CONFIRMACAO)
        self.bot = bot
        self.solicitante = solicitante
        self.membro = membro
        self.interaction_original: Optional[discord.Interaction] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.solicitante.id:
            await interaction.response.send_message(
                "Só quem usou o comando pode responder.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self):
        if self.interaction_original is None:
            return
        try:
            await self.interaction_original.edit_original_response(
                embed=_embed(
                    self.membro,
                    f"Tempo esgotado. O acesso de **{self.membro.display_name}** não foi liberado.",
                    discord.Color.light_grey(),
                ),
                view=None,
            )
        except discord.HTTPException:
            pass

    async def _avisar_convites(self):
        """Avisa, nos tópicos de CHAT_CONVITES com o id da pessoa, quem deu o acesso."""
        canal = await obter_canal(self.bot, CHAT_CONVITES)
        if canal is None:
            return
        threads = await buscar_threads_por_id(canal, self.membro.id)

        embed = discord.Embed(
            description=f"Acesso liberado manualmente por **{self.solicitante.display_name}**.",
            color=discord.Color.green(),
        )
        for t in threads:
            try:
                await t.send(embed=embed, allowed_mentions=SEM_MENCOES)
            except Exception as e:
                logger.warning("Falha ao avisar na thread %s: %s", t.id, e)

    @discord.ui.button(label="Sim", style=discord.ButtonStyle.success)
    async def sim(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.edit_message(
            embed=_embed(
                self.membro,
                f"Liberando o acesso de **{self.membro.display_name}**...",
                discord.Color.blue(),
            ),
            view=None,
        )

        try:
            await acesso_ao_servidor(self.bot, self.membro)
            await self._avisar_convites()
        except Exception as e:
            logger.exception("Erro ao forçar acesso de %s", self.membro.id)
            await interaction.edit_original_response(
                embed=_embed(
                    self.membro,
                    f"❌ Erro ao liberar o acesso: `{type(e).__name__}`",
                    discord.Color.red(),
                )
            )
            return

        await interaction.edit_original_response(
            embed=_embed(
                self.membro,
                f"✅ Acesso de **{self.membro.display_name}** liberado.",
                discord.Color.green(),
            )
        )
        await enviar_logs(
            self.bot,
            f"🔓 {self.solicitante.mention} forçou o acesso de {self.membro.mention} "
            f"(`{self.membro.id}`).",
        )

    @discord.ui.button(label="Não", style=discord.ButtonStyle.danger)
    async def nao(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.edit_message(
            embed=_embed(
                self.membro,
                f"Acesso de **{self.membro.display_name}** não foi liberado.",
                discord.Color.light_grey(),
            ),
            view=None,
        )
        await enviar_logs(
            self.bot,
            f"🚫 {self.solicitante.mention} cancelou o acesso forçado de "
            f"{self.membro.mention} (`{self.membro.id}`).",
        )


# ---------------------------------------------------------------------------
# COMANDO
# ---------------------------------------------------------------------------

def _id_do_titulo_da_thread(canal) -> Optional[int]:
    """Último número de 15 a 20 dígitos no título da thread."""
    if not isinstance(canal, discord.Thread):
        return None
    achados = _REGEX_ID.findall(canal.name)
    return int(achados[-1]) if achados else None


@app_commands.command(
    name="forçar_acesso",
    description="Dá acesso ao servidor para uma pessoa.",
)
@app_commands.describe(
    pessoa="Id ou @ da pessoa (opcional: se vazio, usa o id do título da thread)"
)
@app_commands.guild_only()
async def forcar_acesso(interaction: discord.Interaction, pessoa: Optional[str] = None):
    solicitante = interaction.user
    if not isinstance(solicitante, discord.Member) or not any(
        r.id in CARGOS_PERMITIDOS for r in solicitante.roles
    ):
        await interaction.response.send_message(
            "Você não tem permissão para usar este comando.", ephemeral=True
        )
        return

    # 1) descobrir o id
    if pessoa:
        achado = _REGEX_ID.search(pessoa)
        user_id = int(achado.group()) if achado else None
    else:
        user_id = _id_do_titulo_da_thread(interaction.channel)

    if user_id is None:
        await interaction.response.send_message(
            "❌ Não encontrei um id. Preencha o campo `pessoa` ou use o comando "
            "em uma thread que tenha o id da pessoa no título.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True)

    # 2) achar a pessoa no servidor
    membro = interaction.guild.get_member(user_id)
    if membro is None:
        try:
            membro = await interaction.guild.fetch_member(user_id)
        except discord.NotFound:
            membro = None
        except discord.HTTPException:
            membro = None

    if membro is None:
        await interaction.followup.send(
            f"❌ Não encontrei o membro com id `{user_id}` neste servidor.",
            ephemeral=True,
        )
        return

    # 3) pergunta de confirmação (efêmera)
    view = ConfirmarAcessoView(interaction.client, solicitante, membro)
    view.interaction_original = interaction
    await interaction.followup.send(embed=_embed_pergunta(membro), view=view, ephemeral=True)


def registrar_forcar_acesso(bot):
    """Registra o comando no tree. Chamar antes do bot.tree.sync()."""
    bot.tree.add_command(forcar_acesso)