# Esse código serve para:
# 1- Marcar ping de acolhimento quando alguém criar uma thread no fórum de apresentações
# 2- Adicionar o cargo de apresentado a essa pessoa
import asyncio
import discord

from config.IDs import CHAT_FORUM_APRESENTACOES, CARGO_APRESENTADO, CARGO_ACOLHIMENTO, CHAT_LOGS

def registrar_evento_on_thread_create(bot):

    @bot.listen("on_thread_create")
    async def ping_acolhimento_thread_create(thread: discord.Thread):
        # Só nos interessa o fórum de apresentações
        if thread.parent_id != CHAT_FORUM_APRESENTACOES:
            return

        # Pequena espera para o Discord terminar de montar a thread
        await asyncio.sleep(1)

        guild = thread.guild

        #region Autor
        autor = thread.owner or guild.get_member(thread.owner_id)

        if autor is None and thread.owner_id:
            try:
                autor = await guild.fetch_member(thread.owner_id)
            except discord.HTTPException:
                autor = None
        #endregion

        #region Ping recepcionistas
        try:
            await thread.send(
                f"<@&{CARGO_ACOLHIMENTO}>",
                allowed_mentions=discord.AllowedMentions(roles=True),
            )
            ping_ok = True
        except discord.HTTPException as e:
            print(f"[ping_acolhimento] Falha ao enviar ping na thread {thread.id}: {e}")
            ping_ok = False
        #endregion

        #region Cargo de apresentado
        cargo_ok = False
        cargo = guild.get_role(CARGO_APRESENTADO)

        if isinstance(autor, discord.Member) and cargo:
            try:
                await autor.add_roles(cargo, reason="Criou uma apresentação.")
                cargo_ok = True
            except discord.HTTPException as e:
                print(f"[ping_acolhimento] Falha ao dar cargo a {autor.id}: {e}")
        #endregion

        #region Log
        canal_logs = bot.get_channel(CHAT_LOGS)
        if canal_logs is None:
            return

        acoes = [
            "• Mensagem enviada no tópico." if ping_ok else "• ❌ Falha ao enviar mensagem no tópico.",
            "• Cargo de apresentado concedido." if cargo_ok else "• ❌ Cargo de apresentado não concedido.",
        ]

        embed = discord.Embed(
            title="👋 Nova apresentação",
            color=discord.Color.green() if (ping_ok and cargo_ok) else discord.Color.orange(),
        )
        embed.add_field(
            name="Criado por",
            value=autor.mention if autor else "Desconhecido",
            inline=False,
        )
        embed.add_field(name="Canal", value=thread.parent.mention if thread.parent else "—", inline=False)
        embed.add_field(name="Tópico", value=f"[Clique aqui]({thread.jump_url})", inline=False)
        embed.add_field(name="Ações", value="\n".join(acoes), inline=False)

        try:
            await canal_logs.send(embed=embed)
        except discord.HTTPException as e:
            print(f"[ping_acolhimento] Falha ao enviar log: {e}")
        #endregion