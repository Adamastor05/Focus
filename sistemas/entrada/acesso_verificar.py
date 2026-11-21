"""
acesso_verificar.py

Comando de prefixo `;acesso verificar` + listener de CARGO_VERIFICADO.

1) Staff (CARGO_TRIAGEM / CARGO_FOCUS_ADM / CARGO_ADM) usa `;acesso verificar` dentro do
   tópico da pessoa em CHAT_CONVITES. O id vem do nome do tópico.
   A própria mensagem `;acesso verificar` fica no tópico: apagá-la reverte a ação.

2) Quando a pessoa ganhar CARGO_VERIFICADO, o bot procura os tópicos dela em
   CHAT_CONVITES e procura ali mensagens `;acesso verificar`:
   - texto diferente de `;acesso verificar` exato -> avisa no tópico e nos logs;
   - autor sem cargo para usar o comando -> avisa no tópico e nos logs;
   - válida -> ativa o acesso_ao_servidor, apaga a mensagem, avisa no tópico
     quem usou e avisa nos logs.

No on_ready (antes do bot.tree.sync()):

    from sistemas.entrada.acesso_verificar import acesso_ao_verificar
    acesso_ao_verificar(bot)
"""

import logging
import re

import discord
from discord.ext import commands

from config.IDs import (
    CARGO_ADM,
    CARGO_FOCUS_ADM,
    CARGO_TRIAGEM,
    CARGO_VERIFICADO,
    CHAT_CONVITES,
)
from sistemas.entrada.acesso_ao_servidor import (
    acesso_ao_servidor,
    buscar_threads_por_id,
    enviar_logs,
    obter_canal,
)

logger = logging.getLogger(__name__)

TEXTO_COMANDO = ";acesso verificar"
CARGOS_PERMITIDOS = {CARGO_TRIAGEM, CARGO_FOCUS_ADM, CARGO_ADM}
LIMITE_MENSAGENS_THREAD = 500  # quantas mensagens de cada tópico olhar
SEM_MENCOES = discord.AllowedMentions.none()

_REGEX_ID = re.compile(r"\d{15,20}")

# evita rodar duas vezes ao mesmo tempo para a mesma pessoa
_em_verificacao: set[int] = set()


# ---------------------------------------------------------------------------
# UTILIDADES
# ---------------------------------------------------------------------------

def _id_do_nome(nome: str):
    """Último número de 15 a 20 dígitos do nome da thread."""
    achados = _REGEX_ID.findall(nome)
    return int(achados[-1]) if achados else None


def _tem_cargo_permitido(membro: discord.Member) -> bool:
    return any(r.id in CARGOS_PERMITIDOS for r in membro.roles)


async def _autor_autorizado(guild: discord.Guild, user_id: int) -> bool:
    membro = guild.get_member(user_id)
    if membro is None:
        try:
            membro = await guild.fetch_member(user_id)
        except discord.HTTPException:
            return False
    return _tem_cargo_permitido(membro)


# ---------------------------------------------------------------------------
# COMANDO ;acesso verificar
# ---------------------------------------------------------------------------

@commands.group(name="acesso", invoke_without_command=True)
async def acesso(ctx: commands.Context):
    """Grupo `;acesso`. Sozinho não faz nada; o subcomando é `;acesso verificar`."""
    return


@acesso.command(name="verificar")
@commands.guild_only()
async def verificar(ctx: commands.Context):
    msg = ctx.message

    if not isinstance(ctx.author, discord.Member) or not _tem_cargo_permitido(ctx.author):
        await msg.reply("Você não tem permissão para usar este comando.", mention_author=False)
        return

    canal = ctx.channel
    if not isinstance(canal, discord.Thread) or canal.parent_id != CHAT_CONVITES:
        await msg.reply(
            "❌ Use este comando dentro do tópico da pessoa em <#"
            f"{CHAT_CONVITES}>.",
            mention_author=False,
        )
        return

    user_id = _id_do_nome(canal.name)
    if user_id is None:
        await msg.reply(
            "❌ Não encontrei um id no nome deste tópico.", mention_author=False
        )
        return

    if msg.content != TEXTO_COMANDO:
        await msg.reply(
            f"❌ Use exatamente `{TEXTO_COMANDO}`, sem nada além disso.",
            mention_author=False,
        )
        return

    await msg.reply(
        f"Quando <@{user_id}> se verificar, darei acesso ao servidor. "
        "Para reverter isso, apague sua mensagem.",
        mention_author=False,
    )


# ---------------------------------------------------------------------------
# AO GANHAR CARGO_VERIFICADO
# ---------------------------------------------------------------------------

async def _preparar_thread(thread: discord.Thread):
    """Desarquiva a thread (se preciso) para poder apagar/enviar mensagens."""
    if thread.archived:
        try:
            await thread.edit(archived=False)
        except discord.HTTPException:
            pass


async def _processar_verificacao(bot, after: discord.Member):
    canal = await obter_canal(bot, CHAT_CONVITES)
    if canal is None:
        raise RuntimeError("CHAT_CONVITES não encontrado")

    threads = await buscar_threads_por_id(canal, after.id)
    if not threads:
        return  # sem tópico: ninguém usou ;acesso verificar

    validas: dict[discord.Thread, list[discord.Message]] = {}

    for t in threads:
        async for m in t.history(limit=LIMITE_MENSAGENS_THREAD):
            if m.author.bot:
                continue
            if not m.content.strip().lower().startswith(TEXTO_COMANDO):
                continue

            # texto diferente de ";acesso verificar" exato
            if m.content != TEXTO_COMANDO:
                try:
                    await m.reply(
                        f"⚠️ Esta mensagem parece o comando de verificação, mas não está "
                        f"exatamente como `{TEXTO_COMANDO}`. Apague e envie de novo, "
                        "exatamente assim, para eu poder dar o acesso.",
                    )
                except discord.HTTPException:
                    pass
                await enviar_logs(
                    bot,
                    f"⚠️ {after.mention} ganhou o cargo de verificado, mas a mensagem de "
                    f"{m.author.mention} em {t.mention} não está exatamente como "
                    f"`{TEXTO_COMANDO}`: {m.jump_url}",
                )
                continue

            # autor sem cargo para usar o comando
            if not await _autor_autorizado(after.guild, m.author.id):
                try:
                    await m.reply(
                        f"⚠️ O autor desta mensagem não tem cargo para usar `{TEXTO_COMANDO}`. "
                        "Ignorei.",
                        mention_author=False,
                    )
                except discord.HTTPException:
                    pass
                await enviar_logs(
                    bot,
                    f"⚠️ {after.mention} ganhou o cargo de verificado, mas {m.author.mention} "
                    f"não tem cargo para usar `{TEXTO_COMANDO}` ({t.mention}): {m.jump_url}",
                )
                continue

            validas.setdefault(t, []).append(m)

    if not validas:
        return

    # ativa o acesso (uma única vez, mesmo com vários tópicos/mensagens)
    await acesso_ao_servidor(bot, after)

    todos_autores: dict[int, discord.abc.User] = {}
    for t, mensagens in validas.items():
        await _preparar_thread(t)

        autores_thread: dict[int, discord.abc.User] = {}
        for m in mensagens:
            autores_thread[m.author.id] = m.author
            todos_autores[m.author.id] = m.author
            try:
                await m.delete()
            except discord.HTTPException as e:
                logger.warning("Falha ao apagar mensagem %s: %s", m.id, e)

        quem = ", ".join(a.mention for a in autores_thread.values())
        try:
            await t.send(
                f"✅ {after.mention} se verificou e o acesso ao servidor foi liberado. "
                f"O comando `{TEXTO_COMANDO}` foi usado por {quem}.",
                allowed_mentions=SEM_MENCOES,
            )
        except discord.HTTPException as e:
            logger.warning("Falha ao avisar na thread %s: %s", t.id, e)

    quem_logs = ", ".join(a.mention for a in todos_autores.values())
    await enviar_logs(
        bot,
        f"✅ {after.mention} (`{after.id}`) se verificou: acesso liberado via "
        f"`{TEXTO_COMANDO}` de {quem_logs}.",
    )


async def _on_member_update(bot, before: discord.Member, after: discord.Member):
    tinha = any(r.id == CARGO_VERIFICADO for r in before.roles)
    tem = any(r.id == CARGO_VERIFICADO for r in after.roles)
    if tinha or not tem:
        return

    if after.id in _em_verificacao:
        return
    _em_verificacao.add(after.id)
    try:
        await _processar_verificacao(bot, after)
    except Exception as e:
        logger.exception("Erro ao processar verificação de %s", after.id)
        await enviar_logs(
            bot,
            f"❌ Erro ao processar a verificação de {after.mention} (`{after.id}`): "
            f"`{type(e).__name__}: {e}`",
        )
    finally:
        _em_verificacao.discard(after.id)


# ---------------------------------------------------------------------------
# REGISTRO
# ---------------------------------------------------------------------------

def acesso_ao_verificar(bot):
    """Registra o comando ;acesso verificar e o listener de CARGO_VERIFICADO."""
    bot.add_command(acesso)

    async def on_member_update(before: discord.Member, after: discord.Member):
        await _on_member_update(bot, before, after)

    bot.add_listener(on_member_update, "on_member_update")