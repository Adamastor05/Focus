import asyncio
from datetime import datetime, timezone

import discord

from config.IDs import chat_convites, invite_tracker_bot


def registrar_evento_on_member_join(bot):
    @bot.event
    async def on_member_join(membro: discord.Member):
        #region Criar tópico no chat de convites
        await asyncio.sleep(4)

        canal = membro.guild.get_channel(chat_convites)
        if canal is None:
            return

        agora = datetime.now(timezone.utc)
        dias = (agora - membro.created_at).days

        mensagem_base = None
        ultima_mensagem_bot = None

        # Procura a mensagem do Invite Tracker Bot
        async for msg in canal.history(limit=20):

            if msg.author.id != invite_tracker_bot:
                continue

            if ultima_mensagem_bot is None:
                ultima_mensagem_bot = msg

            idade = (agora - msg.created_at).total_seconds()

            if idade <= 10:
                conteudo = msg.content.lower()

                if (
                    str(membro.id) in conteudo
                    or membro.name.lower() in conteudo
                    or membro.display_name.lower() in conteudo
                ):
                    mensagem_base = msg
                    break

        if mensagem_base is None:
            mensagem_base = ultima_mensagem_bot

        if mensagem_base is None:
            return

        # Criação do tópico

        try:
            thread = await mensagem_base.create_thread(
                name=f"{membro.name} {membro.id}",
                auto_archive_duration=60
            )

        except discord.HTTPException:

            thread = await canal.create_thread(
                name=f"{membro.name} {membro.id}",
                type=discord.ChannelType.public_thread,
                auto_archive_duration=60
            )

        # Primeira mensagem

        fluxograma_recepcao = "https://cdn.discordapp.com/attachments/1522709780051923214/1529144496196161576/image.png?ex=6a6775ca&is=6a66244a&hm=9eee175b33ddcb8b755184bf4ad39aa7665cd72accf65c7b1a2330b13e6a117c"
        await thread.send(fluxograma_recepcao)    
        await thread.send("<@&1419489233940512828>") #ping de recepcionistas. o yagpdb apaga.
        
        if dias < 1:
            idade = "Menos de 1 dia \n VERIFICAÇÃO OBRIGATÓRIA"
        elif dias == 1:
            idade = "**1 dias \n VERIFICAÇÃO OBRIGATÓRIA"
        elif dias <14:
            idade = f"{dias} dias \n VERIFICAÇÃO OBRIGATÓRIA"
        elif dias < 30:
            idade = f"**{dias} dias**"
        elif dias < 365:
            meses = dias // 30
            idade = f"{meses} mês" if meses == 1 else f"{meses} meses"
        else:
            anos = dias // 365
            idade = f"{anos} ano" if anos == 1 else f"{anos} anos"


        embed = discord.Embed(
            title="Novo membro",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=membro.display_avatar.url)
        embed.add_field(
            name="Nome",
            value=membro.name,
            inline=False
        )
        embed.add_field(
                name="Menção",
                value=membro.mention,
                inline=True
        )
        embed.add_field(
            name="ID",
            value=str(membro.id),
            inline=False
        )
        embed.add_field(
            name="Idade da conta",
            value=idade,
            inline=False
        )
        embed.add_field(
            name="Verifique o xp global com a Loritta",
            value="Se for menor que **3000**, verificação obrigatória.",
            inline=False
        )
        await thread.send(
            content=f"{membro.mention}",
            embed=embed
        )
        id_usuario = membro.id
        await asyncio.sleep(1)
        await thread.send(f"Verifique o **xp** na loritta: \n ```+perfil {id_usuario}```")
        await thread.send(f"+perfil {id_usuario}")
        await asyncio.sleep(5)
        await thread.send(f"Verifique o **perfil** do discord: \n# {membro.mention}")

        # Procura o ID apenas no chat_convites
        # (ignora mensagens do dia atual)
        inicio_hoje = datetime.now(timezone.utc).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )
        encontrou = False
        async for msg in canal.history(limit=None, before=inicio_hoje):

            if str(membro.id) in msg.content:
                encontrou = True
                break

        if encontrou:
            await thread.send(
                "⚠️ Achei o ID dessa pessoa anteriormente no chat de convites."
            )
        else:
            await thread.send(
                "✅ Nenhuma ocorrência anterior desse ID foi encontrada."
            )
        #endregion
