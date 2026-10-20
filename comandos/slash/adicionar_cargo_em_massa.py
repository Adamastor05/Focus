import discord
from discord import app_commands
import re


def registrar_comando_adicionar_cargo_em_massa(
    bot,
    cargo_focus_adm_id,
    cargo_administrador_id,
    chat_logs_id
):

    @bot.tree.command(
        name="adicionar_cargo_em_massa",
        description="Adiciona um cargo a várias pessoas de uma vez."
    )
    @app_commands.describe(
        cargo="Cargo que será dado às pessoas.",
        pessoas="Cole aqui as menções das pessoas que receberão o cargo."
    )
    async def adicionar_cargo_em_massa(
        interaction: discord.Interaction,
        cargo: discord.Role,
        pessoas: str
    ):

        # ============================================================
        # VERIFICAR SERVIDOR
        # ============================================================

        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em um servidor.",
                ephemeral=True
            )
            return

        # ============================================================
        # VERIFICAR PERMISSÃO
        # ============================================================

        cargos_usuario = [
            role.id for role in interaction.user.roles
        ]

        if (
            cargo_focus_adm_id not in cargos_usuario
            and cargo_administrador_id not in cargos_usuario
        ):
            await interaction.response.send_message(
                "❌ Você não possui permissão para usar este comando.",
                ephemeral=True
            )
            return

        # ============================================================
        # VERIFICAR HIERARQUIA DO BOT
        # ============================================================

        bot_member = interaction.guild.me

        if bot_member is None:
            await interaction.response.send_message(
                "❌ Não consegui identificar o bot no servidor.",
                ephemeral=True
            )
            return

        if cargo >= bot_member.top_role:
            await interaction.response.send_message(
                "❌ Não posso adicionar esse cargo porque ele está "
                "acima ou no mesmo nível do meu cargo.",
                ephemeral=True
            )
            return

        # ============================================================
        # EXTRAIR IDs DAS MENÇÕES
        # ============================================================

        ids = re.findall(
            r"<@!?(\d+)>",
            pessoas
        )

        # Também permite colar IDs diretamente
        if not ids:
            ids = re.findall(
                r"\b\d{17,20}\b",
                pessoas
            )

        # Remover IDs duplicados
        ids = list(dict.fromkeys(ids))

        if not ids:
            await interaction.response.send_message(
                "❌ Não encontrei nenhuma pessoa.\n\n"
                "Cole as menções, por exemplo:\n"
                "`@João @Maria @Pedro`",
                ephemeral=True
            )
            return

        # ============================================================
        # AVISAR AO DISCORD QUE VAI PROCESSAR
        # ============================================================

        await interaction.response.defer(ephemeral=True)

        # ============================================================
        # LOCALIZAR MEMBROS
        # ============================================================

        membros = []
        nao_encontrados = []

        for membro_id in ids:

            membro = interaction.guild.get_member(
                int(membro_id)
            )

            if membro is None:
                try:
                    membro = await interaction.guild.fetch_member(
                        int(membro_id)
                    )
                except (
                    discord.NotFound,
                    discord.Forbidden,
                    discord.HTTPException
                ):
                    membro = None

            if membro is None:
                nao_encontrados.append(membro_id)
                continue

            membros.append(membro)

        # ============================================================
        # NENHUM MEMBRO ENCONTRADO
        # ============================================================

        if not membros:
            await interaction.followup.send(
                "❌ Não consegui encontrar nenhuma das pessoas "
                "informadas no servidor.",
                ephemeral=True
            )
            return

        # ============================================================
        # ADICIONAR CARGO
        # ============================================================

        adicionados = []
        ja_possuiam = []
        erros = []

        for membro in membros:

            if cargo in membro.roles:
                ja_possuiam.append(membro)
                continue

            try:

                await membro.add_roles(
                    cargo,
                    reason=(
                        f"/adicionar_cargo_em_massa usado por "
                        f"{interaction.user} "
                        f"({interaction.user.id})"
                    )
                )

                adicionados.append(membro)

            except (
                discord.Forbidden,
                discord.HTTPException
            ):
                erros.append(membro)

        # ============================================================
        # RESPOSTA EFÊMERA
        # ============================================================

        mensagem = (
            "🎖️ **Adição de cargo concluída!**\n\n"
            f"**Cargo:** {cargo.mention}\n"
            f"👥 Pessoas encontradas: **{len(membros)}**\n"
            f"➕ Cargo adicionado: **{len(adicionados)}**\n"
            f"☑️ Já possuíam: **{len(ja_possuiam)}**\n"
            f"❌ Erros: **{len(erros)}**"
        )

        if nao_encontrados:
            mensagem += (
                f"\n⚠️ Não encontradas: "
                f"**{len(nao_encontrados)}**"
            )

        await interaction.followup.send(
            mensagem,
            ephemeral=True
        )

        # ============================================================
        # EMBED DE LOG
        # ============================================================

        embed_log = discord.Embed(
            title="🎖️ Adição de cargo em massa",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )

        # ============================================================
        # QUEM USOU
        # ============================================================

        embed_log.add_field(
            name="👤 Quem usou",
            value=(
                f"{interaction.user.display_name}\n"
                f"`{interaction.user.id}`"
            ),
            inline=False
        )

        # ============================================================
        # CARGO
        # ============================================================

        embed_log.add_field(
            name="🎖️ Cargo concedido",
            value=(
                f"<@&{cargo.id}>\n"
                f"`{cargo.id}`"
            ),
            inline=False
        )

        # ============================================================
        # QUEM GANHOU
        # ============================================================

        if adicionados:

            pessoas_adicionadas = "\n".join(
                f"<@{membro.id}> — `{membro.id}`"
                for membro in adicionados
            )

        else:
            pessoas_adicionadas = "Ninguém."

        embed_log.add_field(
            name=f"➕ Quem ganhou o cargo ({len(adicionados)})",
            value=pessoas_adicionadas[:1024],
            inline=False
        )

        # ============================================================
        # QUEM JÁ POSSUÍA
        # ============================================================

        if ja_possuiam:

            pessoas_que_ja_possuiam = "\n".join(
                f"<@{membro.id}> — `{membro.id}`"
                for membro in ja_possuiam
            )

        else:
            pessoas_que_ja_possuiam = "Ninguém."

        embed_log.add_field(
            name=f"☑️ Já possuíam o cargo ({len(ja_possuiam)})",
            value=pessoas_que_ja_possuiam[:1024],
            inline=False
        )

        # ============================================================
        # ERROS
        # ============================================================

        if erros:

            pessoas_com_erro = "\n".join(
                f"<@{membro.id}> — `{membro.id}`"
                for membro in erros
            )

        else:
            pessoas_com_erro = "Nenhum."

        embed_log.add_field(
            name=f"❌ Erros ({len(erros)})",
            value=pessoas_com_erro[:1024],
            inline=False
        )

        # ============================================================
        # NÃO ENCONTRADAS
        # ============================================================

        if nao_encontrados:

            nao_encontradas_texto = "\n".join(
                f"`{id_membro}`"
                for id_membro in nao_encontrados
            )

            embed_log.add_field(
                name="⚠️ Pessoas não encontradas",
                value=nao_encontradas_texto[:1024],
                inline=False
            )

        embed_log.set_thumbnail(
            url=interaction.user.display_avatar.url
        )

        embed_log.set_footer(
            text="Sistema de adição de cargos"
        )

        # ============================================================
        # ENVIAR LOG
        # ============================================================

        canal_logs = interaction.guild.get_channel(
            chat_logs_id
        )

        if canal_logs is None:
            try:
                canal_logs = await bot.fetch_channel(
                    chat_logs_id
                )
            except (
                discord.NotFound,
                discord.Forbidden,
                discord.HTTPException
            ):
                canal_logs = None

        if canal_logs is not None:

            try:

                await canal_logs.send(
                    embed=embed_log,
                    allowed_mentions=discord.AllowedMentions.none()
                )

            except discord.Forbidden:

                print(
                    "[CARGO EM MASSA] "
                    "Não tenho permissão para enviar "
                    "mensagens no canal de logs."
                )

            except discord.HTTPException as e:

                print(
                    f"[CARGO EM MASSA] "
                    f"Erro ao enviar log: {e}"
                )