import json
import os
import re
import traceback
from collections import OrderedDict

import discord

# ajuste para o lugar onde ficam suas constantes
from config.IDs import CHAT_REGRAS_TICKET_DE_ENTRADA, CHAT_CONVITES
from utils.webhook_utils import enviar_como_autor

FRASES_IGNORADAS = [
    "por que você gostaria de entrar no servidor?",
    "se verifique em",
    "qual é a sua religião?",
    "se verificou.",
    "acessou o servidor",
    "saiu do servidor.",
]

ARQUIVO_MAPA = "dados/espelho_convites.json"  # id original -> [id da thread, id da msg do webhook]
LIMITE_MAPA = 3000


# ---------- mapa persistente (para os links dos replies) ----------
def _carregar_mapa() -> OrderedDict:
    try:
        with open(ARQUIVO_MAPA, "r", encoding="utf-8") as f:
            return OrderedDict(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return OrderedDict()


def _salvar_mapa(mapa: OrderedDict):
    os.makedirs(os.path.dirname(ARQUIVO_MAPA), exist_ok=True)
    with open(ARQUIVO_MAPA, "w", encoding="utf-8") as f:
        json.dump(mapa, f)


# ---------- utilidades ----------
def _textos_embed(embed: discord.Embed) -> list[str]:
    partes = [
        embed.title,
        embed.description,
        embed.footer.text if embed.footer else None,
        embed.author.name if embed.author else None,
    ]
    for campo in embed.fields:
        partes += [campo.name, campo.value]
    return [p for p in partes if p]


def deve_ignorar(bot, message: discord.Message) -> bool:
    if message.author.id != bot.user.id:
        return False
    textos = [message.content or ""]
    for e in message.embeds:
        textos += _textos_embed(e)
    texto = "\n".join(textos).casefold()
    return any(frase in texto for frase in FRASES_IGNORADAS)


def extrair_id(nome: str) -> int | None:
    ids = re.findall(r"\d{17,20}", nome)
    return int(ids[-1]) if ids else None


async def achar_thread_convites(bot, user_id: int) -> discord.Thread | None:
    canal = bot.get_channel(CHAT_CONVITES) or await bot.fetch_channel(CHAT_CONVITES)
    alvo = str(user_id)

    for t in canal.threads:  # ativas
        if alvo in t.name:
            return t
    async for t in canal.archived_threads(limit=None):  # arquivadas
        if alvo in t.name:
            return t
    return None


async def montar_view_resposta(message: discord.Message, guild_id: int, mapa) -> discord.ui.View | None:
    ref = message.reference
    if not ref or not ref.message_id:
        return None

    alvo = ref.resolved if isinstance(ref.resolved, discord.Message) else None
    if alvo is None:
        try:
            alvo = await message.channel.fetch_message(ref.message_id)
        except discord.HTTPException:
            alvo = None

    nome = alvo.author.display_name if alvo else "Mensagem apagada"

    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(
        style=discord.ButtonStyle.primary,  # azul
        label=nome[:80],
        disabled=True,
    ))

    espelho = mapa.get(str(ref.message_id))
    if espelho:  # só há link se a mensagem respondida também foi espelhada
        url = f"https://discord.com/channels/{guild_id}/{espelho[0]}/{espelho[1]}"
        view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.link,
            label="Ver mensagem",
            url=url,
        ))
    return view


# ---------- registro ----------
def espelhar_ticket_convites(bot):
    if getattr(bot, "_espelho_convites_registrado", False):  # evita listener duplicado
        return
    bot._espelho_convites_registrado = True

    mapa = _carregar_mapa()

    @bot.listen("on_message")
    async def _espelhar_ticket(message: discord.Message):
        try:
            canal = message.channel
            if not isinstance(canal, discord.Thread):
                return
            if canal.parent_id != CHAT_REGRAS_TICKET_DE_ENTRADA:
                return
            if message.type not in (discord.MessageType.default, discord.MessageType.reply):
                return
            if deve_ignorar(bot, message):
                return

            user_id = extrair_id(canal.name)
            if user_id is None:
                return

            destino = await achar_thread_convites(bot, user_id)
            if destino is None:
                return

            # conteúdo
            conteudo = message.content or ""
            for s in message.stickers:
                conteudo += f"\n{s.url}"

            arquivos = []
            for a in message.attachments:
                try:
                    arquivos.append(await a.to_file(spoiler=a.is_spoiler()))
                except discord.HTTPException:
                    conteudo += f"\n{a.url}"

            # só embeds "rich" (os de preview de link o próprio Discord recria)
            embeds = [e for e in message.embeds if e.type == "rich"][:10]

            conteudo = conteudo.strip()
            if not conteudo and not embeds and not arquivos:
                return

            view = await montar_view_resposta(message, destino.guild.id, mapa)

            # webhook aceita 2000 caracteres; divide se precisar
            partes = [conteudo[i:i + 2000] for i in range(0, len(conteudo), 2000)] or [""]

            enviada = await enviar_como_autor(
                bot, destino, message.author,
                content=partes[0], embeds=embeds, files=arquivos, view=view,
            )
            if view:
                view.stop()  # botões são só visuais, não precisa escutar interações

            for resto in partes[1:]:
                await enviar_como_autor(bot, destino, message.author, content=resto)

            mapa[str(message.id)] = [destino.id, enviada.id]
            while len(mapa) > LIMITE_MAPA:
                mapa.popitem(last=False)
            _salvar_mapa(mapa)

        except Exception:
            traceback.print_exc()