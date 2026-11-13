import json
import re

import discord
from discord import app_commands
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from config.IDs import CARGO_MODERADOR, CARGO_FOCUS_ADM, CARGO_ADM, CHAT_THREAD_DM_FECHADA, CHAT_REGRAS_TICKET_DE_ENTRADA, CHAT_LOGS_COMPOSTO
from gemini_manager import proxima_api, marcar_api_como_indisponivel, quantidade_apis
from groq_manager import analisar_imagem as groq_analisar_imagem

# ======================= CONFIG =======================
CARGOS_PERMITIDOS = {CARGO_MODERADOR, CARGO_FOCUS_ADM, CARGO_ADM}

GEMINI_MODELO = "gemini-3.6-flash"

# Erros em que a API está sobrecarregada: marca cooldown e tenta outra API do Gemini.
CODIGOS_TENTAR_OUTRA_API = (429, 409)

# O que a IA deve considerar como foto de perfil inadequada (vale para Gemini e Groq).
# Ajuste conforme as regras do seu servidor.
REGRAS_FOTO = (
    "Fotos inadequadas incluem: nudez ou conteúdo sexual/sugestivo, violência ou gore, "
    "símbolos de ódio, conteúdo ofensivo ou desrespeitoso, imagens que promovam atividades "
    "ilegais ou conteúdo que desrespeite a temática do servidor."
)
# ======================================================

TIPOS = {
    "trocar": "Pedir para trocar",
    "analisar": "Analisar",
    "nada": "Nada",
}

# Um client do Gemini por chave, para não recriar a cada uso.
_clients: dict[str, genai.Client] = {}


def _client(api_key: str) -> genai.Client:
    if api_key not in _clients:
        _clients[api_key] = genai.Client(api_key=api_key)
    return _clients[api_key]


# ======================= ERROS =======================
class Gemini503(Exception):
    """Erro 503: o Gemini está fora do ar e não funcionará em nenhuma API."""


class GeminiSemApis(Exception):
    """Todas as APIs do Gemini estão em cooldown/sobrecarregadas (ou nenhuma configurada)."""


class FalhaNasDuasIAs(Exception):
    """Gemini e Groq falharam."""

    def __init__(self, motivo_gemini: str, motivo_groq: str):
        super().__init__(f"Gemini: {motivo_gemini} | Groq: {motivo_groq}")
        self.motivo_gemini = motivo_gemini
        self.motivo_groq = motivo_groq


# ======================= HELPERS =======================
def tem_permissao(member) -> bool:
    return any(r.id in CARGOS_PERMITIDOS for r in getattr(member, "roles", []))


def padrao_id(uid: int) -> re.Pattern:
    return re.compile(rf"(?<!\d){uid}(?!\d)")


async def obter_canal(bot, canal_id: int):
    return bot.get_channel(canal_id) or await bot.fetch_channel(canal_id)


async def log(bot, titulo: str, descricao: str):
    """Envia a mesma log para todos os chats de CHAT_LOGS_COMPOSTO."""
    embed = discord.Embed(
        title=titulo,
        description=descricao[:4000],
        color=discord.Color.blurple(),
        timestamp=discord.utils.utcnow(),
    )
    for canal_id in CHAT_LOGS_COMPOSTO:
        try:
            canal = await obter_canal(bot, canal_id)
            await canal.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
        except discord.HTTPException:
            pass


async def resolver_pessoa(bot, guild: discord.Guild, texto: str):
    """Aceita menção, id ou texto contendo o id. Retorna Member, User ou None."""
    achado = re.search(r"\d{15,20}", texto)
    if not achado:
        return None
    uid = int(achado.group())

    membro = guild.get_member(uid)
    if membro:
        return membro
    try:
        return await guild.fetch_member(uid)
    except discord.HTTPException:
        pass
    try:
        return await bot.fetch_user(uid)
    except discord.HTTPException:
        return None


async def id_na_dm_fechada(bot, uid: int) -> bool:
    thread = await obter_canal(bot, CHAT_THREAD_DM_FECHADA)
    padrao = padrao_id(uid)
    async for msg in thread.history(limit=None):
        textos = [msg.content or ""]
        for e in msg.embeds:
            textos += [e.title or "", e.description or ""]
        if any(padrao.search(t) for t in textos):
            return True
    return False


async def achar_ticket(bot, uid: int):
    """Procura o tópico com o id no título; se houver vários, o mais recente."""
    canal = await obter_canal(bot, CHAT_REGRAS_TICKET_DE_ENTRADA)
    padrao = padrao_id(uid)

    threads = {t.id: t for t in canal.threads}  # ativos

    try:
        async for t in canal.archived_threads(limit=None):
            threads[t.id] = t
    except discord.HTTPException:
        pass

    if isinstance(canal, discord.TextChannel):
        try:
            async for t in canal.archived_threads(private=True, limit=None):
                threads[t.id] = t
        except discord.HTTPException:
            pass

    candidatos = [t for t in threads.values() if padrao.search(t.name)]
    # id de thread é snowflake: maior id = criado mais recentemente
    return max(candidatos, key=lambda t: t.id) if candidatos else None


async def baixar_avatar(alvo) -> bytes:
    asset = alvo.display_avatar.replace(size=512, format="png")
    return await asset.read()


def descrever_erro(e: Exception) -> str:
    return f"{type(e).__name__}: {e}"[:500]


# ======================= PROMPT (mesmos critérios para as duas IAs) =======================
def montar_prompt(tipo: str, observacao: str | None, json_saida: bool = False) -> str:
    obs = f"\n\nObservação da moderação (leve em conta): {observacao}" if observacao else ""

    if tipo == "trocar":
        instrucao = (
            "Analise a foto de perfil enviada e escreva uma mensagem educada, curta e "
            "respeitosa, em português do Brasil, pedindo para a pessoa trocar a foto, "
            "explicando brevemente o motivo. Fale diretamente com a pessoa (segunda pessoa) "
            f"em nome da equipe de moderação.\n\n{REGRAS_FOTO}"
        )
    elif tipo == "analisar":
        instrucao = (
            "Analise a foto de perfil enviada e diga, em português do Brasil, se ela é "
            "inadequada ou adequada, justificando brevemente. NÃO peça para a pessoa trocar "
            "a foto e não escreva como se estivesse falando com ela: é uma análise interna "
            f"para a equipe de moderação.\n\n{REGRAS_FOTO}"
        )
    else:  # nada
        instrucao = (
            "Não analise nem comente a foto e não peça para trocá-la. Escreva apenas uma "
            "mensagem curta em português do Brasil baseada exclusivamente na observação "
            "da moderação abaixo."
        )

    if json_saida:
        # O groq_manager força response_format=json_object, então o prompt precisa pedir JSON.
        formato = (
            'Responda SOMENTE com um objeto JSON válido no formato {"texto": "<sua resposta>"}, '
            "com no máximo 1500 caracteres no campo texto e sem títulos."
        )
    else:
        formato = "Responda com no máximo 1500 caracteres, sem títulos."

    return f"{instrucao}{obs}\n\n{formato}"


# ======================= GEMINI =======================
async def gerar_com_gemini(imagem: bytes, tipo: str, observacao: str | None) -> tuple[str, int]:
    """
    - 429/409 (sobrecarregada): coloca a API em cooldown e tenta a próxima.
    - 503: levanta Gemini503 (não adianta tentar outras APIs).
    - Sem APIs disponíveis: levanta GeminiSemApis.
    Retorna (texto, quantidade_de_apis_tentadas).
    """
    contents = [
        types.Part.from_bytes(data=imagem, mime_type="image/png"),
        montar_prompt(tipo, observacao),
    ]

    tentativas = 0
    for _ in range(max(quantidade_apis(), 1)):
        try:
            api_key = proxima_api()
        except RuntimeError as e:
            raise GeminiSemApis(str(e)) from e

        tentativas += 1
        try:
            resp = await _client(api_key).aio.models.generate_content(
                model=GEMINI_MODELO, contents=contents
            )
        except genai_errors.APIError as e:
            if e.code in CODIGOS_TENTAR_OUTRA_API:
                marcar_api_como_indisponivel(api_key)
                continue
            if e.code == 503:
                raise Gemini503(str(e)) from e
            raise

        texto = (resp.text or "").strip()
        if not texto:
            raise ValueError("O Gemini não retornou texto (resposta vazia ou bloqueada).")
        return texto, tentativas

    raise GeminiSemApis("Todas as APIs do Gemini estão sobrecarregadas no momento.")


# ======================= GROQ =======================
def extrair_texto_json(bruto: str) -> str:
    bruto = re.sub(r"<think>.*?</think>", "", bruto or "", flags=re.DOTALL).strip()
    try:
        dados = json.loads(bruto)
    except json.JSONDecodeError:
        achado = re.search(r"\{.*\}", bruto, flags=re.DOTALL)
        if not achado:
            raise ValueError("A Groq não retornou um JSON válido.")
        dados = json.loads(achado.group())

    texto = str(dados.get("texto", "")).strip() if isinstance(dados, dict) else ""
    if not texto:
        raise ValueError("A Groq retornou o JSON sem o campo 'texto'.")
    return texto


async def gerar_com_groq(imagem: bytes, tipo: str, observacao: str | None) -> str:
    bruto = await groq_analisar_imagem(
        image_bytes=imagem,
        prompt=montar_prompt(tipo, observacao, json_saida=True),
        mime_type="image/png",
    )
    return extrair_texto_json(bruto)


# ======================= ORQUESTRAÇÃO (Gemini → Groq) =======================
async def gerar_texto(imagem: bytes, tipo: str, observacao: str | None) -> dict:
    """
    Tenta o Gemini; se der 503 ou qualquer outra exceção, tenta a Groq.
    Retorna {"texto", "provedor", "tentativas_gemini", "motivo_gemini"}.
    Levanta FalhaNasDuasIAs se as duas falharem.
    """
    try:
        texto, tentativas = await gerar_com_gemini(imagem, tipo, observacao)
        return {"texto": texto, "provedor": "Gemini",
                "tentativas_gemini": tentativas, "motivo_gemini": None}

    except Gemini503 as e:
        motivo_gemini = f"503 (serviço indisponível em todas as APIs): {e}"
    except GeminiSemApis as e:
        motivo_gemini = f"sem APIs disponíveis: {e}"
    except Exception as e:  # qualquer exceção não tratada
        motivo_gemini = descrever_erro(e)

    try:
        texto = await gerar_com_groq(imagem, tipo, observacao)
    except Exception as e:
        raise FalhaNasDuasIAs(motivo_gemini, descrever_erro(e)) from e

    return {"texto": texto, "provedor": "Groq (fallback)",
            "tentativas_gemini": None, "motivo_gemini": motivo_gemini}


# ======================= VIEW =======================
class PainelFotoView(discord.ui.View):
    def __init__(self, bot, alvo, texto: str):
        super().__init__(timeout=None)
        self.bot = bot
        self.alvo = alvo
        self.texto = texto

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if tem_permissao(interaction.user):
            return True
        await interaction.response.send_message(
            "Você não tem permissão para usar esses botões.", ephemeral=True
        )
        return False

    @discord.ui.button(label="Enviar para o privado", style=discord.ButtonStyle.primary)
    async def enviar_privado(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        quem = f"{interaction.user} ({interaction.user.id})"
        alvo = f"{self.alvo} ({self.alvo.id})"

        try:
            fechada = await id_na_dm_fechada(self.bot, self.alvo.id)
        except discord.HTTPException as e:
            await interaction.followup.send(
                "Não consegui ler a thread de DM fechada, então não enviei.", ephemeral=True
            )
            await log(self.bot, "Botão: enviar no privado (erro)",
                      f"Por: {quem}\nPessoa: {alvo}\nErro ao ler a thread de DM fechada: `{e}`")
            return

        if fechada:
            await interaction.followup.send(
                "Não enviei: o id da pessoa está na thread de DM fechada.", ephemeral=True
            )
            await log(self.bot, "Botão: enviar no privado (bloqueado)",
                      f"Por: {quem}\nPessoa: {alvo}\nMotivo: id está na thread de DM fechada.")
            return

        try:
            await self.alvo.send(self.texto[:2000])
        except (discord.Forbidden, discord.HTTPException):
            try:
                thread = await obter_canal(self.bot, CHAT_THREAD_DM_FECHADA)
                await thread.send(str(self.alvo.id))
            except discord.HTTPException:
                pass
            await interaction.followup.send(
                "Não consegui enviar no privado (DM fechada). Registrei o id na thread.",
                ephemeral=True,
            )
            await log(self.bot, "Botão: enviar no privado (falhou)",
                      f"Por: {quem}\nPessoa: {alvo}\nA DM falhou; id enviado na thread de DM fechada.")
            return

        await interaction.followup.send("Mensagem enviada no privado.", ephemeral=True)
        await log(self.bot, "Botão: enviar no privado (sucesso)",
                  f"Por: {quem}\nPessoa: {alvo}\n\nMensagem:\n{self.texto}")

    @discord.ui.button(label="Enviar para o ticket de início", style=discord.ButtonStyle.secondary)
    async def enviar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        quem = f"{interaction.user} ({interaction.user.id})"
        alvo = f"{self.alvo} ({self.alvo.id})"

        try:
            thread = await achar_ticket(self.bot, self.alvo.id)
        except discord.HTTPException as e:
            await interaction.followup.send("Erro ao procurar o ticket.", ephemeral=True)
            await log(self.bot, "Botão: enviar no ticket (erro)",
                      f"Por: {quem}\nPessoa: {alvo}\nErro: `{e}`")
            return

        if thread is None:
            await interaction.followup.send(
                "Não encontrei nenhum ticket de entrada com o id dessa pessoa.", ephemeral=True
            )
            await log(self.bot, "Botão: enviar no ticket (não encontrado)",
                      f"Por: {quem}\nPessoa: {alvo}\nNenhum tópico com o id no título.")
            return

        try:
            await thread.send(
                f"{self.alvo.mention} {self.texto}"[:2000],
                allowed_mentions=discord.AllowedMentions(users=[self.alvo]),
            )
        except discord.HTTPException as e:
            await interaction.followup.send(
                f"Achei o ticket ({thread.mention}), mas não consegui enviar.", ephemeral=True
            )
            await log(self.bot, "Botão: enviar no ticket (falhou)",
                      f"Por: {quem}\nPessoa: {alvo}\nTicket: {thread.mention}\nErro: `{e}`")
            return

        await interaction.followup.send(f"Mensagem enviada em {thread.mention}.", ephemeral=True)
        await log(self.bot, "Botão: enviar no ticket (sucesso)",
                  f"Por: {quem}\nPessoa: {alvo}\nTicket: {thread.mention}\n\nMensagem:\n{self.texto}")

    @discord.ui.button(label="Manualmente", style=discord.ButtonStyle.danger)
    async def manualmente(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        await log(self.bot, "Botão: manualmente",
                  f"Por: {interaction.user} ({interaction.user.id})\n"
                  f"Pessoa: {self.alvo} ({self.alvo.id})\nBotões desativados.")


# ======================= COMANDO =======================
def setup(bot):
    @bot.tree.command(
        name="analisar_foto_de_perfil",
        description="Analisa a foto de perfil de uma pessoa com IA.",
    )
    @app_commands.guild_only()
    @app_commands.describe(
        pessoa="A pessoa (menção) ou o id dela",
        tipo="O que fazer com a foto da pessoa",
        observacao="Observação opcional para a IA considerar",
    )
    @app_commands.choices(
        tipo=[app_commands.Choice(name=nome, value=valor) for valor, nome in TIPOS.items()]
    )
    async def analisar_foto_de_perfil(
        interaction: discord.Interaction,
        pessoa: str,
        tipo: app_commands.Choice[str],
        observacao: str | None = None,
    ):
        if not tem_permissao(interaction.user):
            await interaction.response.send_message(
                "Você não tem permissão para usar este comando.", ephemeral=True
            )
            return

        if tipo.value == "nada" and not observacao:
            await interaction.response.send_message(
                "Com o tipo **Nada** você precisa preencher a observação.", ephemeral=True
            )
            return

        await interaction.response.defer()

        alvo = await resolver_pessoa(bot, interaction.guild, pessoa)
        if alvo is None:
            await interaction.followup.send("Não encontrei essa pessoa.", ephemeral=True)
            await log(bot, "/analisar_foto_de_perfil (pessoa não encontrada)",
                      f"Por: {interaction.user} ({interaction.user.id})\nEntrada: `{pessoa}`")
            return

        quem = f"{interaction.user} ({interaction.user.id})"
        resumo = (
            f"Por: {quem}\nPessoa: {alvo} ({alvo.id})\nTipo: {tipo.name}\n"
            f"Observação: {observacao or '—'}"
        )

        try:
            imagem = await baixar_avatar(alvo)
        except Exception as e:
            await interaction.followup.send(
                f"Não consegui baixar a foto de perfil: `{e}`", ephemeral=True
            )
            await log(bot, "/analisar_foto_de_perfil (erro ao baixar foto)",
                      f"{resumo}\nErro: `{descrever_erro(e)}`")
            return

        try:
            resultado = await gerar_texto(imagem, tipo.value, observacao)
        except FalhaNasDuasIAs as e:
            await interaction.followup.send(
                "⚠️ Não consegui analisar a foto: o **Gemini** e a **Groq** falharam. "
                "Tente novamente mais tarde.",
                ephemeral=True,
            )
            await log(bot, "/analisar_foto_de_perfil (Gemini e Groq falharam)",
                      f"{resumo}\n\nGemini: `{e.motivo_gemini}`\nGroq: `{e.motivo_groq}`")
            return

        texto = resultado["texto"]
        provedor = resultado["provedor"]

        embed = discord.Embed(
            title="Análise da foto de perfil",
            description=texto[:4000],
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url=alvo.display_avatar.url)
        embed.add_field(name="Pessoa", value=f"{alvo.mention} (`{alvo.id}`)", inline=True)
        embed.add_field(name="Tipo", value=tipo.name, inline=True)
        if observacao:
            embed.add_field(name="Observação", value=observacao[:1000], inline=False)
        embed.set_footer(text=f"Analisado por: {provedor}")

        await interaction.followup.send(
            embed=embed,
            view=PainelFotoView(bot, alvo, texto),
            allowed_mentions=discord.AllowedMentions.none(),
        )

        if resultado["motivo_gemini"]:
            detalhe = f"Gemini falhou ({resultado['motivo_gemini']}); usado: {provedor}."
        else:
            detalhe = f"Provedor: {provedor} (APIs do Gemini tentadas: {resultado['tentativas_gemini']})."
        await log(bot, "/analisar_foto_de_perfil (usado)",
                  f"{resumo}\n{detalhe}\n\nTexto gerado:\n{texto}")