"""
Adiciona o CARGO_TEMPO a todos os membros a partir das 23:00 (Brasília),
parando quando todos tiverem o cargo ou ao chegar em 23:58 (o que vier primeiro).

Uso no main:
    from sistemas.timed_roles.events import adicionar_cargo_tempo
    adicionar_cargo_tempo.setup(bot)
"""
import logging

import discord

from .agendador import agendar_diario, agora, cargos_encontrados, horario_hoje, obter_membros

log = logging.getLogger("timed_roles")

# ===================== CONFIGURAÇÃO =====================
HORA_INICIO, MINUTO_INICIO = 23, 0     # quando começa
HORA_LIMITE, MINUTO_LIMITE = 23, 58    # hora em que PARA, mesmo que falte gente
INCLUIR_BOTS = False                   # True = também adiciona nos bots
ORDEM_REVERSA = True                   # começa do fim da lista p/ não competir com o outro bot
# ========================================================


async def processar_guild(guild: discord.Guild, cargo: discord.Role):
    if not cargo.is_assignable():
        log.error("[adicionar_cargo] sem permissão para gerenciar o cargo %s.", cargo.name)
        return

    limite = horario_hoje(HORA_LIMITE, MINUTO_LIMITE)
    membros = await obter_membros(guild)
    if ORDEM_REVERSA:
        membros.reverse()

    adicionados = pulados = falhas = 0

    for membro in membros:
        if agora() >= limite:
            log.info("[adicionar_cargo] %s: chegou ao horário limite.", guild.name)
            break
        if membro.bot and not INCLUIR_BOTS:
            continue
        # O cache é atualizado em tempo real pelo Discord: se o outro bot já
        # deu o cargo, a gente simplesmente pula (evita requisição repetida).
        if cargo in membro.roles:
            pulados += 1
            continue
        try:
            await membro.add_roles(cargo, reason="Cargo tempo (automático)")
            adicionados += 1
        except discord.Forbidden:
            falhas += 1
        except discord.HTTPException as e:
            falhas += 1
            log.warning("[adicionar_cargo] falha em %s: %s", membro, e)

    log.info("[adicionar_cargo] %s: adicionados=%d | já tinham=%d | falhas=%d",
             guild.name, adicionados, pulados, falhas)


async def executar(bot):
    for guild, cargo in cargos_encontrados(bot):
        await processar_guild(guild, cargo)


def setup(bot):
    agendar_diario(bot, "adicionar_cargo", HORA_INICIO, MINUTO_INICIO, executar)