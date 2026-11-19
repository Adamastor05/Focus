#region IMPORTS
import discord
from discord.ext import commands
from discord import app_commands
from discord.utils import get
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
import os
import json
import asyncio
import re
import time
import io
import subprocess
from discord.ext import tasks
from zoneinfo import ZoneInfo
from datetime import time, datetime, timezone, timedelta
from collections import defaultdict
from config.tokens import TOKEN
from config.versao import VERSAO_ATUAL

from google import genai
from google.genai import types
from gemini_manager import proxima_api, marcar_api_como_indisponivel

bot = commands.Bot(command_prefix=";", intents=intents, help_command=None)
#endregion

# VERSÃO 3.1 -------------------------------------------

import comandos.events.contador_emojis
comandos.events.contador_emojis.registrar(bot)

import comandos.events.booster_logs
comandos.events.booster_logs.setup(bot)

import comandos.events.analisar_mdd
comandos.events.analisar_mdd.setup(bot)

import sistemas.manipular_cargos.slash.salvar_cargos_thread
sistemas.manipular_cargos.slash.salvar_cargos_thread.setup(bot)
# e lembre de dar o sync da árvore (await bot.tree.sync()) depois de registrar

from comandos.events.listeners.on_ready import registrar_evento_on_ready
registrar_evento_on_ready(bot)

# VERSÃO 3.2 -----------------------------------------
from comandos.slash.resumir_conversa import registrar_comando_resumir_conversa
registrar_comando_resumir_conversa(bot)

from sistemas.entrada.acesso_ao_servidor import registrar as registrar_acesso
from sistemas.entrada.botao_acesso import registrar_botao_acesso


#region ;Ping e on_ready

@bot.command()
async def ping(ctx):
    await ctx.send(f"""-# {VERSAO_ATUAL} complementar""")

from config.IDs import CHAT_LOGS

@bot.event
async def on_ready():

        global agendador_mensagens_task

        await bot.tree.sync()

        print(f"Logado como {bot.user}")

        channel = bot.get_channel(CHAT_LOGS)

        if channel is not None:
            await channel.send(
                f"""🟢 "Não é bom que esteja só." — Gn 2.18b
-# 📁** `Focus {VERSAO_ATUAL}` **"""
            )
#endregion

bot.run(TOKEN)