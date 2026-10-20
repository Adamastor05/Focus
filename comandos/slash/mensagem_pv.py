import discord
from discord import app_commands


def registrar_comando_mensagem_pv(
    cargo_moderador,
    bot,
    chat_logs
):

    # Mensagens prontas
    MENSAGENS = {
        "teste": "Apenas um teste.",
        "advertencia": "Olá! Esta é uma advertência. Pedimos que leia novamente as regras do servidor.",
        "foto1": "Sua foto infringe as regras do servidor, pedimos que troque.",
        "foto2": """⚠️ **Advertência**

    Esta advertência refere-se à sua foto de perfil anterior, que continha a imagem de uma mulher seminua (independentemente de ser você ou não), o que não é permitido em nosso servidor.

    Percebemos que a foto já foi alterada, o que resolve a situação. Ainda assim, esta advertência será registrada como orientação para que esse tipo de imagem não seja utilizado novamente.

    Em nosso servidor, solicitamos que fotos de perfil sejam compatíveis com a proposta cristã da comunidade. Em caso de reincidência, poderão ser aplicadas medidas de moderação mais severas.
        """
    }

    @bot.tree.command(name="mensagem_pv", description="Envia uma mensagem no privado de um usuário.")
    @app_commands.describe(
        usuario="Usuário que receberá a mensagem",
        predefinida="Escolha uma mensagem pronta",
        mensagem="Escreva uma mensagem personalizada"
    )
    @app_commands.choices(
        predefinida=[
            app_commands.Choice(name="Teste", value="teste"),
            app_commands.Choice(name="Advertência", value="advertencia"),
            app_commands.Choice(name="foto1", value="foto1"),
            app_commands.Choice(name="foto2", value="foto2")
        ]
    )
    async def mensagem(
        interaction: discord.Interaction,
        usuario: discord.Member,
        predefinida: app_commands.Choice[str] = None,
        mensagem: str = None
    ):

        if cargo_moderador not in [cargo.id for cargo in interaction.user.roles]:
            await interaction.response.send_message(
                "❌ Você não tem permissão para usar este comando.",
            ephemeral=True
            )
            return

        # Usa a mensagem personalizada caso exista
        if mensagem:
            texto = mensagem
        elif predefinida:
            texto = MENSAGENS[predefinida.value]
        else:
            await interaction.response.send_message(
                "Você precisa informar uma mensagem personalizada ou escolher uma mensagem predefinida.",
                ephemeral=True
            )
            return

        if usuario == bot.user:
            await interaction.response.send_message(
                "❌ Não é possível enviar uma mensagem privada para o próprio bot.",
                ephemeral=True
            )
            return
        try:
            await usuario.send(texto)
        except discord.Forbidden:
            await interaction.response.send_message(
                "Não foi possível enviar mensagem para esse usuário.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"✅ Mensagem privada enviada para {usuario.mention}.\n"
            f"-# Evite enviar muitas mensagens em pouco tempo.",
            ephemeral=True
        )

        canal_logs = interaction.guild.get_channel(chat_logs)

        if canal_logs:
            embed = discord.Embed(
                title="📨 Mensagem privada enviada",
                color=discord.Color.yellow()
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_author(
                name=f"Enviado por {interaction.user}",
                icon_url=interaction.user.display_avatar
            )
            embed.add_field(
                name="Enviado por",
                value=f"{interaction.user.mention}\n`{interaction.user.id}`",
                inline=False
            )
            embed.add_field(
                name="Destinatário",
                value=f"{usuario.mention}\n`{usuario.id}`",
                inline=False
            )
            embed.add_field(
                name="Mensagem",
                value=f"```{texto}```",
                inline=False
            )
            await canal_logs.send(embed=embed)
#endregion