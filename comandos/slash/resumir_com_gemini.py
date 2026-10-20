import discord
from discord.ext import commands
from google import genai

from gemini_manager import proxima_api


def registrar_comando_resumir_com_gemini(
    bot: commands.Bot,
    valentes: int,
) -> None:
    @bot.tree.command(
        name="resumir_com_gemini",
        description="Resume toda a conversa deste tópico usando IA.",
    )
    async def resumir_com_gemini(
        interaction: discord.Interaction,
    ) -> None:
        if not any(
            role.id == valentes
            for role in interaction.user.roles
        ):
            await interaction.response.send_message(
                "Você não tem permissão para usar este comando.",
                ephemeral=True,
            )
            return

        if not isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message(
                "Este comando só pode ser usado dentro de um tópico.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)
        conversa = ""

        async for mensagem in interaction.channel.history(
            limit=None,
            oldest_first=True,
        ):
            if not mensagem.content.strip():
                continue

            conversa += (
                f"{mensagem.author.display_name}: "
                f"{mensagem.content}\n"
            )

        if not conversa.strip():
            await interaction.followup.send(
                "Não encontrei mensagens para resumir."
            )
            return

        try:
            client = genai.Client(api_key=proxima_api())
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=f"""
Você é um moderador imparcial.

Leia toda a conversa abaixo e produza um resumo claro e organizado.

Sua resposta deve conter:

# Tema
Explique qual era o assunto principal.

# Resumo
Resuma toda a discussão de forma objetiva.

# Principais argumentos
Liste os principais argumentos apresentados por cada lado.

# Conclusão
Explique como terminou, sem tomar partido.

Não invente informações. Baseie-se apenas na conversa.

{conversa}
""",
            )

            resumo = response.text
        except Exception as erro:
            await interaction.followup.send(
                f"Erro ao gerar resumo:\n```{erro}```"
            )
            return

        if resumo is None:
            await interaction.followup.send(
                "O Gemini não retornou um resumo."
            )
            return

        if len(resumo) <= 2000:
            await interaction.followup.send(f"## 📝 Resumo\n\n{resumo}")
        else:
            await interaction.followup.send("## 📝 Resumo")

            for inicio in range(0, len(resumo), 2000):
                await interaction.followup.send(
                    resumo[inicio:inicio + 2000]
                )
