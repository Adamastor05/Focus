"""Listeners (bot.listen) que disparam a análise de foto de perfil.

Só observam os eventos; a análise em si está em analise_perfil.py.
Precisa da intent de membros (intents.members = True) ativada.
"""
import discord

from sistemas.analise_pfp.analisar_foto_perfil import processar_foto
from config.IDs import BIBLIA_EM_FOCO

GUILD_ID = BIBLIA_EM_FOCO


def _tem_foto(membro: discord.Member) -> bool:
    """Foto padrão do Discord não precisa ser analisada."""
    return membro.avatar is not None or membro.guild_avatar is not None


async def _executar(bot, membro: discord.Member, origem: str):
    try:
        await processar_foto(bot, membro, origem)
    except Exception as e:
        print(f"[PERFIL] Erro ao processar {membro} ({membro.id}) [{origem}]: {e}")


def registrar_listeners_perfil(bot):
    # ---------- Entrou no servidor ----------
    @bot.listen("on_member_join")
    async def perfil_on_member_join(member: discord.Member):
        if member.guild.id != GUILD_ID or member.bot:
            return
        if not _tem_foto(member):
            return
        await _executar(bot, member, "entrada")

    # ---------- Trocou a foto global ----------
    @bot.listen("on_user_update")
    async def perfil_on_user_update(before: discord.User, after: discord.User):
        if after.bot or before.avatar == after.avatar:
            return
        if after.avatar is None:  # removeu a foto
            return

        guild = bot.get_guild(GUILD_ID)
        membro = guild.get_member(after.id) if guild else None
        if membro is None:  # não está no servidor
            return

        # Se a pessoa tem foto própria no servidor, a foto exibida aqui não mudou.
        if membro.guild_avatar is not None:
            return

        await _executar(bot, membro, "troca")

    # ---------- Trocou a foto específica do servidor ----------
    @bot.listen("on_member_update")
    async def perfil_on_member_update(before: discord.Member, after: discord.Member):
        if after.guild.id != GUILD_ID or after.bot:
            return
        if before.guild_avatar == after.guild_avatar:
            return
        if after.guild_avatar is None:  # removeu a foto do servidor
            return

        await _executar(bot, after, "troca")