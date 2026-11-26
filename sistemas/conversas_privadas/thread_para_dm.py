import traceback

import discord

from config.IDs import CHAT_CONVERSAS_PRIVADAS
from . import banco
from .ferramentas import (
    avisar_no_topico, dm_da_pessoa, embed_apagada, embed_editada,
    embed_falha_envio, extrair_id, obter_canal,
)

PREFIXO_IGNORAR = "i#"


def _limitar(txt: str) -> str:
    return txt if len(txt) <= 2000 else txt[:1999] + "…"


async def _tratar_apagada(bot, message_id: int):
    row = banco.por_thread_msg(message_id)
    if row is None or row["origem"] != "thread":
        return  # mensagem da pessoa (webhook) apagada no tópico: nada a fazer no privado

    erro = None
    try:
        dm = await obter_canal(bot, row["dm_channel_id"])
        await dm.get_partial_message(row["dm_msg_id"]).delete()
    except discord.HTTPException as e:
        erro = str(e)

    await avisar_no_topico(bot, row["thread_id"], embed_apagada(row, discord.utils.utcnow(), erro))
    banco.apagar(row["id"])


def registrar_thread_para_dm(bot):

    @bot.listen("on_message")
    async def _thread_para_dm(message: discord.Message):
        try:
            canal = message.channel
            if not isinstance(canal, discord.Thread) or canal.parent_id != CHAT_CONVERSAS_PRIVADAS:
                return
            if message.id == canal.id:  # mensagem inicial de tópico de fórum
                return
            if message.webhook_id is not None:  # inclui as mensagens espelhadas da pessoa
                return
            if message.author.bot and message.author.id != bot.user.id:
                return
            if message.type not in (discord.MessageType.default, discord.MessageType.reply):
                return
            if any(e.type == "rich" for e in message.embeds):
                return
            if message.content.lstrip().lower().startswith(PREFIXO_IGNORAR):
                return

            user_id = extrair_id(canal.name)
            if user_id is None:
                return

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

            kwargs = {"allowed_mentions": discord.AllowedMentions.none()}
            if conteudo:
                kwargs["content"] = _limitar(conteudo)
            if arquivos:
                kwargs["files"] = arquivos

            try:
                dm = await dm_da_pessoa(bot, user_id)
                enviada = await dm.send(**kwargs)
            except discord.Forbidden:
                await avisar_no_topico(bot, canal.id, embed_falha_envio(
                    "A pessoa está com o privado fechado ou bloqueou o bot."))
                return
            except discord.HTTPException as e:
                await avisar_no_topico(bot, canal.id, embed_falha_envio(str(e)))
                return

            banco.salvar(
                origem="thread",
                user_id=user_id,
                thread_id=canal.id,
                thread_msg_id=message.id,
                dm_channel_id=dm.id,
                dm_msg_id=enviada.id,
                autor_id=message.author.id,
                autor_nome=message.author.display_name,
                autor_avatar=message.author.display_avatar.url,
                conteudo=message.content,
            )
        except Exception:
            traceback.print_exc()

    @bot.listen("on_raw_message_edit")
    async def _thread_editada(payload: discord.RawMessageUpdateEvent):
        try:
            dados = payload.data
            if not dados.get("edited_timestamp"):  # atualização de preview de link, não é edição
                return
            row = banco.por_thread_msg(payload.message_id)
            if row is None or row["origem"] != "thread":
                return
            novo = dados.get("content")
            if novo is None or novo == row["conteudo"]:
                return

            erro = None
            try:
                dm = await obter_canal(bot, row["dm_channel_id"])
                await dm.get_partial_message(row["dm_msg_id"]).edit(content=_limitar(novo) or None)
            except discord.HTTPException as e:
                erro = str(e)

            editado_em = discord.utils.parse_time(dados["edited_timestamp"]) or discord.utils.utcnow()
            await avisar_no_topico(bot, row["thread_id"], embed_editada(row, row["conteudo"], novo, editado_em, erro))
            banco.atualizar_conteudo(row["id"], novo)
        except Exception:
            traceback.print_exc()

    @bot.listen("on_raw_message_delete")
    async def _thread_apagada(payload: discord.RawMessageDeleteEvent):
        try:
            await _tratar_apagada(bot, payload.message_id)
        except Exception:
            traceback.print_exc()

    @bot.listen("on_raw_bulk_message_delete")
    async def _thread_apagadas_em_massa(payload: discord.RawBulkMessageDeleteEvent):
        try:
            for mid in payload.message_ids:
                await _tratar_apagada(bot, mid)
        except Exception:
            traceback.print_exc()