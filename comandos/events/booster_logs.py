"""
booster_logs.py

Todo dia às 00:10 (e também no on_ready):
  1. Lê a thread CHAT_THREAD_LOGS_BOOSTS_POR_PESSOA, onde ficam os boosts de cada pessoa.
  2. Quem está nessa thread mas não tem mais o cargo de booster tem a mensagem
     apagada, e o aviso é enviado em CHAT_LOGS.
  3. Envia na thread CHAT_THREAD_LOGS_BOOSTER uma mensagem por boost de cada booster.

Modelo da mensagem na thread de boosts por pessoa (uma mensagem por pessoa):

    ID: 123456789012345678 | Nome: joao | Boosts: 2

Para mudar a quantidade, basta EDITAR a mensagem.

Uso no main.py (sem cogs):

    import booster_logs
    booster_logs.setup(bot)
"""

import asyncio
import datetime
import re
from zoneinfo import ZoneInfo

import discord
from discord.ext import tasks

# ---------------------------------------------------------------------------
# CONFIG - ajuste os imports para onde você já define essas constantes
# ---------------------------------------------------------------------------
from config.IDs import (
    BIBLIA_EM_FOCO,
    CARGO_BOOSTER_NATIVO,
    CHAT_LOGS,
    CHAT_THREAD_LOGS_BOOSTER,
    CHAT_THREAD_LOGS_BOOSTS_POR_PESSOA,
)

FUSO = ZoneInfo("America/Sao_Paulo")
HORARIO = datetime.time(hour=0, minute=10, tzinfo=FUSO)

MARCADOR_SEM_BOOSTER = "Nenhum booster no servidor hoje."

RE_ID = re.compile(r"ID:\s*(\d{15,22})", re.IGNORECASE)
RE_BOOSTS = re.compile(r"Boosts?:\s*(\d+)", re.IGNORECASE)
RE_NOME = re.compile(r"Nome:\s*([^|\n]+)", re.IGNORECASE)

_lock = asyncio.Lock()
_bot: discord.Client | None = None


def _inicio_do_dia() -> datetime.datetime:
    agora = datetime.datetime.now(FUSO)
    return agora.replace(hour=0, minute=0, second=0, microsecond=0)


async def _obter_canal(bot, canal_id: int):
    canal = bot.get_channel(canal_id)
    if canal is None:
        try:
            canal = await bot.fetch_channel(canal_id)
        except discord.DiscordException as e:
            print(f"[booster_logs] não consegui acessar o canal {canal_id}: {e}")
            return None
    if getattr(canal, "archived", False):
        try:
            await canal.edit(archived=False)
        except discord.DiscordException as e:
            print(f"[booster_logs] não consegui desarquivar {canal_id}: {e}")
    return canal


async def _obter_boosters(bot) -> list[discord.Member] | None:
    """Retorna a lista de boosters, ou None se algo deu errado (para não
    confundir erro com 'nenhum booster' e apagar mensagens por engano)."""
    guild = bot.get_guild(BIBLIA_EM_FOCO)
    if guild is None:
        print("[booster_logs] servidor não encontrado")
        return None

    role = guild.get_role(CARGO_BOOSTER_NATIVO)
    if role is None:
        print("[booster_logs] cargo de booster não encontrado")
        return None

    if not guild.chunked:
        await guild.chunk()

    return list(role.members)


async def _ler_boosts_por_pessoa(thread) -> dict[int, dict]:
    """Lê a thread de boosts por pessoa. Retorna {id: {nome, boosts, mensagens}}."""
    entradas: dict[int, dict] = {}
    async for m in thread.history(limit=None, oldest_first=True):
        achou_id = RE_ID.search(m.content)
        if not achou_id:
            continue
        uid = int(achou_id.group(1))
        entrada = entradas.setdefault(
            uid, {"nome": "desconhecido", "boosts": 1, "mensagens": []}
        )
        entrada["mensagens"].append(m)

        achou_boosts = RE_BOOSTS.search(m.content)
        if achou_boosts:
            entrada["boosts"] = int(achou_boosts.group(1))
        achou_nome = RE_NOME.search(m.content)
        if achou_nome:
            entrada["nome"] = achou_nome.group(1).strip()
    return entradas


async def _remover_ex_boosters(bot, entradas: dict, ids_boosters: set[int]) -> None:
    """Apaga da thread de boosts por pessoa quem não tem mais o cargo e avisa em CHAT_LOGS."""
    canal_logs = None

    for uid, entrada in list(entradas.items()):
        if uid in ids_boosters:
            continue

        apagou_tudo = True
        for m in entrada["mensagens"]:
            try:
                await m.delete()
            except discord.NotFound:
                pass  # já foi apagada
            except discord.DiscordException as e:
                apagou_tudo = False
                print(f"[booster_logs] não consegui apagar a mensagem de {uid}: {e}")

        if not apagou_tudo:
            continue  # tenta de novo na próxima análise

        del entradas[uid]

        if canal_logs is None:
            canal_logs = await _obter_canal(bot, CHAT_LOGS)
        if canal_logs is not None:
            await canal_logs.send(
                f"⚠️ {entrada['nome']} (`{uid}`) não tem mais o cargo de booster. "
                f"A mensagem dela foi removida de <#{CHAT_THREAD_LOGS_BOOSTS_POR_PESSOA}>.",
                allowed_mentions=discord.AllowedMentions.none(),
            )


async def enviar_logs_booster(bot=None) -> None:
    """Limpa ex-boosters e envia as mensagens do dia que ainda não foram enviadas."""
    bot = bot or _bot

    # Lock: evita duplicar se o on_ready e o horário das 0:10 coincidirem
    async with _lock:
        thread_logs = await _obter_canal(bot, CHAT_THREAD_LOGS_BOOSTER)
        thread_pessoas = await _obter_canal(bot, CHAT_THREAD_LOGS_BOOSTS_POR_PESSOA)
        if thread_logs is None or thread_pessoas is None:
            return

        boosters = await _obter_boosters(bot)
        if boosters is None:
            return

        # 1) Lê os boosts por pessoa e remove quem saiu
        entradas = await _ler_boosts_por_pessoa(thread_pessoas)
        ids_boosters = {m.id for m in boosters}
        await _remover_ex_boosters(bot, entradas, ids_boosters)

        # 2) Logs diários
        mensagens_hoje = [
            m async for m in thread_logs.history(limit=None, after=_inicio_do_dia())
        ]

        if not boosters:
            ja_avisou = any(MARCADOR_SEM_BOOSTER in m.content for m in mensagens_hoje)
            if not ja_avisou:
                await thread_logs.send(MARCADOR_SEM_BOOSTER)
            return

        total_esperado = 0
        for member in boosters:
            entrada = entradas.get(member.id)
            if entrada is None:
                print(
                    f"[booster_logs] {member} ({member.id}) é booster mas não está "
                    f"na thread de boosts por pessoa; contando 1 boost."
                )
            qtd = max(1, entrada["boosts"]) if entrada else 1
            total_esperado += qtd

            # Quantas mensagens de hoje já citam o id (do bot ou manuais)
            ja_enviadas = sum(1 for m in mensagens_hoje if str(member.id) in m.content)

            for _ in range(max(0, qtd - ja_enviadas)):
                await thread_logs.send(f"{member.display_name} — `{member.id}`")
                await asyncio.sleep(0.5)  # evita rate limit

        guild = bot.get_guild(BIBLIA_EM_FOCO)
        if guild and guild.premium_subscription_count != total_esperado:
            print(
                f"[booster_logs] atenção: o servidor tem "
                f"{guild.premium_subscription_count} boosts, mas a soma na thread "
                f"de boosts por pessoa é {total_esperado}."
            )


@tasks.loop(time=HORARIO)
async def _loop_diario():
    await enviar_logs_booster()


@_loop_diario.before_loop
async def _antes_do_loop():
    await _bot.wait_until_ready()


async def _on_ready_booster_logs():
    await enviar_logs_booster()
    if not _loop_diario.is_running():
        _loop_diario.start()


def setup(bot: discord.Client) -> None:
    """Chame no main: booster_logs.setup(bot)"""
    global _bot
    _bot = bot
    bot.add_listener(_on_ready_booster_logs, "on_ready")