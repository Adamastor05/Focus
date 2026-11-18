import re
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from google import genai

from config.IDs import CHAT_LOGS_COMPOSTO, CHAT_THREAD_DM_FECHADA, valentes
from gemini_manager import (
    marcar_api_como_indisponivel,
    proxima_api,
    quantidade_apis,
)
from groq_manager import gerar_texto as groq_gerar_texto

GEMINI_MODELO = "gemini-3.6-flash"

# Códigos de erro em que vale a pena tentar outra API do Gemini
CODIGOS_TENTAR_OUTRA_API = (409, 429, 503)

# Limite de caracteres da conversa enviada à Groq (contexto menor)
LIMITE_CONVERSA_GROQ = 60000

# Segurança: máximo de mensagens lidas por execução
MAX_MENSAGENS = 5000

TAMANHO_EMBED = 4000

REGEX_LINK = re.compile(
    r"discord(?:app)?\.com/channels/(?:\d+|@me)/(\d+)/(\d+)"
)

PROMPTS = {
    "debate": """
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
""",
    "duvida": """
Leia a conversa abaixo e identifique as dúvidas (perguntas) que foram
feitas e as respostas que receberam.

Para cada dúvida, use este formato:

# Pergunta
Escreva a pergunta de forma clara.

# Resposta
Escreva a resposta que foi dada na conversa.

**Perguntou:** nome de quem fez a pergunta
**Respondeu:** nome de quem respondeu

Se uma pergunta não foi respondida, diga isso em "Resposta".
Repita o formato para cada dúvida.
Não invente informações. Baseie-se apenas na conversa.
""",
    "incoerencia": """
Você é um analista teológico que avalia a conversa pelos princípios
protestantes (as cinco solas: Sola Scriptura, Sola Fide, Sola Gratia,
Solus Christus e Soli Deo Gloria).

Leia a conversa abaixo e analise se o que foi dito está de acordo com
esses princípios.

Sua resposta deve conter:

# Tema
Qual era o assunto.

# Análise
Aponte o que está certo e o que está errado ou incoerente, citando
trechos da conversa e quem disse.

# Veredito
Diga claramente se está CERTO ou ERRADO segundo os princípios
protestantes (ou parcialmente certo, explicando o motivo).

Não invente informações. Baseie-se apenas na conversa.
""",
}

TITULOS = {
    "debate": "📝 Resumo do debate",
    "duvida": "❓ Dúvidas e respostas",
    "incoerencia": "⚖️ Análise de incoerência",
    "outro": "📝 Resumo personalizado",
}

AVISO_TAMANHO = (
    "\n\nSeja objetivo: a resposta deve ter no máximo cerca de 3500 caracteres."
)


# ---------------------------------------------------------------- utilidades
def extrair_referencia(texto: str) -> tuple[Optional[int], Optional[int]]:
    """Recebe um id ou link e devolve (id_do_canal | None, id_da_mensagem)."""
    texto = texto.strip()

    if texto.isdigit():
        return None, int(texto)

    achado = REGEX_LINK.search(texto)
    if achado:
        return int(achado.group(1)), int(achado.group(2))

    return None, None


def dividir_texto(texto: str, tamanho: int = TAMANHO_EMBED) -> list[str]:
    partes: list[str] = []
    atual = ""

    for linha in texto.split("\n"):
        while len(linha) > tamanho:
            if atual:
                partes.append(atual)
                atual = ""
            partes.append(linha[:tamanho])
            linha = linha[tamanho:]

        if len(atual) + len(linha) + 1 > tamanho:
            partes.append(atual)
            atual = linha
        else:
            atual = f"{atual}\n{linha}" if atual else linha

    if atual.strip():
        partes.append(atual)

    return partes


def formatar_mensagem(mensagem: discord.Message) -> str:
    return f"{mensagem.author.display_name}: {mensagem.content}\n"


def codigo_do_erro(erro: Exception) -> Optional[int]:
    codigo = getattr(erro, "code", None) or getattr(
        erro, "status_code", None
    )
    return codigo if isinstance(codigo, int) else None


async def registrar_log(bot: commands.Bot, embed: discord.Embed) -> None:
    for chat_id in CHAT_LOGS_COMPOSTO:
        try:
            canal = bot.get_channel(chat_id) or await bot.fetch_channel(
                chat_id
            )
            await canal.send(embed=embed)
        except Exception as erro:
            print(f"[resumir_conversa] falha ao enviar log a {chat_id}: {erro}")


def criar_log(
    titulo: str,
    usuario: discord.abc.User,
    campos: dict[str, str],
    cor: discord.Color = discord.Color.blurple(),
) -> discord.Embed:
    embed = discord.Embed(title=titulo, color=cor)
    embed.add_field(
        name="Usuário",
        value=f"{usuario.mention} (`{usuario.id}`)",
        inline=False,
    )
    for nome, valor in campos.items():
        embed.add_field(name=nome, value=valor[:1024] or "—", inline=False)
    embed.timestamp = discord.utils.utcnow()
    return embed


# ------------------------------------------------------------------------ IA
async def gerar_com_gemini(prompt: str) -> str:
    ultimo_erro: Optional[Exception] = None

    for _ in range(max(quantidade_apis(), 1)):
        api_key = proxima_api()

        try:
            client = genai.Client(api_key=api_key)
            response = await client.aio.models.generate_content(
                model=GEMINI_MODELO,
                contents=prompt,
            )

            if not response.text:
                raise ValueError("O Gemini não retornou texto.")

            return response.text
        except Exception as erro:
            ultimo_erro = erro

            if codigo_do_erro(erro) in CODIGOS_TENTAR_OUTRA_API:
                marcar_api_como_indisponivel(api_key)
                continue

            break

    raise ultimo_erro or RuntimeError("Gemini indisponível.")


async def gerar_resposta(
    instrucao: str,
    conversa: str,
) -> tuple[str, str]:
    """Devolve (texto, nome_da_ia_usada). Gemini primeiro, Groq se falhar."""
    prompt = f"{instrucao.strip()}{AVISO_TAMANHO}\n\nConversa:\n\n{conversa}"

    try:
        return await gerar_com_gemini(prompt), f"Gemini ({GEMINI_MODELO})"
    except Exception as erro_gemini:
        print(f"[resumir_conversa] Gemini falhou: {erro_gemini}")

    conversa_groq = conversa[-LIMITE_CONVERSA_GROQ:]
    prompt_groq = (
        f"{instrucao.strip()}{AVISO_TAMANHO}\n\nConversa:\n\n{conversa_groq}"
    )
    texto = await groq_gerar_texto(prompt_groq)
    return texto, "Groq"


# ------------------------------------------------------------------- botões
class ViewResumo(discord.ui.View):
    def __init__(
        self,
        bot: commands.Bot,
        solicitante: discord.abc.User,
        canal: discord.abc.Messageable,
        titulo: str,
        partes: list[str],
    ) -> None:
        super().__init__(timeout=900)
        self.bot = bot
        self.solicitante = solicitante
        self.canal = canal
        self.titulo = titulo
        self.partes = partes
        self.mensagem: Optional[discord.WebhookMessage] = None

    def montar_embeds(self, footer: str) -> list[discord.Embed]:
        embeds = []
        for i, parte in enumerate(self.partes, start=1):
            embed = discord.Embed(
                title=self.titulo if i == 1 else None,
                description=parte,
                color=discord.Color.blurple(),
            )
            embed.set_footer(
                text=footer,
                icon_url=self.solicitante.display_avatar.url,
            )
            embeds.append(embed)
        return embeds

    def desativar(self) -> None:
        for item in self.children:
            item.disabled = True

    async def interaction_check(
        self, interaction: discord.Interaction
    ) -> bool:
        if interaction.user.id != self.solicitante.id:
            await interaction.response.send_message(
                "Só quem usou o comando pode usar estes botões.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        self.desativar()
        if self.mensagem:
            try:
                await self.mensagem.edit(view=self)
            except discord.HTTPException:
                pass

    @discord.ui.button(label="Enviar", style=discord.ButtonStyle.success)
    async def enviar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        self.desativar()
        await interaction.response.edit_message(view=self)

        footer = f"Solicitado por {self.solicitante.display_name}"

        try:
            for embed in self.montar_embeds(footer):
                await self.canal.send(embed=embed)
        except discord.HTTPException as erro:
            await interaction.followup.send(
                f"Não consegui enviar no canal: {erro}",
                ephemeral=True,
            )
            await registrar_log(
                self.bot,
                criar_log(
                    "❌ Resumo: falha ao enviar no canal",
                    self.solicitante,
                    {"Erro": str(erro)},
                    discord.Color.red(),
                ),
            )
            return

        await interaction.followup.send(
            "Resumo enviado no canal.", ephemeral=True
        )
        await registrar_log(
            self.bot,
            criar_log(
                "📤 Resumo enviado no canal",
                self.solicitante,
                {"Canal": f"<#{self.canal.id}>"},
                discord.Color.green(),
            ),
        )

    @discord.ui.button(label="Não enviar", style=discord.ButtonStyle.danger)
    async def nao_enviar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        self.desativar()
        await interaction.response.edit_message(view=self)

        if await id_esta_na_thread_dm_fechada(
            self.bot, self.solicitante.id
        ):
            await interaction.followup.send(
                "Seu privado está na lista de DM fechada, então não enviei "
                "nada por lá. O resumo não foi enviado em nenhum lugar.",
                ephemeral=True,
            )
            await registrar_log(
                self.bot,
                criar_log(
                    "🚫 Resumo não enviado (DM fechada)",
                    self.solicitante,
                    {"Motivo": "id na thread CHAT_THREAD_DM_FECHADA"},
                    discord.Color.orange(),
                ),
            )
            return

        try:
            for embed in self.montar_embeds(
                f"Solicitado por {self.solicitante.display_name}"
            ):
                await self.solicitante.send(embed=embed)
        except discord.HTTPException as erro:
            await interaction.followup.send(
                f"Não consegui enviar no seu privado: {erro}",
                ephemeral=True,
            )
            await registrar_log(
                self.bot,
                criar_log(
                    "❌ Resumo: falha ao enviar na DM",
                    self.solicitante,
                    {"Erro": str(erro)},
                    discord.Color.red(),
                ),
            )
            return

        await interaction.followup.send(
            "Enviei o resumo no seu privado.", ephemeral=True
        )
        await registrar_log(
            self.bot,
            criar_log(
                "📩 Resumo enviado na DM",
                self.solicitante,
                {},
                discord.Color.green(),
            ),
        )


async def id_esta_na_thread_dm_fechada(
    bot: commands.Bot, usuario_id: int
) -> bool:
    try:
        thread = bot.get_channel(
            CHAT_THREAD_DM_FECHADA
        ) or await bot.fetch_channel(CHAT_THREAD_DM_FECHADA)

        async for mensagem in thread.history(limit=None):
            if str(usuario_id) in mensagem.content:
                return True
    except Exception as erro:
        print(f"[resumir_conversa] falha ao ler DM_FECHADA: {erro}")

    return False


# ------------------------------------------------------------------ comando
def registrar_comando_resumir_conversa(
    bot: commands.Bot,
) -> None:
    @bot.tree.command(
        name="resumir_conversa",
        description="Resume uma conversa (thread ou trecho de chat) usando IA.",
    )
    @app_commands.describe(
        origem="Thread: lê o tópico inteiro. Chat: lê entre duas mensagens.",
        tipo="O que a IA deve fazer com a conversa.",
        mensagem_inicial="(Chat) id ou link da primeira mensagem.",
        mensagem_final="(Chat) id ou link da última mensagem.",
        prompt="(Outro) escreva o que a IA deve fazer.",
    )
    @app_commands.choices(
        origem=[
            app_commands.Choice(name="Chat", value="chat"),
            app_commands.Choice(name="Thread", value="thread"),
        ],
        tipo=[
            app_commands.Choice(name="Debate", value="debate"),
            app_commands.Choice(name="Dúvida", value="duvida"),
            app_commands.Choice(name="Incoerência", value="incoerencia"),
            app_commands.Choice(name="Outro", value="outro"),
        ],
    )
    async def resumir_conversa(
        interaction: discord.Interaction,
        origem: app_commands.Choice[str],
        tipo: app_commands.Choice[str],
        mensagem_inicial: Optional[str] = None,
        mensagem_final: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> None:
        # ---------- permissão
        if not any(
            role.id == valentes
            for role in getattr(interaction.user, "roles", [])
        ):
            await interaction.response.send_message(
                "Você não tem permissão para usar este comando.",
                ephemeral=True,
            )
            return

        # ---------- validações
        if origem.value == "thread":
            if not isinstance(interaction.channel, discord.Thread):
                await interaction.response.send_message(
                    "A opção **thread** só pode ser usada dentro de um "
                    "tópico.",
                    ephemeral=True,
                )
                return
        else:
            if not mensagem_inicial or not mensagem_final:
                await interaction.response.send_message(
                    "Na opção **chat** você precisa informar a mensagem "
                    "inicial e a mensagem final (id ou link).",
                    ephemeral=True,
                )
                return

        if tipo.value == "outro" and not (prompt and prompt.strip()):
            await interaction.response.send_message(
                "Na opção **Outro** você precisa escrever o prompt.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        canal = interaction.channel
        mensagens: list[discord.Message] = []

        # ---------- coleta das mensagens
        try:
            if origem.value == "thread":
                async for m in canal.history(
                    limit=MAX_MENSAGENS, oldest_first=True
                ):
                    mensagens.append(m)
            else:
                canal_ini, id_ini = extrair_referencia(mensagem_inicial)
                canal_fim, id_fim = extrair_referencia(mensagem_final)

                if id_ini is None or id_fim is None:
                    await interaction.followup.send(
                        "Não entendi o id ou o link de uma das mensagens."
                    )
                    return

                for canal_ref in (canal_ini, canal_fim):
                    if canal_ref is not None and canal_ref != canal.id:
                        await interaction.followup.send(
                            "As mensagens precisam estar no mesmo canal "
                            "em que você usou o comando."
                        )
                        return

                if id_ini > id_fim:
                    id_ini, id_fim = id_fim, id_ini

                msg_ini = await canal.fetch_message(id_ini)
                msg_fim = await canal.fetch_message(id_fim)

                mensagens.append(msg_ini)
                async for m in canal.history(
                    limit=MAX_MENSAGENS,
                    after=msg_ini,
                    before=msg_fim,
                    oldest_first=True,
                ):
                    mensagens.append(m)
                if msg_fim.id != msg_ini.id:
                    mensagens.append(msg_fim)
        except discord.NotFound:
            await interaction.followup.send(
                "Não encontrei uma das mensagens neste canal."
            )
            return
        except discord.HTTPException as erro:
            await interaction.followup.send(
                f"Erro ao ler as mensagens:\n```{erro}```"
            )
            return

        conversa = "".join(
            formatar_mensagem(m) for m in mensagens if m.content.strip()
        )

        if not conversa.strip():
            await interaction.followup.send(
                "Não encontrei mensagens para resumir."
            )
            return

        instrucao = (
            prompt.strip() if tipo.value == "outro" else PROMPTS[tipo.value]
        )

        # ---------- IA
        try:
            texto, ia_usada = await gerar_resposta(instrucao, conversa)
        except Exception as erro:
            await interaction.followup.send(
                f"Erro ao gerar a resposta:\n```{erro}```"
            )
            await registrar_log(
                bot,
                criar_log(
                    "❌ Resumo: erro nas duas IAs",
                    interaction.user,
                    {
                        "Canal": f"<#{canal.id}>",
                        "Origem": origem.name,
                        "Tipo": tipo.name,
                        "Erro": str(erro),
                    },
                    discord.Color.red(),
                ),
            )
            return

        if not texto or not texto.strip():
            await interaction.followup.send(
                "A IA não retornou nenhuma resposta."
            )
            return

        # ---------- resposta efêmera + botões
        partes = dividir_texto(texto.strip())
        view = ViewResumo(
            bot=bot,
            solicitante=interaction.user,
            canal=canal,
            titulo=TITULOS[tipo.value],
            partes=partes,
        )

        embeds = view.montar_embeds("Prévia: só você está vendo isto")

        for embed in embeds[:-1]:
            await interaction.followup.send(embed=embed, ephemeral=True)

        view.mensagem = await interaction.followup.send(
            embed=embeds[-1],
            view=view,
            ephemeral=True,
            wait=True,
        )

        await registrar_log(
            bot,
            criar_log(
                "📝 /resumir_conversa usado",
                interaction.user,
                {
                    "Canal": f"<#{canal.id}>",
                    "Origem": origem.name,
                    "Tipo": tipo.name,
                    "Mensagens lidas": str(len(mensagens)),
                    "IA usada": ia_usada,
                    "Prompt personalizado": (
                        prompt if tipo.value == "outro" and prompt else "—"
                    ),
                },
            ),
        )