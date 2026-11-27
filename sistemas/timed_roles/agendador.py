"""
Utilitários compartilhados pelos eventos de cargo temporário.
Sem cogs: cada evento chama `agendar_diario(bot, ...)` dentro do seu `setup(bot)`.
"""
import asyncio
import logging
import traceback
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo  # no Windows: pip install tzdata

import discord

from config.IDs import CARGO_TEMPO

log = logging.getLogger("timed_roles")

FUSO = ZoneInfo("America/Sao_Paulo")  # horário de Brasília


def agora() -> datetime:
    return datetime.now(FUSO)


def horario_hoje(hora: int, minuto: int) -> datetime:
    return agora().replace(hour=hora, minute=minuto, second=0, microsecond=0)


def proxima_execucao(hora: int, minuto: int) -> datetime:
    alvo = horario_hoje(hora, minuto)
    if alvo <= agora():
        alvo += timedelta(days=1)
    return alvo


def agendar_diario(bot, nome: str, hora: int, minuto: int, funcao):
    """
    Executa `await funcao(bot)` todo dia às hora:minuto (Brasília).
    Inicia sozinho quando o bot ficar pronto (on_ready).
    """
    estado = {"iniciado": False}

    async def loop_diario():
        await bot.wait_until_ready()
        while not bot.is_closed():
            alvo = proxima_execucao(hora, minuto)
            log.info("[%s] próxima execução: %s", nome, alvo.strftime("%d/%m %H:%M"))
            await asyncio.sleep(max(0, (alvo - agora()).total_seconds()))
            while agora() < alvo:  # garante que não dispara adiantado
                await asyncio.sleep(0.5)
            try:
                await funcao(bot)
            except Exception:
                log.error("[%s] erro:\n%s", nome, traceback.format_exc())

    async def iniciar():
        if estado["iniciado"]:  # on_ready pode disparar várias vezes
            return
        estado["iniciado"] = True
        bot.loop.create_task(loop_diario())

    # Se o bot já estiver rodando, inicia direto; senão espera o on_ready
    if bot.is_ready():
        bot.loop.create_task(iniciar())
    else:
        bot.add_listener(iniciar, "on_ready")


def cargos_encontrados(bot):
    """Retorna [(guild, cargo)] de todos os servidores que possuem o CARGO_TEMPO."""
    resultado = []
    for guild in bot.guilds:
        cargo = guild.get_role(CARGO_TEMPO)
        if cargo:
            resultado.append((guild, cargo))
    return resultado


async def obter_membros(guild: discord.Guild) -> list[discord.Member]:
    """Lista de membros (carrega o cache completo se necessário). Requer intents.members."""
    if not guild.chunked:
        await guild.chunk()
    return list(guild.members)


async def remover_cargo_de_membros(guild, cargo, filtro, nome, ordem_reversa=True, max_passadas=5):
    """
    Remove o cargo de todos os membros que passam em `filtro(member)`.
    Só para quando não sobrar ninguém (ou quando só restarem membros que o bot não consegue mexer).
    """
    if not cargo.is_assignable():
        log.error("[%s] sem permissão para gerenciar o cargo %s (verifique hierarquia/permissões).", nome, cargo.name)
        return

    if not guild.chunked:
        await guild.chunk()

    falhas = set()  # quem deu Forbidden (cargo acima do bot, dono do servidor etc.)
    removidos = 0

    for passada in range(1, max_passadas + 1):
        alvos = [m for m in cargo.members if filtro(m) and m.id not in falhas]
        if not alvos:
            break
        if ordem_reversa:
            alvos.reverse()  # evita "colidir" com o outro bot, que provavelmente vai na ordem normal

        for membro in alvos:
            if cargo not in membro.roles:  # o outro bot já removeu
                continue
            try:
                await membro.remove_roles(cargo, reason=f"{nome} (automático)")
                removidos += 1
            except discord.Forbidden:
                falhas.add(membro.id)
            except discord.HTTPException as e:
                log.warning("[%s] falha em %s: %s", nome, membro, e)

        await asyncio.sleep(2)  # dá tempo do cache receber os eventos antes da próxima passada

    restantes = [m for m in cargo.members if filtro(m)]
    log.info("[%s] %s: removido de %d | ainda com o cargo: %d (sem permissão: %d)",
             nome, guild.name, removidos, len(restantes), len(falhas))