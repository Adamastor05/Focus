import traceback

import discord

from . import banco
from .ferramentas import obter_canal


async def _contraparte(bot, payload) -> discord.PartialMessage | None:
    """Devolve a mensagem do 'outro lado' (tópico <-> privado)."""
    if payload.guild_id is None:
        row = banco.por_dm_msg(payload.message_id)
        if row is None:
            return None
        canal = await obter_canal(bot, row["thread_id"])
        return canal.get_partial_message(row["thread_msg_id"])

    row = banco.por_thread_msg(payload.message_id)
    if row is None:
        return None
    canal = await obter_canal(bot, row["dm_channel_id"])
    return canal.get_partial_message(row["dm_msg_id"])


def registrar_reacoes(bot):

    @bot.listen("on_raw_reaction_add")
    async def _reacao_add(payload: discord.RawReactionActionEvent):
        try:
            if payload.user_id == bot.user.id:  # evita loop com as reações espelhadas pelo próprio bot
                return
            alvo = await _contraparte(bot, payload)
            if alvo is None:
                return
            await alvo.add_reaction(payload.emoji)
        except discord.HTTPException:
            pass  # emoji inacessível ao bot, mensagem apagada etc.
        except Exception:
            traceback.print_exc()

    @bot.listen("on_raw_reaction_remove")
    async def _reacao_remove(payload: discord.RawReactionActionEvent):
        try:
            if payload.user_id == bot.user.id:
                return
            alvo = await _contraparte(bot, payload)
            if alvo is None:
                return

            # se ainda sobrou alguém (que não seja o bot) com a mesma reação neste lado, mantém no outro
            canal_origem = await obter_canal(bot, payload.channel_id)
            msg_origem = await canal_origem.fetch_message(payload.message_id)
            for r in msg_origem.reactions:
                if str(r.emoji) == str(payload.emoji):
                    if r.count - (1 if r.me else 0) > 0:
                        return

            await alvo.remove_reaction(payload.emoji, bot.user)
        except discord.HTTPException:
            pass
        except Exception:
            traceback.print_exc()