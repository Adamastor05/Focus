"""
contador_emojis.py
------------------
Módulo simples (sem cogs) para discord.py 2.x.

A cada mensagem enviada no servidor (evento on_message), conta os emojis
(customizados e unicode) e as figurinhas usados. Também conta as reações
adicionadas (evento on_raw_reaction_add). Mantém o ranking atualizado na
thread configurada. A contagem fica salva em um arquivo JSON,
então não se perde quando o bot reinicia.

Dependências:
    pip install -U discord.py

Requisitos no Developer Portal:
    - Ativar "Message Content Intent"

Permissões do bot:
    - Ver canais e Enviar mensagens na thread

Uso no main.py:
    import discord
    from discord.ext import commands
    import contador_emojis

    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix="!", intents=intents)

    contador_emojis.registrar(bot)   # <- registra o listener do on_message

    bot.run("SEU_TOKEN")

Obs.: usa bot.add_listener, então NÃO sobrescreve o on_message que você já
tenha no main.
"""

import asyncio
import json
import re
from pathlib import Path

import discord
from discord.ext import commands

THREAD_ID = 1570496887608316067
ARQUIVO = Path(__file__).with_name("contagem_emojis.json")

# Segundos de espera antes de atualizar a thread (agrupa várias mensagens
# seguidas em uma única atualização, evitando limite de requisições).
INTERVALO = 30

LIMITE_MSG = 1900  # margem abaixo do limite de 2000 caracteres do Discord

# <:nome:id> ou <a:nome:id>
CUSTOM_EMOJI_RE = re.compile(r"<(a?):(\w+):(\d+)>")

# Detecção de emojis unicode sem bibliotecas externas.
# Cobre: emojis simples, com variação (FE0F), tons de pele, sequências com ZWJ
# (ex.: 👨‍👩‍👧), bandeiras (🇧🇷) e keycaps (1️⃣).
_BASE = (
    "[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B50\u2B55\u203C\u2049\u2122\u2139"
    "\u2194-\u21AA\u231A-\u23FF\u24C2\u25AA-\u25FE\u2934\u2935\u2B05-\u2B07"
    "\u2B1B\u2B1C\u3030\u303D\u3297\u3299]"
)
_ELEMENTO = _BASE + "[\uFE0F\U0001F3FB-\U0001F3FF]*"
_EMOJI_RE = re.compile(
    "[\U0001F1E6-\U0001F1FF]{2}"  # bandeiras
    "|[0-9#*]\uFE0F?\u20E3"  # keycaps
    "|" + _ELEMENTO + "(?:\u200D" + _ELEMENTO + ")*"  # emoji (com ZWJ)
)

# Estado em memória (espelhado no JSON)
# {"emojis": {"😂": 3}, "figurinhas": {"id": {"nome": "x", "qtd": 2}}, "mensagens": [ids]}
_dados: dict = {"emojis": {}, "figurinhas": {}, "mensagens": []}
_tarefa: asyncio.Task | None = None


# ----------------------------------------------------------------------
# Persistência
# ----------------------------------------------------------------------
def _carregar():
    global _dados
    if ARQUIVO.exists():
        try:
            lido = json.loads(ARQUIVO.read_text(encoding="utf-8"))
            _dados["emojis"] = lido.get("emojis", {})
            _dados["figurinhas"] = lido.get("figurinhas", {})
            _dados["mensagens"] = lido.get("mensagens", [])
        except (json.JSONDecodeError, OSError):
            pass


def _salvar():
    try:
        ARQUIVO.write_text(
            json.dumps(_dados, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError as e:
        print(f"[contador_emojis] erro ao salvar: {e}")


# ----------------------------------------------------------------------
# Contagem
# ----------------------------------------------------------------------
def _emojis_unicode(texto: str) -> list[str]:
    return _EMOJI_RE.findall(texto)


def _contar_mensagem(msg: discord.Message) -> bool:
    """Conta emojis e figurinhas da mensagem. Retorna True se contou algo."""
    contou = False
    texto = msg.content or ""

    # Emojis customizados
    for animado, nome, eid in CUSTOM_EMOJI_RE.findall(texto):
        chave = f"<{animado}:{nome}:{eid}>"
        _dados["emojis"][chave] = _dados["emojis"].get(chave, 0) + 1
        contou = True

    # Emojis unicode
    for e in _emojis_unicode(texto):
        _dados["emojis"][e] = _dados["emojis"].get(e, 0) + 1
        contou = True

    # Figurinhas
    for fig in msg.stickers:
        atual = _dados["figurinhas"].setdefault(str(fig.id), {"nome": fig.name, "qtd": 0})
        atual["nome"] = fig.name
        atual["qtd"] += 1
        contou = True

    return contou


def _contar_reacao(payload: discord.RawReactionActionEvent) -> None:
    """Conta uma reação adicionada (1 reação = 1 uso do emoji)."""
    e = payload.emoji
    if e.id:  # emoji customizado
        chave = f"<{'a' if e.animated else ''}:{e.name}:{e.id}>"
    else:  # emoji unicode
        chave = e.name
    _dados["emojis"][chave] = _dados["emojis"].get(chave, 0) + 1


# ----------------------------------------------------------------------
# Envio / atualização na thread
# ----------------------------------------------------------------------
def _quebrar_linhas(titulo: str, linhas: list[str]) -> list[str]:
    partes, atual = [], f"**{titulo}**\n"
    if not linhas:
        return [atual + "Nenhum até agora."]
    for linha in linhas:
        if len(atual) + len(linha) + 1 > LIMITE_MSG:
            partes.append(atual)
            atual = ""
        atual += linha + "\n"
    partes.append(atual)
    return partes


async def _obter_thread(bot: commands.Bot):
    thread = bot.get_channel(THREAD_ID)
    if thread is None:
        thread = await bot.fetch_channel(THREAD_ID)
    if isinstance(thread, discord.Thread) and thread.archived:
        await thread.edit(archived=False)
    return thread


def _montar_textos() -> list[str]:
    emojis = sorted(_dados["emojis"].items(), key=lambda x: x[1], reverse=True)
    figs = sorted(_dados["figurinhas"].values(), key=lambda x: x["qtd"], reverse=True)

    linhas_emojis = [f"{i}. {e} — **{q}**" for i, (e, q) in enumerate(emojis, start=1)]
    linhas_figs = [f"{i}. {f['nome']} — **{f['qtd']}**" for i, f in enumerate(figs, start=1)]

    resumo = (
        "📊 **Contagem de emojis e figurinhas**\n"
        f"Emojis diferentes: **{len(emojis)}** (usos: **{sum(q for _, q in emojis)}**)\n"
        f"Figurinhas diferentes: **{len(figs)}** (usos: **{sum(f['qtd'] for f in figs)}**)"
    )

    return [resumo] + _quebrar_linhas("Emojis", linhas_emojis) + _quebrar_linhas("Figurinhas", linhas_figs)


async def _atualizar_thread(bot: commands.Bot):
    """Edita as mensagens do ranking na thread (ou cria, se não existirem)."""
    thread = await _obter_thread(bot)
    textos = _montar_textos()
    ids_antigos = list(_dados["mensagens"])
    ids_novos = []

    for i, texto in enumerate(textos):
        if i < len(ids_antigos):
            try:
                await thread.get_partial_message(ids_antigos[i]).edit(content=texto)
                ids_novos.append(ids_antigos[i])
                continue
            except discord.NotFound:
                pass  # mensagem apagada: envia uma nova
        msg = await thread.send(texto)
        ids_novos.append(msg.id)

    # Apaga mensagens que sobraram (ranking ficou menor)
    for mid in ids_antigos[len(textos):]:
        try:
            await thread.get_partial_message(mid).delete()
        except (discord.NotFound, discord.Forbidden):
            pass

    _dados["mensagens"] = ids_novos
    _salvar()


async def _atualizar_depois(bot: commands.Bot):
    await asyncio.sleep(INTERVALO)
    try:
        await _atualizar_thread(bot)
    except discord.Forbidden:
        print("[contador_emojis] sem permissão para enviar na thread.")
    except discord.NotFound:
        print("[contador_emojis] thread não encontrada. Verifique o THREAD_ID.")
    except discord.HTTPException as e:
        print(f"[contador_emojis] erro ao atualizar a thread: {e}")


def _agendar_atualizacao(bot: commands.Bot):
    global _tarefa
    if _tarefa is None or _tarefa.done():
        _tarefa = asyncio.create_task(_atualizar_depois(bot))


# ----------------------------------------------------------------------
# Registro no bot
# ----------------------------------------------------------------------
def registrar(bot: commands.Bot):
    """Chame no main: contador_emojis.registrar(bot)"""
    _carregar()

    async def on_message(msg: discord.Message):
        if msg.author.bot or msg.guild is None:
            return
        if msg.channel.id == THREAD_ID:  # não conta a própria thread do ranking
            return
        if _contar_mensagem(msg):
            _salvar()
            _agendar_atualizacao(bot)

    async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
        if payload.guild_id is None:  # ignora mensagens privadas
            return
        if payload.channel_id == THREAD_ID:  # não conta a thread do ranking
            return
        if payload.member is not None and payload.member.bot:
            return
        if bot.user is not None and payload.user_id == bot.user.id:
            return
        _contar_reacao(payload)
        _salvar()
        _agendar_atualizacao(bot)

    bot.add_listener(on_message, "on_message")
    bot.add_listener(on_raw_reaction_add, "on_raw_reaction_add")