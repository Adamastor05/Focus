from collections import defaultdict

import discord
from discord.ext import commands


def registrar_comando_ranking_mdd(
    bot: commands.Bot,
    chat_mensagem_do_dia_id: int,
) -> None:
    @bot.tree.command(
        name="ranking_mdd",
        description="Mostra o ranking de participação no chat de mensagem do dia.",
    )
    async def ranking_mdd(
        interaction: discord.Interaction,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "Este comando só pode ser usado em um servidor.",
                ephemeral=True,
            )
            return

        canal = interaction.guild.get_channel(chat_mensagem_do_dia_id)
        if canal is None:
            await interaction.response.send_message(
                "Não encontrei o canal de mensagens do dia.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        quantidade = defaultdict(int)
        dias_usuario = defaultdict(set)
        primeira_mensagem = {}
        usuarios = {}
        mensagens_por_dia = defaultdict(int)

        async for mensagem in canal.history(limit=None, oldest_first=True):
            if mensagem.author.bot:
                continue

            dia = mensagem.created_at.date()
            usuario_id = mensagem.author.id

            quantidade[usuario_id] += 1
            dias_usuario[usuario_id].add(dia)
            mensagens_por_dia[dia] += 1
            usuarios[usuario_id] = mensagem.author

            if usuario_id not in primeira_mensagem:
                primeira_mensagem[usuario_id] = mensagem.created_at

        if not mensagens_por_dia:
            await interaction.followup.send(
                "Não há mensagens no histórico desse canal."
            )
            return

        dias_com_mensagem = set(mensagens_por_dia)
        total_dias = len(dias_com_mensagem)
        ranking_normal = []
        ranking_incompleto = []

        for usuario_id, total_mensagens in quantidade.items():
            autor = usuarios[usuario_id]
            eh_deleted_user = (
                (getattr(autor, "name", "") or "").lower() == "deleted_user"
                or (
                    (getattr(autor, "global_name", "") or "").lower()
                    == "deleted_user"
                )
            )
            dias_participados = dias_usuario[usuario_id]
            participou_de_todos = dias_participados == dias_com_mensagem
            item = {
                "id": usuario_id,
                "usuario": autor,
                "quantidade": total_mensagens,
                "primeira_mensagem": primeira_mensagem[usuario_id],
                "dias": len(dias_participados),
                "deleted": eh_deleted_user,
            }

            if eh_deleted_user or not participou_de_todos:
                ranking_incompleto.append(item)
            else:
                ranking_normal.append(item)

        ranking_normal.sort(
            key=lambda item: (
                -item["quantidade"],
                item["primeira_mensagem"],
            )
        )
        ranking_incompleto.sort(
            key=lambda item: (
                item["deleted"],
                -item["quantidade"],
                item["primeira_mensagem"],
            )
        )
        ranking_final = ranking_normal + ranking_incompleto

        embed = discord.Embed(
            title="🏆 Ranking de Mensagens do Dia",
            description=(
                f"Período analisado: **todo o histórico disponível**\n"
                f"Dias com atividade: **{total_dias}**"
            ),
            color=discord.Color.gold(),
        )
        linhas = []

        for posicao, item in enumerate(ranking_final, start=1):
            usuario = item["usuario"]
            quantidade_msg = item["quantidade"]
            dias = item["dias"]

            if posicao == 1:
                prefixo = "🥇"
            elif posicao == 2:
                prefixo = "🥈"
            elif posicao == 3:
                prefixo = "🥉"
            else:
                prefixo = f"`{posicao}.`"

            if item["deleted"]:
                status = " • `deleted_user`"
            elif dias < total_dias:
                status = f" • `{dias}/{total_dias} dias`"
            else:
                status = ""

            linhas.append(
                f"{prefixo} **{usuario.display_name}** — "
                f"**{quantidade_msg}** mensagens{status}"
            )

        partes = []
        atual = ""
        for linha in linhas:
            if len(atual) + len(linha) + 1 > 4000:
                partes.append(atual)
                atual = ""
            atual += linha + "\n"

        if atual:
            partes.append(atual)

        embed.description += "\n\n" + partes[0]
        await interaction.followup.send(embed=embed)

        for parte in partes[1:]:
            embed_extra = discord.Embed(
                description=parte,
                color=discord.Color.gold(),
            )
            await interaction.followup.send(embed=embed_extra)
