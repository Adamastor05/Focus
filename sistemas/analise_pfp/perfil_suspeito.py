"""Segunda parte: foto passou de 60 pontos.

- Embed em CHAT_PERFIS_SUSPEITOS (sem a foto), com nome, menção, id, descrição e resultado.
- Thread pública na embed: imagem + moderadores, análise da IA (vira a descrição) e
  o texto de "pedir para trocar" com os botões (e confirmação).
"""
import io

import discord

from config.IDs import CARGO_MODERADOR, CHAT_PERFIS_SUSPEITOS, CHAT_THREAD_DM_FECHADA
from comandos.slash.analisar_foto_perfil import (
    FalhaNasDuasIAs,
    achar_ticket,
    gerar_texto,
    id_na_dm_fechada,
    log,
    obter_canal,
    padrao_id,
    tem_permissao,
)

RESULTADO_INICIAL = "Em andamento"


# ======================= EMBED =======================
async def _mensagem_da_embed(thread: discord.Thread) -> discord.Message:
    """A thread foi criada a partir da embed, então o id da thread = id da mensagem."""
    canal = thread.parent or await thread.guild.fetch_channel(thread.parent_id)
    return await canal.fetch_message(thread.id)


def _indice_campo(embed: discord.Embed, nome: str) -> int | None:
    for i, campo in enumerate(embed.fields):
        if campo.name == nome:
            return i
    return None


async def atualizar_embed(
    thread: discord.Thread,
    *,
    descricao: str | None = None,
    resultado: str | None = None,
    acao: str | None = None,
):
    """Edita a embed do tópico: descrição, resultado e/ou acrescenta uma linha em "Ações"."""
    try:
        msg = await _mensagem_da_embed(thread)
        embed = msg.embeds[0]

        if descricao is not None:
            embed.description = descricao[:4000]

        if resultado is not None:
            i = _indice_campo(embed, "Resultado")
            if i is None:
                embed.add_field(name="Resultado", value=resultado[:1024], inline=False)
            else:
                embed.set_field_at(i, name="Resultado", value=resultado[:1024],
                                   inline=embed.fields[i].inline)

        if acao:
            linha = f"{discord.utils.format_dt(discord.utils.utcnow(), 'R')} {acao}"
            i = _indice_campo(embed, "Ações")
            if i is None:
                embed.add_field(name="Ações", value=linha[:1024], inline=False)
            else:
                novo = f"{embed.fields[i].value}\n{linha}"
                embed.set_field_at(i, name="Ações", value=novo[-1024:], inline=False)

        await msg.edit(embed=embed, allowed_mentions=discord.AllowedMentions.none())
    except (discord.HTTPException, IndexError) as e:
        print(f"[PERFIL] Não consegui editar a embed do tópico {thread.id}: {e}")


# ======================= TÓPICO ABERTO =======================
def buscar_caso_aberto(bot, uid: int) -> discord.Thread | None:
    """Thread ativa (não arquivada) dessa pessoa em CHAT_PERFIS_SUSPEITOS, pelo id no nome."""
    canal = bot.get_channel(CHAT_PERFIS_SUSPEITOS)
    if canal is None:
        return None
    padrao = padrao_id(uid)
    abertos = [t for t in canal.threads if not t.archived and padrao.search(t.name)]
    return max(abertos, key=lambda t: t.id) if abertos else None


async def avisar_troca_de_foto(thread: discord.Thread, membro: discord.Member, imagem: bytes):
    try:
        await thread.send(
            f"🔄 {membro.mention} trocou a foto de perfil. Nova foto abaixo (a análise dela vai no log).",
            file=discord.File(io.BytesIO(imagem), filename="nova_foto.png"),
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except discord.HTTPException as e:
        print(f"[PERFIL] Não consegui avisar a troca de foto no tópico {thread.id}: {e}")


async def avisar_nova_foto_suspeita(thread: discord.Thread, membro: discord.Member,
                                    suspeitas: dict[str, int]):
    resumo = ", ".join(f"{nome} ({valor}/100)" for nome, valor in suspeitas.items())
    try:
        await thread.send(
            f"⚠️ A nova foto de {membro.mention} também passou do limite: {resumo}.",
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except discord.HTTPException as e:
        print(f"[PERFIL] Não consegui avisar a nova foto suspeita no tópico {thread.id}: {e}")


# ======================= ABRIR CASO =======================
def _duracao_arquivamento(guild: discord.Guild) -> int:
    # 7 dias exigem boost nível 2; 3 dias, nível 1; 1 dia sempre pode.
    if guild.premium_tier >= 2:
        return 10080
    if guild.premium_tier >= 1:
        return 4320
    return 1440


async def abrir_caso(bot, membro: discord.Member, imagem: bytes,
                     suspeitas: dict[str, int], *,
                     denunciante: discord.abc.User | None = None) -> discord.Thread:
    """
    suspeitas: {"Nome da categoria": pontuação} das categorias acima de 60.
    denunciante: se vier, o caso é uma denúncia manual (botão "Denunciar imagem"):
                 não marca os moderadores e a IA analisa sem pontuação prévia.
    Retorna a thread criada.
    """
    canal = await obter_canal(bot, CHAT_PERFIS_SUSPEITOS)

    # ---------- embed (SEM a foto) ----------
    embed = discord.Embed(
        title="🚨 Foto de perfil suspeita",
        color=discord.Color.orange(),
        timestamp=discord.utils.utcnow(),
    )  # descrição vazia por enquanto
    embed.add_field(name="Nome", value=f"{membro.display_name} (@{membro.name})", inline=True)
    embed.add_field(name="Usuário", value=membro.mention, inline=True)
    embed.add_field(name="ID", value=f"`{membro.id}`", inline=True)
    embed.add_field(name="Resultado", value=RESULTADO_INICIAL, inline=False)

    msg = await canal.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    # ---------- thread pública na embed ----------
    thread = await msg.create_thread(
        name=f"Perfil — {membro.display_name[:50]} ({membro.id})",
        auto_archive_duration=_duracao_arquivamento(canal.guild),
    )

    resumo = ", ".join(f"{nome} ({valor}/100)" for nome, valor in suspeitas.items())
    arquivo = discord.File(io.BytesIO(imagem), filename="foto_de_perfil.png")

    if denunciante is not None:
        # denúncia manual: NÃO marca os moderadores
        await thread.send(
            f"🚩 Imagem de {membro.mention} denunciada por {denunciante.mention}.",
            file=arquivo,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        obs = (
            "Esta foto de perfil foi denunciada manualmente, sem pontuação automática. "
            "Explique o que há de errado nela, se houver algo."
        )
    else:
        role = canal.guild.get_role(CARGO_MODERADOR)
        mencao = role.mention if role else ""
        await thread.send(
            f"{mencao} foto de perfil de {membro.mention} acima do limite: {resumo}.".strip(),
            file=arquivo,
            allowed_mentions=(
                discord.AllowedMentions(roles=[role]) if role else discord.AllowedMentions.none()
            ),
        )
        obs = (
            f"A triagem automática deu pontuação alta (acima de 60) em: {resumo}. "
            "Explique o que há de errado nesta foto de perfil."
        )

    # ---------- texto 1: pedir para trocar (com botões) ----------
    try:
        r = await gerar_texto(imagem, "trocar", None)
    except FalhaNasDuasIAs as e:
        await thread.send(
            "⚠️ Não consegui gerar o texto de \"pedir para trocar\": o **Gemini** e a **Groq** falharam."
        )
        await log(bot, "Perfil suspeito (texto de pedir para trocar falhou)",
                  f"Membro: {membro} ({membro.id})\nGemini: `{e.motivo_gemini}`\nGroq: `{e.motivo_groq}`")
    else:
        texto = r["texto"]
        pedido = discord.Embed(
            title="Pedir para trocar",
            description=texto[:4000],
            color=discord.Color.blurple(),
        )
        pedido.set_footer(text=f"Gerado por: {r['provedor']}")
        view = PainelTrocaView(bot, membro, texto, thread)
        # guarda a mensagem para poder desativar os botões e avisar na embed depois
        view.message = await thread.send(embed=pedido, view=view)

    # ---------- texto 2: análise (vira a descrição) ----------
    try:
        r = await gerar_texto(imagem, "analisar", obs)
    except FalhaNasDuasIAs as e:
        await thread.send(
            "⚠️ Não consegui gerar a análise: o **Gemini** e a **Groq** falharam. "
            "Dá para usar o `/analisar_foto_de_perfil` manualmente."
        )
        await log(bot, "Perfil suspeito (análise da IA falhou)",
                  f"Membro: {membro} ({membro.id})\nGemini: `{e.motivo_gemini}`\nGroq: `{e.motivo_groq}`")
    else:
        texto = r["texto"]
        await atualizar_embed(thread, descricao=texto)
        analise = discord.Embed(title="Análise da IA", description=texto[:4000],
                                color=discord.Color.blurple())
        analise.set_footer(text=f"Analisado por: {r['provedor']}")
        await thread.send(embed=analise)

    return thread


# ======================= CONFIRMAÇÃO =======================
class ConfirmarView(discord.ui.View):
    """Mensagem efêmera com Confirmar / Cancelar; só quem clicou no botão original responde."""

    def __init__(self, autor_id: int, executar):
        super().__init__(timeout=60)
        self.autor_id = autor_id
        self.executar = executar

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.autor_id:
            return True
        await interaction.response.send_message("Esse botão não é seu.", ephemeral=True)
        return False

    @discord.ui.button(label="Confirmar", style=discord.ButtonStyle.success)
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.edit_message(content="Enviando...", view=None)
        await self.executar(interaction)

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary)
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.edit_message(content="Envio cancelado.", view=None)


# ======================= BOTÕES =======================
class PainelTrocaView(discord.ui.View):
    def __init__(self, bot, alvo: discord.Member, texto: str, thread: discord.Thread):
        super().__init__(timeout=None)
        self.bot = bot
        self.alvo = alvo
        self.texto = texto
        self.thread = thread
        self.message: discord.Message | None = None  # mensagem "Pedir para trocar"

    async def _marcar_enviado_privado(self, quem: discord.abc.User):
        """Desativa os botões e avisa na embed de "pedir para trocar"."""
        for item in self.children:
            item.disabled = True
        if self.message is None:
            return
        try:
            embed = self.message.embeds[0]
            embed.add_field(
                name="📨 Enviado no privado",
                value=(
                    f"{quem.mention} enviou esta mensagem no privado de {self.alvo.mention} "
                    f"{discord.utils.format_dt(discord.utils.utcnow(), 'R')}."
                ),
                inline=False,
            )
            await self.message.edit(embed=embed, view=self)
        except (discord.HTTPException, IndexError) as e:
            print(f"[PERFIL] Não consegui atualizar a mensagem de pedir para trocar: {e}")

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if tem_permissao(interaction.user):
            return True
        await interaction.response.send_message(
            "Você não tem permissão para usar esses botões.", ephemeral=True
        )
        return False

    async def _confirmar(self, interaction: discord.Interaction, pergunta: str, executar):
        await interaction.response.send_message(
            pergunta, view=ConfirmarView(interaction.user.id, executar), ephemeral=True
        )

    # ---------- privado ----------
    @discord.ui.button(label="Enviar para o privado", style=discord.ButtonStyle.primary)
    async def enviar_privado(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._confirmar(
            interaction,
            f"Enviar a mensagem no privado de {self.alvo.mention}?",
            self._executar_privado,
        )

    async def _executar_privado(self, interaction: discord.Interaction):
        quem = f"{interaction.user} ({interaction.user.id})"
        alvo = f"{self.alvo} ({self.alvo.id})"

        try:
            fechada = await id_na_dm_fechada(self.bot, self.alvo.id)
        except discord.HTTPException as e:
            await interaction.followup.send(
                "Não consegui ler a thread de DM fechada, então não enviei.", ephemeral=True
            )
            await log(self.bot, "Perfil: enviar no privado (erro)",
                      f"Por: {quem}\nPessoa: {alvo}\nErro ao ler a thread de DM fechada: `{e}`")
            return

        if fechada:
            await interaction.followup.send(
                "Não enviei: o id da pessoa está na thread de DM fechada.", ephemeral=True
            )
            await log(self.bot, "Perfil: enviar no privado (bloqueado)",
                      f"Por: {quem}\nPessoa: {alvo}\nMotivo: id está na thread de DM fechada.")
            await atualizar_embed(
                self.thread,
                acao=f"⚠️ {interaction.user.mention} tentou enviar no privado, mas o id está na thread de DM fechada.",
            )
            return

        try:
            await self.alvo.send(self.texto[:2000])
        except (discord.Forbidden, discord.HTTPException):
            try:
                thread_dm = await obter_canal(self.bot, CHAT_THREAD_DM_FECHADA)
                await thread_dm.send(str(self.alvo.id))
            except discord.HTTPException:
                pass
            await interaction.followup.send(
                "Não consegui enviar no privado (DM fechada). Registrei o id na thread.",
                ephemeral=True,
            )
            await log(self.bot, "Perfil: enviar no privado (falhou)",
                      f"Por: {quem}\nPessoa: {alvo}\nA DM falhou; id enviado na thread de DM fechada.")
            await atualizar_embed(
                self.thread,
                acao=f"⚠️ {interaction.user.mention} tentou enviar no privado, mas a DM está fechada.",
            )
            return

        await interaction.followup.send("Mensagem enviada no privado.", ephemeral=True)
        await log(self.bot, "Perfil: enviar no privado (sucesso)",
                  f"Por: {quem}\nPessoa: {alvo}\n\nMensagem:\n{self.texto}")
        await atualizar_embed(
            self.thread,
            acao=f"📨 {interaction.user.mention} enviou a mensagem no privado de {self.alvo.mention} pelo bot.",
        )
        await self._marcar_enviado_privado(interaction.user)

    # ---------- ticket ----------
    @discord.ui.button(label="Enviar para o ticket de início", style=discord.ButtonStyle.secondary)
    async def enviar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._confirmar(
            interaction,
            f"Enviar a mensagem no ticket de entrada de {self.alvo.mention}?",
            self._executar_ticket,
        )

    async def _executar_ticket(self, interaction: discord.Interaction):
        quem = f"{interaction.user} ({interaction.user.id})"
        alvo = f"{self.alvo} ({self.alvo.id})"

        try:
            ticket = await achar_ticket(self.bot, self.alvo.id)
        except discord.HTTPException as e:
            await interaction.followup.send("Erro ao procurar o ticket.", ephemeral=True)
            await log(self.bot, "Perfil: enviar no ticket (erro)",
                      f"Por: {quem}\nPessoa: {alvo}\nErro: `{e}`")
            return

        if ticket is None:
            await interaction.followup.send(
                "Não encontrei nenhum ticket de entrada com o id dessa pessoa.", ephemeral=True
            )
            await log(self.bot, "Perfil: enviar no ticket (não encontrado)",
                      f"Por: {quem}\nPessoa: {alvo}\nNenhum tópico com o id no título.")
            return

        try:
            await ticket.send(
                f"{self.alvo.mention} {self.texto}"[:2000],
                allowed_mentions=discord.AllowedMentions(users=[self.alvo]),
            )
        except discord.HTTPException as e:
            await interaction.followup.send(
                f"Achei o ticket ({ticket.mention}), mas não consegui enviar.", ephemeral=True
            )
            await log(self.bot, "Perfil: enviar no ticket (falhou)",
                      f"Por: {quem}\nPessoa: {alvo}\nTicket: {ticket.mention}\nErro: `{e}`")
            return

        await interaction.followup.send(f"Mensagem enviada em {ticket.mention}.", ephemeral=True)
        await log(self.bot, "Perfil: enviar no ticket (sucesso)",
                  f"Por: {quem}\nPessoa: {alvo}\nTicket: {ticket.mention}\n\nMensagem:\n{self.texto}")

    # ---------- manualmente ----------
    @discord.ui.button(label="Manualmente", style=discord.ButtonStyle.danger)
    async def manualmente(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        await log(self.bot, "Perfil: manualmente",
                  f"Por: {interaction.user} ({interaction.user.id})\n"
                  f"Pessoa: {self.alvo} ({self.alvo.id})\nBotões desativados.")