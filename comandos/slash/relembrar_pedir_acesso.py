from datetime import datetime, timezone

import discord
from discord.ext import commands


def registrar_comando_relembrar_pedir_acesso(
    bot: commands.Bot,
    cargo_administrador: int,
    cargo_pedir_acesso: int,
    chat_ticket: int,
    chat_logs: int,
) -> None:
    @bot.tree.command(
        name="relembrar_pedir_acesso",
        description="Lembra os membros de responderem ao pedido de acesso.",
    )
    async def relembrar_pedir_acesso(
        interaction: discord.Interaction,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "Este comando só pode ser usado em um servidor.",
                ephemeral=True,
            )
            return

        if not any(
            role.id == cargo_administrador
            for role in interaction.user.roles
        ):
            await interaction.response.send_message(
                "Você não possui permissão para usar este comando.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        role = guild.get_role(cargo_pedir_acesso)
        forum = guild.get_channel(chat_ticket)
        logs = guild.get_channel(chat_logs)

        if role is None or forum is None or logs is None:
            faltantes = []
            if role is None:
                faltantes.append("cargo de pedir acesso")
            if forum is None:
                faltantes.append("fórum de tickets")
            if logs is None:
                faltantes.append("canal de logs")

            await interaction.followup.send(
                "Não encontrei: " + ", ".join(faltantes) + ".",
                ephemeral=True,
            )
            return

        threads = list(forum.threads)
        async for thread in forum.archived_threads(limit=None):
            threads.append(thread)

        enviados = 0
        sem_topico = 0
        ignorados = 0

        for membro in role.members:
            if membro.joined_at is None:
                ignorados += 1
                continue

            tempo_no_servidor = (
                datetime.now(timezone.utc) - membro.joined_at
            )
            if tempo_no_servidor.total_seconds() <= 36 * 60 * 60:
                ignorados += 1
                continue

            thread_encontrada = next(
                (
                    thread
                    for thread in threads
                    if str(membro.id) in thread.name
                ),
                None,
            )

            if thread_encontrada is None:
                sem_topico += 1
                await logs.send(
                    f"⚠️ O membro **{membro}** (`{membro.id}`) "
                    f"não possui um tópico próprio em {forum.mention}."
                )
                continue

            dias = tempo_no_servidor.days
            await thread_encontrada.send(
                f"Olá, {membro.mention}!\n"
                f"Você está no servidor há **{dias} dias** e ainda não "
                "acessou o servidor. Leia as mensagens acima para darmos "
                "prosseguimento."
            )
            await logs.send(
                f"✅ Lembrete enviado para **{membro}** (`{membro.id}`) "
                f"no tópico {thread_encontrada.mention}."
            )
            enviados += 1

        await interaction.followup.send(
            "Envio de lembretes concluído.\n"
            f"✅ Lembretes enviados: **{enviados}**\n"
            f"⚠️ Sem tópico próprio: **{sem_topico}**\n"
            f"⏭️ Ignorados (menos de 36 horas ou sem data de entrada): "
            f"**{ignorados}**",
            ephemeral=True,
        )
