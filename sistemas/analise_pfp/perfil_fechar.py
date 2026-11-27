"""Comando ;fechar nas threads de CHAT_PERFIS_SUSPEITOS."""
import discord

from config.IDs import CHAT_PERFIS_SUSPEITOS
from comandos.slash.analisar_foto_perfil import log, tem_permissao
from sistemas.analise_pfp.perfil_suspeito import atualizar_embed

COMANDO = ";fechar"
NAO_FECHAR = "Não fechar"
OPCOES = [
    "Trocou de foto",
    "Expulso/Banido",
    "Erro da IA",
    "Nenhum acima",
    NAO_FECHAR,
]


class FecharView(discord.ui.View):
    def __init__(self, bot, thread: discord.Thread, autor: discord.Member):
        super().__init__(timeout=300)
        self.bot = bot
        self.thread = thread
        self.autor = autor
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.autor.id:
            return True
        await interaction.response.send_message(
            "Só quem usou o comando pode responder.", ephemeral=True
        )
        return False

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass

    @discord.ui.select(
        placeholder="Selecione o motivo",
        options=[discord.SelectOption(label=o, value=o) for o in OPCOES],
    )
    async def escolher(self, interaction: discord.Interaction, select: discord.ui.Select):
        escolha = select.values[0]

        # desativa o menu
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

        sem_mencao = discord.AllowedMentions.none()

        if escolha == NAO_FECHAR:
            await self.thread.send(
                f"{self.autor.mention} escolheu não fechar o tópico.",
                allowed_mentions=sem_mencao,
            )
            return

        await atualizar_embed(self.thread, resultado=escolha)
        await self.thread.send(
            f"🔒 {self.autor.mention} fechou o tópico. Motivo: **{escolha}**.",
            allowed_mentions=sem_mencao,
        )
        await log(
            self.bot,
            "Perfil: tópico fechado",
            f"Por: {self.autor} ({self.autor.id})\nTópico: {self.thread.mention}\nMotivo: {escolha}",
        )

        try:
            await self.thread.edit(archived=True)
        except discord.HTTPException as e:
            print(f"[PERFIL] Não consegui arquivar o tópico {self.thread.id}: {e}")


def registrar_fechar_perfil(bot):
    @bot.listen("on_message")
    async def perfil_fechar_on_message(message: discord.Message):
        if message.author.bot or message.guild is None:
            return
        if message.content.strip().lower() != COMANDO:
            return

        canal = message.channel
        if not isinstance(canal, discord.Thread) or canal.parent_id != CHAT_PERFIS_SUSPEITOS:
            return

        if not tem_permissao(message.author):
            await message.reply(
                "Você não tem permissão para usar este comando.",
                delete_after=8,
                mention_author=False,
            )
            return

        view = FecharView(bot, canal, message.author)
        view.message = await message.reply(
            "Por que você quer fechar o tópico?",
            view=view,
            mention_author=False,
        )
