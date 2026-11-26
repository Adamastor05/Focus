import re
import traceback

import discord

from config.IDs import CHAT_CONVERSAS_PRIVADAS

_cache_threads: dict[int, int] = {}  # id da pessoa -> id do tópico


def extrair_id(nome: str) -> int | None:
    ids = re.findall(r"\d{17,20}", nome)
    return int(ids[-1]) if ids else None


async def obter_canal(bot, canal_id: int):
    return bot.get_channel(canal_id) or await bot.fetch_channel(canal_id)


async def thread_da_pessoa(bot, user_id: int) -> discord.Thread | None:
    """Acha o tópico de CHAT_CONVERSAS_PRIVADAS cujo título tem o id da pessoa."""
    tid = _cache_threads.get(user_id)
    if tid:
        try:
            t = await obter_canal(bot, tid)
            if extrair_id(t.name) == user_id:
                return t
        except discord.HTTPException:
            pass
        _cache_threads.pop(user_id, None)

    canal = await obter_canal(bot, CHAT_CONVERSAS_PRIVADAS)
    for t in canal.threads:  # ativos
        if extrair_id(t.name) == user_id:
            _cache_threads[user_id] = t.id
            return t
    async for t in canal.archived_threads(limit=None):  # arquivados
        if extrair_id(t.name) == user_id:
            _cache_threads[user_id] = t.id
            return t
    return None


async def dm_da_pessoa(bot, user_id: int) -> discord.DMChannel:
    user = bot.get_user(user_id) or await bot.fetch_user(user_id)
    return user.dm_channel or await user.create_dm()


# ---------- avisos em embed ----------
def _cortar(txt: str | None, n: int = 1024) -> str:
    txt = txt or "*(sem texto)*"
    return txt if len(txt) <= n else txt[: n - 1] + "…"


def _rotulo(row) -> str:
    return "Mensagem da equipe (enviada ao privado)" if row["origem"] == "thread" \
        else "Mensagem da pessoa (privado)"


def _data_original(row):
    msg_id = row["thread_msg_id"] if row["origem"] == "thread" else row["dm_msg_id"]
    return discord.utils.snowflake_time(msg_id)


def embed_editada(row, antes: str, depois: str, editado_em, erro: str | None = None) -> discord.Embed:
    e = discord.Embed(title="✏️ Mensagem editada", color=discord.Color.orange(), timestamp=editado_em)
    e.set_author(name=row["autor_nome"], icon_url=row["autor_avatar"])
    e.add_field(name="Antes", value=_cortar(antes), inline=False)
    e.add_field(name="Depois", value=_cortar(depois), inline=False)
    e.add_field(name="Autor", value=f"<@{row['autor_id']}>", inline=True)
    e.add_field(name="Data original", value=discord.utils.format_dt(_data_original(row), "F"), inline=True)
    e.add_field(name="Data da edição", value=discord.utils.format_dt(editado_em, "F"), inline=True)
    if erro:
        e.add_field(name="⚠️ Falha ao editar no privado", value=_cortar(erro), inline=False)
    e.set_footer(text=_rotulo(row))
    return e


def embed_apagada(row, apagado_em, erro: str | None = None) -> discord.Embed:
    e = discord.Embed(title="🗑️ Mensagem apagada", color=discord.Color.red(), timestamp=apagado_em)
    e.set_author(name=row["autor_nome"], icon_url=row["autor_avatar"])
    e.add_field(name="Conteúdo", value=_cortar(row["conteudo"]), inline=False)
    e.add_field(name="Autor", value=f"<@{row['autor_id']}>", inline=True)
    e.add_field(name="Data original", value=discord.utils.format_dt(_data_original(row), "F"), inline=True)
    e.add_field(name="Data de apagamento", value=discord.utils.format_dt(apagado_em, "F"), inline=True)
    if erro:
        e.add_field(name="⚠️ Falha ao apagar no privado", value=_cortar(erro), inline=False)
    e.set_footer(text=_rotulo(row))
    return e


def embed_falha_envio(motivo: str) -> discord.Embed:
    return discord.Embed(
        title="⚠️ Não foi possível enviar ao privado",
        description=_cortar(motivo, 4000),
        color=discord.Color.red(),
    )


async def avisar_no_topico(bot, thread_id: int, embed: discord.Embed):
    try:
        thread = await obter_canal(bot, thread_id)
        if isinstance(thread, discord.Thread) and thread.archived:
            await thread.edit(archived=False)
        await thread.send(embed=embed)
    except discord.HTTPException:
        traceback.print_exc()