import re
from datetime import datetime, timezone

import discord
from discord import app_commands

from config.IDs import (
    cargo_genero_nao_informado,
    cargo_homem,
    cargo_mulher,
    cargo_recepcionista,
    chat_convites,
    chat_logs_thread_motivos,
    invite_tracker_bot,
)


data_corte_de_procurar_convites = datetime(2026, 7, 1, tzinfo=timezone.utc)


def registrar_comando_motivo(bot):
    @app_commands.context_menu(name="Motivo")
    async def motivo(interaction: discord.Interaction, message: discord.Message):
        # Permissão
        if not any(r.id == cargo_recepcionista for r in interaction.user.roles):
            return await interaction.response.send_message(
                "Você não possui permissão.",
                ephemeral=True
            )

        try:
            await message.add_reaction("✅")
        except discord.Forbidden:
            pass  # O bot não tem permissão para adicionar reações
        except discord.HTTPException:
            pass  # Falha ao adicionar a reação

        membro = message.author

        await interaction.channel.send(
        f"{membro.mention}"
    )

        # ---------------- Convite ----------------

        convite = "convite_vanity"

        canal_convites = bot.get_channel(chat_convites)

        if canal_convites is None:
            canal_convites = await bot.fetch_channel(chat_convites)

        async for msg in canal_convites.history(
        limit=None,
        after=data_corte_de_procurar_convites
    ):
            # Apenas mensagens do Invite Tracker Bot
            if msg.author.id != invite_tracker_bot:
                continue

            texto = msg.content

            # Verifica se é a mensagem desse membro
            if f"id: {membro.id}" not in texto.lower():
                continue

            encontrado = re.search(
                r"Convite:\s*([A-Za-z0-9_-]+)",
                texto,
                re.IGNORECASE
            )

            if encontrado:
                convite = encontrado.group(1)

            break

        # ---------------- Gênero ----------------

        if any(r.id == cargo_homem for r in membro.roles):
            genero = "Homem"

        elif any(r.id == cargo_mulher for r in membro.roles):
            genero = "Mulher"

        elif any(r.id == cargo_genero_nao_informado for r in membro.roles):
            genero = "Gênero não informado"

        else:
            genero = "Gênero não informado"

        # ---------------- Canal de logs ----------------

        canal_logs = bot.get_channel(chat_logs_thread_motivos)

        if canal_logs is None:
            canal_logs = await bot.fetch_channel(chat_logs_thread_motivos)

        texto_novo = message.content.strip()

        mensagem_existente = None

        async for msg in canal_logs.history(limit=None, oldest_first=True):

            if f"**ID:** {membro.id}" in msg.content:
                mensagem_existente = msg
                break

        if mensagem_existente:

            partes = mensagem_existente.content.split("**Mensagens:**", 1)

            mensagens = ""

            if len(partes) == 2:
                mensagens = partes[1].strip()

            if texto_novo not in mensagens:
                if mensagens:
                    mensagens += "\n"
                mensagens += texto_novo

            await mensagem_existente.edit(
                content=(
                    f"**ID:** {membro.id}\n"
                    f"**Convite:** {convite}\n"
                    f"**Gênero:** {genero}\n\n"
                    f"**Mensagens:**\n"
                    f"{mensagens}"
                )
            )

        else:

            await canal_logs.send(
                f"**ID:** {membro.id}\n"
                f"**Convite:** {convite}\n"
                f"**Gênero:** {genero}\n\n"
                f"**Mensagens:**\n"
                f"{texto_novo}"
            )

        await interaction.response.send_message(
            "Verifique o chat de logs.",
            ephemeral=True
        )

    bot.tree.add_command(motivo)
