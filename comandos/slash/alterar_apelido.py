from datetime import datetime
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands


def registrar_comando_alterar_apelido(
    bot: commands.Bot,
    cargo_destaque_do_dia_id: int,
    cargo_booster_id: int,
    chat_logs_threads_apelidos_id: int,
) -> None:
    @app_commands.command(
        name="alterar_apelido",
        description="Altera o apelido de outro membro.",
    )
    @app_commands.describe(
        pessoa="Nome, apelido, menção ou ID da pessoa",
        novo_apelido="Novo apelido da pessoa",
    )
    async def alterar_apelido(
        interaction: discord.Interaction,
        pessoa: str,
        novo_apelido: str,
    ) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "❌ Este comando só pode ser usado dentro de um servidor.",
                ephemeral=True,
            )
            return

        possui_permissao = (
            cargo_destaque_do_dia_id
            in [cargo.id for cargo in interaction.user.roles]
            or cargo_booster_id
            in [cargo.id for cargo in interaction.user.roles]
        )
        if not possui_permissao:
            await interaction.response.send_message(
                "❌ Você precisa possuir o cargo "
                "`cargo_destaque_do_dia` ou `cargo_booster` "
                "para usar este comando.",
                ephemeral=True,
            )
            return

        pessoa = pessoa.strip()
        membro = None
        texto_id = (
            pessoa
            .replace("<@", "")
            .replace("!", "")
            .replace(">", "")
        )
        if texto_id.isdigit():
            membro = guild.get_member(int(texto_id))

        if membro is None:
            pessoa_lower = pessoa.lower()
            membro = discord.utils.find(
                lambda candidato: (
                    candidato.name.lower() == pessoa_lower
                    or candidato.display_name.lower() == pessoa_lower
                ),
                guild.members,
            )

        if membro is None:
            await interaction.response.send_message(
                "❌ Não encontrei essa pessoa no servidor.\n\n"
                "Você pode informar o nome, apelido, @menção ou ID.",
                ephemeral=True,
            )
            return

        novo_apelido = novo_apelido.strip()
        if not novo_apelido:
            await interaction.response.send_message(
                "❌ O novo apelido não pode estar vazio.",
                ephemeral=True,
            )
            return

        if len(novo_apelido) > 32:
            await interaction.response.send_message(
                "❌ O novo apelido pode ter no máximo 32 caracteres.",
                ephemeral=True,
            )
            return

        thread_logs = guild.get_thread(chat_logs_threads_apelidos_id)
        if thread_logs is None:
            try:
                thread_logs = await guild.fetch_channel(
                    chat_logs_threads_apelidos_id
                )
            except discord.NotFound:
                await interaction.response.send_message(
                    "❌ Não encontrei a thread de logs de apelidos.",
                    ephemeral=True,
                )
                return
            except discord.Forbidden:
                await interaction.response.send_message(
                    "❌ Não tenho permissão para acessar "
                    "a thread de logs de apelidos.",
                    ephemeral=True,
                )
                return
            except discord.HTTPException as erro:
                print(
                    f"[APELIDOS] Erro ao buscar thread de logs: {erro}"
                )
                await interaction.response.send_message(
                    "❌ Ocorreu um erro ao acessar a thread de logs.",
                    ephemeral=True,
                )
                return

        if not isinstance(thread_logs, discord.Thread):
            await interaction.response.send_message(
                "❌ O ID configurado em "
                "`chat_logs_threads_apelidos_DDD` "
                "não corresponde a uma thread.",
                ephemeral=True,
            )
            return

        agora = datetime.now(ZoneInfo("America/Sao_Paulo"))
        data_atual = agora.strftime("%Y-%m-%d")
        quantidade_alteracoes = 0

        try:
            async for mensagem in thread_logs.history(limit=None):
                texto = mensagem.content
                if not texto.startswith(data_atual):
                    continue
                if f"Executor: {interaction.user.id}" not in texto:
                    continue

                quantidade_alteracoes += 1
                if quantidade_alteracoes >= 3:
                    break
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Não tenho permissão para ler "
                "o histórico da thread de logs.",
                ephemeral=True,
            )
            return
        except discord.HTTPException as erro:
            print(
                f"[APELIDOS] Erro ao verificar histórico: {erro}"
            )
            await interaction.response.send_message(
                "❌ Ocorreu um erro ao verificar "
                "seu limite diário.",
                ephemeral=True,
            )
            return

        if quantidade_alteracoes >= 3:
            await interaction.response.send_message(
                "❌ Você já atingiu o limite de "
                "**3 alterações de apelido hoje**.",
                ephemeral=True,
            )
            return

        bot_member = guild.me
        if bot_member is None:
            await interaction.response.send_message(
                "❌ Não consegui identificar o bot no servidor.",
                ephemeral=True,
            )
            return

        if membro == guild.owner:
            await interaction.response.send_message(
                "❌ Não é possível alterar o apelido "
                "do dono do servidor.",
                ephemeral=True,
            )
            return

        if membro == bot_member:
            await interaction.response.send_message(
                "❌ Não posso alterar meu próprio apelido "
                "através deste comando.",
                ephemeral=True,
            )
            return

        if membro.top_role >= bot_member.top_role:
            await interaction.response.send_message(
                "❌ Não posso alterar o apelido dessa pessoa "
                "porque o cargo mais alto dela é igual ou "
                "superior ao meu.",
                ephemeral=True,
            )
            return

        apelido_antigo = membro.display_name
        try:
            await membro.edit(
                nick=novo_apelido,
                reason=(
                    f"Alteração de apelido por {interaction.user} "
                    f"({interaction.user.id})"
                ),
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ O Discord não permitiu alterar "
                "o apelido dessa pessoa.",
                ephemeral=True,
            )
            return
        except discord.HTTPException as erro:
            print(f"[APELIDOS] Erro ao alterar apelido: {erro}")
            await interaction.response.send_message(
                "❌ Ocorreu um erro ao alterar o apelido.",
                ephemeral=True,
            )
            return

        numero_alteracao = quantidade_alteracoes + 1
        mensagem_log = (
            f"{data_atual} | "
            f"Executor: {interaction.user.id} | "
            f"Alvo: {membro.id} | "
            f"Antigo: {apelido_antigo} | "
            f"Novo: {novo_apelido} | "
            f"Alteração: {numero_alteracao}/3"
        )
        try:
            await thread_logs.send(mensagem_log)
        except discord.Forbidden:
            await interaction.response.send_message(
                f"✅ O apelido de {membro.mention} "
                f"foi alterado para **{novo_apelido}**.\n\n"
                "⚠️ Porém, não consegui registrar "
                "a alteração na thread de logs.",
                ephemeral=True,
            )
            return
        except discord.HTTPException as erro:
            print(f"[APELIDOS] Erro ao registrar log: {erro}")

        await interaction.response.send_message(
            "✅ **Apelido alterado com sucesso!**\n\n"
            f"👤 **Pessoa:** {membro.mention}\n"
            f"📝 **Apelido anterior:** {apelido_antigo}\n"
            f"✏️ **Novo apelido:** {novo_apelido}\n"
            f"📊 **Alterações hoje:** {numero_alteracao}/3",
            ephemeral=True,
        )

    bot.tree.add_command(alterar_apelido)
