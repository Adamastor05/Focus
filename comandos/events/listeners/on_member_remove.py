import discord

from config.IDs import chat_convites, chat_ticket


def registrar_evento_on_member_remove(bot):
    @bot.event
    async def on_member_remove(member: discord.Member):
        for canal_id in (chat_convites, chat_ticket):
            canal = bot.get_channel(canal_id)

            if canal is None:
                continue

            # Tópicos ativos
            for thread in canal.threads:
                if str(member.id) in thread.name:
                    await thread.send(f"⚠️ {member.mention} saiu do servidor.")
                    break

            # Tópicos arquivados
            async for thread in canal.archived_threads(limit=None):
                if str(member.id) in thread.name:
                    await thread.send(f"⚠️ {member.mention} saiu do servidor.")
                    break
