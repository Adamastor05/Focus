import traceback

import discord

from utils.webhook_utils import enviar_como_autor
from . import banco
from .ferramentas import avisar_no_topico, embed_apagada, embed_editada, thread_da_pessoa


def registrar_dm_para_thread(bot):

    @bot.listen("on_message")
    async def _dm_para_thread(message: discord.Message):
        try:
            if not isinstance(message.channel, discord.DMChannel):
                return
            if message.author.bot:
                return
            if message.type not in (discord.MessageType.default, discord.MessageType.reply):
                return

            thread = await thread_da_pessoa(bot, message.author.id)
            if thread is None:  # sem tópico para essa pessoa: ignora
                return

            # usa o membro do servidor (apelido e foto do servidor), se existir
            autor = thread.guild.get_member(message.author.id) or message.author

            conteudo = message.content
            for s in message.stickers:
                conteudo += f"\n{s.url}"

            arquivos = []
            for a in message.attachments:
                try:
                    arquivos.append(await a.to_file(spoiler=a.is_spoiler()))
                except discord.HTTPException:
                    conteudo += f"\n{a.url}"

            conteudo = conteudo.strip()
            if not conteudo and not arquivos:
                return

            partes = [conteudo[i:i + 2000] for i in range(0, len(conteudo), 2000)] or [""]
            enviada = await enviar_como_autor(
                bot, thread, autor, content=partes[0], files=arquivos,
            )
            for resto in partes[1:]:
                await enviar_como_autor(bot, thread, autor, content=resto)

            banco.salvar(
                origem="dm",
                user_id=message.author.id,
                thread_id=thread.id,
                thread_msg_id=enviada.id,
                dm_channel_id=message.channel.id,
                dm_msg_id=message.id,
                autor_id=message.author.id,
                autor_nome=autor.display_name,
                autor_avatar=autor.display_avatar.url,
                conteudo=message.content,
            )
        except Exception:
            traceback.print_exc()

    @bot.listen("on_raw_message_edit")
    async def _dm_editada(payload: discord.RawMessageUpdateEvent):
        try:
            if payload.guild_id is not None:
                return
            dados = payload.data
            if not dados.get("edited_timestamp"):
                return
            row = banco.por_dm_msg(payload.message_id)
            if row is None or row["origem"] != "dm":
                return
            novo = dados.get("content")
            if novo is None or novo == row["conteudo"]:
                return

            editado_em = discord.utils.parse_time(dados["edited_timestamp"]) or discord.utils.utcnow()
            await avisar_no_topico(bot, row["thread_id"], embed_editada(row, row["conteudo"], novo, editado_em))
            banco.atualizar_conteudo(row["id"], novo)
        except Exception:
            traceback.print_exc()

    @bot.listen("on_raw_message_delete")
    async def _dm_apagada(payload: discord.RawMessageDeleteEvent):
        try:
            if payload.guild_id is not None:
                return
            row = banco.por_dm_msg(payload.message_id)
            if row is None or row["origem"] != "dm":  # as do bot (origem 'thread') são tratadas no Código 1
                return
            await avisar_no_topico(bot, row["thread_id"], embed_apagada(row, discord.utils.utcnow()))
        except Exception:
            traceback.print_exc()