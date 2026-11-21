"""
acesso_ao_servidor.py

Módulo (sem cogs) para ser importado no main e chamado por outros comandos/eventos.

Uso básico (em outro código):

    from acesso_ao_servidor import acesso_ao_servidor, registrar

    # no main, uma vez (liga o aviso de mensagens nas threads de acolhimento):
    registrar(bot)

    # quando a pessoa acessar o servidor:
    await acesso_ao_servidor(bot, after)
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone

import discord

from config.IDs import (
    CARGO_HOMEM,
    CARGO_MULHER,
    CHAT_AGENDAMENTOS,
    CHAT_BOAS_VINDAS_NOVO,
    CHAT_CONVERSAS,
    CHAT_CONVITES,
    CHAT_LOGS_COMPOSTO,  # lista de ids de chats
    CHAT_PAINEL_DE_CONFIGURACAO,
    CHAT_REGRAS_TICKET_DE_ENTRADA,
    CARGO_PEDIR_ACESSO,
    CARGO_A_VERIFICAR,
    CARGO_VER_CHAT_EXPLICACAO,
    CARGO_CC_CRIAR_CONVITE,
    CARGO_MEMBROS,
    CARGO_DIVISORIA_CARACTERISTICAS,
    CARGO_DIVISORIA_CONQUISTAS,
    CARGO_DIVISORIA_PINGS,
    CARGO_TEMPO,
    CARGO_NOVATOS,
    SAPPHIRE,
    CARGO_ACOLHIMENTO
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CONFIGURAÇÕES (preencher)
# ---------------------------------------------------------------------------

# Cargos que serão aplicados à pessoa quando ela acessar o servidor.
LISTA_CARGOS_APLICAR: list[int] = [
    CARGO_CC_CRIAR_CONVITE,
    CARGO_MEMBROS,
    CARGO_DIVISORIA_CARACTERISTICAS,    
    CARGO_DIVISORIA_CONQUISTAS,
    CARGO_DIVISORIA_PINGS,
    CARGO_TEMPO,
    CARGO_NOVATOS
]
# Cargos que serão REMOVIDOS da pessoa quando ela acessar o servidor.
LISTA_CARGOS_REMOVER: list[int] = [
    CARGO_PEDIR_ACESSO,
    CARGO_A_VERIFICAR,
    CARGO_VER_CHAT_EXPLICACAO
]

# Id do bot SAPPHIRE (usado para achar a mensagem de entrada como alternativa).
# Se deixar 0, o bot procura por autor bot com "sapphire" no nome.
#ID_BOT_SAPPHIRE = 0 - Edit: importei do config.IDs

FRASE_BOTAO_ACESSO = "Clique no botão abaixo para acessar o servidor."

VERSICULO = (
    '"Portanto, acolham uns aos outros, como também Cristo acolheu vocês '
    'para a glória de Deus." (Romanos 15.7)'
)

MINUTOS_PING_PADRAO = 30
LIMITE_MENSAGENS_PAINEL = 500       # quantas mensagens do painel de configuração ler
LIMITE_MENSAGENS_TICKET = 200       # quantas mensagens de cada thread de ticket olhar
LIMITE_THREADS_ARQUIVADAS = 500     # quantas threads arquivadas olhar por canal
MENSAGENS_PARA_ACHAR_ACESSO = 30    # últimas mensagens de CHAT_CONVERSAS a olhar

try:
    from zoneinfo import ZoneInfo

    FUSO = ZoneInfo("America/Recife")
except Exception:  # sem tzdata instalado
    FUSO = timezone(timedelta(hours=-3))

SEM_MENCOES = discord.AllowedMentions.none()

# Evita rodar duas vezes ao mesmo tempo para a mesma pessoa.
_em_processamento: set[int] = set()


# ---------------------------------------------------------------------------
# EMBEDS DE BOAS-VINDAS (você vai modificar cada uma depois)
# ---------------------------------------------------------------------------

def _embed_boas_vindas_base(usuario: discord.Member) -> discord.Embed:
    embed = discord.Embed(
        title="Boas-vindas! É uma alegria ter você conosco.",
        description=(
            "Nosso objetivo é que este servidor seja um espaço de "
            "**comunhão** e **crescimento** na sua caminhada com Cristo. "
            "Embora nossa base teológica seja **protestante**, nossas "
            "portas estão abertas para todos que buscam aprender mais "
            "sobre Deus. Você pode se apresentar em "
            "<#1363009444111188129>."
        ),
        color=discord.Color.blue(),
    )
    embed.set_thumbnail(url=usuario.display_avatar.url)
    embed.set_image(url="https://i.imgur.com/Xwjxew6.jpg")
    embed.set_footer(text="Bíblia em Foco")
    return embed


def embed_boas_vindas_homem(usuario: discord.Member) -> discord.Embed:
    embed_boas_vindas_homem = discord.Embed(
        title="Boas-vindas! É uma alegria ter você conosco.",
        description=(
            """ Nosso objetivo é que este servidor seja um espaço de **comunhão** e **crescimento** na sua caminhada com Cristo. Embora nossa base teológica seja **protestante**, nossas portas estão abertas para todos que buscam aprender mais sobre Deus."""
        ),
        color=discord.Color.blue(),
    )
    embed_boas_vindas_homem.set_thumbnail(url=usuario.display_avatar.url)
    embed_boas_vindas_homem.set_image(url="https://i.imgur.com/Xwjxew6.jpg")
    embed_boas_vindas_homem.set_footer(text="Bíblia em Foco")
    return embed_boas_vindas_homem


def embed_boas_vindas_mulher(usuario: discord.Member) -> discord.Embed:
    embed_boas_vindas_mulher = discord.Embed(
        title="Boas-vindas! É uma alegria ter você conosco.",
        description=(
            """ Nosso objetivo é que este servidor seja um espaço de **comunhão** e **crescimento** na sua caminhada com Cristo. Embora nossa base teológica seja **protestante**, nossas portas estão abertas para todos que buscam aprender mais sobre Deus."""
        ),
        color=discord.Color.blue(),
    )
    embed_boas_vindas_mulher.set_thumbnail(url=usuario.display_avatar.url)
    embed_boas_vindas_mulher.set_image(url="https://i.imgur.com/Xwjxew6.jpg")
    embed_boas_vindas_mulher.set_footer(text="Bíblia em Foco")
    return embed_boas_vindas_mulher


def embed_boas_vindas_excecao(usuario: discord.Member) -> discord.Embed:
    return _embed_boas_vindas_base(usuario)


# ---------------------------------------------------------------------------
# UTILIDADES
# ---------------------------------------------------------------------------

async def obter_canal(bot, canal_id: int):
    canal = bot.get_channel(canal_id)
    if canal is None:
        try:
            canal = await bot.fetch_channel(canal_id)
        except discord.HTTPException:
            canal = None
    return canal


async def enviar_logs(bot, conteudo: str = None, embed: discord.Embed = None):
    """Envia a mesma log para todos os chats de CHAT_LOGS_COMPOSTO."""
    for canal_id in CHAT_LOGS_COMPOSTO:
        try:
            canal = await obter_canal(bot, canal_id)
            if canal is None:
                continue
            await canal.send(
                content=conteudo, embed=embed, allowed_mentions=SEM_MENCOES
            )
        except Exception as e:
            logger.warning("Falha ao enviar log em %s: %s", canal_id, e)


def texto_da_mensagem(msg: discord.Message) -> str:
    partes = [msg.content or ""]
    for e in msg.embeds:
        partes.extend([e.title or "", e.description or ""])
        partes.extend(f"{f.name} {f.value}" for f in e.fields)
    return "\n".join(partes)


def formatar_quando(delta: timedelta) -> str:
    """Data/hora no futuro: dia/mês/ano hora:minuto (fuso de Recife)."""
    return (datetime.now(FUSO) + delta).strftime("%d/%m/%Y %H:%M")


async def buscar_threads_por_id(canal, user_id: int) -> list[discord.Thread]:
    """Threads (ativas e arquivadas) do canal cujo nome contém o id da pessoa."""
    alvo = str(user_id)
    achadas: dict[int, discord.Thread] = {}

    # ativas
    for t in await canal.guild.active_threads():
        if t.parent_id == canal.id and alvo in t.name:
            achadas[t.id] = t

    # arquivadas públicas
    try:
        async for t in canal.archived_threads(limit=LIMITE_THREADS_ARQUIVADAS):
            if alvo in t.name:
                achadas[t.id] = t
    except (discord.Forbidden, discord.HTTPException):
        pass

    # arquivadas privadas (só canais de texto)
    if isinstance(canal, discord.TextChannel):
        try:
            async for t in canal.archived_threads(
                private=True, limit=LIMITE_THREADS_ARQUIVADAS
            ):
                if alvo in t.name:
                    achadas[t.id] = t
        except (discord.Forbidden, discord.HTTPException):
            pass

    return list(achadas.values())


async def ler_configuracoes(bot, chaves: list[str]) -> dict[str, str]:
    """
    Lê CHAT_PAINEL_DE_CONFIGURACAO e devolve {chave: valor} usando sempre a
    ocorrência mais recente de cada chave (formato `chave = valor`).
    """
    canal = await obter_canal(bot, CHAT_PAINEL_DE_CONFIGURACAO)
    resultado: dict[str, str] = {}
    if canal is None:
        return resultado

    async for msg in canal.history(limit=LIMITE_MENSAGENS_PAINEL):  # mais nova primeiro
        texto = texto_da_mensagem(msg)
        for chave in chaves:
            if chave in resultado:
                continue
            achados = re.findall(
                rf"(?<!\w){re.escape(chave)}\s*=\s*([A-Za-z0-9]+)", texto, re.I
            )
            if achados:
                resultado[chave] = achados[-1].lower()
        if len(resultado) == len(chaves):
            break
    return resultado


async def _executar_etapa(bot, nome: str, etapa, *args):
    """Roda uma etapa isolada: se der erro, avisa nos logs e segue o fluxo."""
    try:
        return await etapa(*args)
    except Exception as e:
        logger.exception("Erro na etapa '%s'", nome)
        await enviar_logs(
            bot, f"❌ Erro na etapa **{nome}** de acesso_ao_servidor: `{type(e).__name__}: {e}`"
        )
        return None

# ---------------------------------------------------------------------------
# MENSAGENS DE AGENDAMENTO EXTRAS (você vai preencher depois)
# Retorne o texto da mensagem. Se retornar vazio, nada é enviado.
# ---------------------------------------------------------------------------

def texto_agendamento_extra_1(
    usuario: discord.Member, msg_boas_vindas: discord.Message
) -> str:
    return ""


def texto_agendamento_extra_2(
    usuario: discord.Member, msg_boas_vindas: discord.Message
) -> str:
    return ""

# (será no ponto 6) usar agendamento para remover cargo de novato
async def agendar_tirar_novato(bot, user_id: int) -> str:
    agendar_remover_novatos = (
        "AGENDAR: CARGOS\n"
        "QUANDO: +24h\n"
        "SE_PASSAR: PROSSEGUIR\n"
        "MOTIVO: Remover cargo de novato.\n"
        f"PESSOA: {user_id}\n"
        f"CARGO: {CARGO_NOVATOS}\n"
        "AÇÃO: REMOVER\n"
        "SERVIDOR: 1347727626088878151"
    )

    return agendar_remover_novatos

# ---------------------------------------------------------------------------
# ETAPAS
# ---------------------------------------------------------------------------

async def _aplicar_cargos(bot, after: discord.Member):
    if not LISTA_CARGOS_APLICAR and not LISTA_CARGOS_REMOVER:
        return

    adicionar, remover, faltando = [], [], []

    for cargo_id in LISTA_CARGOS_APLICAR:
        cargo = after.guild.get_role(cargo_id)
        if cargo is None:
            faltando.append(cargo_id)
        elif cargo not in after.roles:
            adicionar.append(cargo)

    for cargo_id in LISTA_CARGOS_REMOVER:
        cargo = after.guild.get_role(cargo_id)
        if cargo is None:
            faltando.append(cargo_id)
        elif cargo in after.roles:
            remover.append(cargo)

    if adicionar:
        await after.add_roles(*adicionar, reason="Acesso ao servidor")
    if remover:
        await after.remove_roles(*remover, reason="Acesso ao servidor")
    if faltando:
        await enviar_logs(
            bot, f"⚠️ Cargos não encontrados em acesso_ao_servidor: `{faltando}`"
        )

async def _avisar_threads(after: discord.Member, threads: list[discord.Thread]):
    for t in threads:
        try:
            await t.send(
                f"{after.mention} acessou o servidor.", allowed_mentions=SEM_MENCOES
            )
        except Exception as e:
            logger.warning("Falha ao avisar na thread %s: %s", t.id, e)


async def _enviar_msg_conversas(bot, after: discord.Member):
    canal = await obter_canal(bot, CHAT_CONVERSAS)
    if canal is None:
        raise RuntimeError("CHAT_CONVERSAS não encontrado")
    return await canal.send(f"<@{after.id}> entrou no servidor.")


async def _apagar_mensagens_botao(threads: list[discord.Thread]):
    for t in threads:
        async for msg in t.history(limit=LIMITE_MENSAGENS_TICKET):
            if msg.author.bot and FRASE_BOTAO_ACESSO in texto_da_mensagem(msg):
                try:
                    await msg.delete()
                except discord.HTTPException as e:
                    logger.warning("Falha ao apagar mensagem %s: %s", msg.id, e)


async def _achar_mensagem_acesso(
    bot, canal: discord.abc.Messageable, after: discord.Member
):
    """
    Procura nas últimas mensagens de CHAT_CONVERSAS a mensagem do bot dizendo que
    a pessoa entrou. Se não achar, procura mensagem da SAPPHIRE marcando o novato.
    """
    texto_esperado = f"<@{after.id}> entrou no servidor."
    mensagens = [m async for m in canal.history(limit=MENSAGENS_PARA_ACHAR_ACESSO)]

    for m in mensagens:
        if m.author.id == bot.user.id and m.content == texto_esperado:
            return m

    for m in mensagens:
        eh_sapphire = (
            (SAPPHIRE and m.author.id == SAPPHIRE)
            or (m.author.bot and "sapphire" in m.author.name.lower())
        )
        if eh_sapphire and (
            after in m.mentions or f"<@{after.id}>" in texto_da_mensagem(m)
        ):
            return m
    return None


async def _criar_thread_acolhimento(
    bot, after: discord.Member, msg_acesso: discord.Message | None, minutos: int
) -> bool:
    canal = await obter_canal(bot, CHAT_CONVERSAS)
    if canal is None:
        raise RuntimeError("CHAT_CONVERSAS não encontrado")

    sufixo = f" • {after.id}"
    nome = after.display_name[: 100 - len(sufixo)] + sufixo

    thread = await canal.create_thread(
        name=nome,
        type=discord.ChannelType.private_thread,
        invitable=False,
        reason=f"Acolhimento de {after} ({after.id})",
    )

    # link para a mensagem de acesso (a que acabamos de enviar, ou procura nas últimas 30)
    msg_link = msg_acesso or await _achar_mensagem_acesso(bot, canal, after)

    descricao = f"{after.mention} acessou o servidor."
    if msg_link:
        descricao += f"\n\n[Ver mensagem de acesso]({msg_link.jump_url})"
    descricao += f"\n\n*{VERSICULO}*"

    embed = discord.Embed(
        title=after.display_name,
        description=descricao,
        color=discord.Color.blue(),
    )
    embed.set_thumbnail(url=after.display_avatar.url)

    await thread.send(
        content=f"<@&{CARGO_ACOLHIMENTO}>",
        #content=f"<@896220143808544800>", # Marcar o Jeftoide (testes apenas)
        embed=embed,
        allowed_mentions=discord.AllowedMentions(roles=True),
    )
    await thread.edit(locked=True)

    # agenda apagar a thread
    canal_agenda = await obter_canal(bot, CHAT_AGENDAMENTOS)
    if canal_agenda is None:
        raise RuntimeError("CHAT_AGENDAMENTOS não encontrado")
    await canal_agenda.send(
        "AGENDAR: DELETAR_THREAD\n"
        f"Quando: {formatar_quando(timedelta(minutes=minutos))}\n"
        f"Motivo: Apagar thread do ping de acolhimento de {after.id}.\n"
        "Se_passar: prosseguir\n"
        " \n"
        f"Link: {thread.jump_url}"
    )
    return True


def _escolher_embed_boas_vindas(after: discord.Member) -> discord.Embed:
    ids = {r.id for r in after.roles} | set(LISTA_CARGOS_APLICAR)
    homem, mulher = CARGO_HOMEM in ids, CARGO_MULHER in ids
    if homem and not mulher:
        return embed_boas_vindas_homem(after)
    if mulher and not homem:
        return embed_boas_vindas_mulher(after)
    return embed_boas_vindas_excecao(after)


async def _enviar_boas_vindas(bot, after: discord.Member):
    canal = await obter_canal(bot, CHAT_BOAS_VINDAS_NOVO)
    if canal is None:
        raise RuntimeError("CHAT_BOAS_VINDAS_NOVO não encontrado")

    msg = await canal.send(
        content=after.mention, embed=_escolher_embed_boas_vindas(after)
    )

    canal_agenda = await obter_canal(bot, CHAT_AGENDAMENTOS)
    if canal_agenda is None:
        raise RuntimeError("CHAT_AGENDAMENTOS não encontrado")

    await canal_agenda.send(
        "AGENDAR: DELETAR_MENSAGEM\n"
        f"link: {msg.jump_url}\n"
        f"quando: {formatar_quando(timedelta(days=1))}"
    )

    # 2 mensagens extras (a preencher)
    for texto in (
        texto_agendamento_extra_1(after, msg),
        texto_agendamento_extra_2(after, msg),
    ):
        if texto:
            await canal_agenda.send(texto)


# ---------------------------------------------------------------------------
# FUNÇÃO PRINCIPAL
# ---------------------------------------------------------------------------

async def acesso_ao_servidor(bot, after: discord.Member):
    """Executa todo o fluxo de acesso ao servidor para o membro `after`."""
    if after.id in _em_processamento:
        return
    _em_processamento.add(after.id)

    try:
        # 1) cargos adicionados e removidos
        await _executar_etapa(bot, "aplicar cargos", _aplicar_cargos, bot, after)

        # 2) mensagem no chat de conversas
        msg_acesso = await _executar_etapa(
            bot, "mensagem em conversas", _enviar_msg_conversas, bot, after
        )

        # painel de configuração (lido uma vez, usado nos passos 3 e 4)
        cfg = await _executar_etapa(
            bot,
            "ler painel de configuração",
            ler_configuracoes,
            bot,
            ["ping_acolhimento_conversas", "minutos_ping_acolhimento", "boas_vindas_focus"],
        ) or {}

        # 3) mensagem no chat de boas-vindas (padrão: off; ignora bots)
        if cfg.get("boas_vindas_focus") == "on" and not after.bot:
            await _executar_etapa(bot, "boas-vindas", _enviar_boas_vindas, bot, after)

        # 4) thread privada no chat de conversas (padrão: off)
        if cfg.get("ping_acolhimento_conversas") == "on":
            try:
                minutos = int(cfg.get("minutos_ping_acolhimento", MINUTOS_PING_PADRAO))
                if minutos <= 0:
                    minutos = MINUTOS_PING_PADRAO
            except ValueError:
                minutos = MINUTOS_PING_PADRAO

            await _executar_etapa(
                bot,
                "thread de acolhimento",
                _criar_thread_acolhimento,
                bot,
                after,
                msg_acesso,
                minutos,
            )

        # 5) por último: procurar tópicos em CHAT_CONVITES e CHAT_REGRAS_TICKET_DE_ENTRADA
        async def _buscar(canal_id):
            canal = await obter_canal(bot, canal_id)
            if canal is None:
                raise RuntimeError(f"Canal {canal_id} não encontrado")
            return await buscar_threads_por_id(canal, after.id)

        threads_convites = await _executar_etapa(
            bot, "buscar tópicos (convites)", _buscar, CHAT_CONVITES
        )
        threads_tickets = await _executar_etapa(
            bot, "buscar tópicos (ticket de entrada)", _buscar, CHAT_REGRAS_TICKET_DE_ENTRADA
        )

        # avisa em todos os tópicos achados
        todas = {t.id: t for t in (threads_convites or []) + (threads_tickets or [])}
        await _executar_etapa(
            bot, "avisar nos tópicos", _avisar_threads, after, list(todas.values())
        )

        # ticket de entrada: avisa nos logs se não achou; senão apaga a mensagem do botão
        if threads_tickets is not None:
            if not threads_tickets:
                await enviar_logs(
                    bot,
                    f"⚠️ Nenhum tópico com o id `{after.id}` ({after.mention}) foi "
                    f"encontrado em <#{CHAT_REGRAS_TICKET_DE_ENTRADA}>.",
                )
            else:
                await _executar_etapa(
                    bot, "apagar mensagem do botão", _apagar_mensagens_botao, threads_tickets
                )

        # 6) usar agendamento para remover cargo de novato
        # Função auxiliar para agendamento
        async def _agendar(bot, user_id):
            mensagem = await agendar_tirar_novato(bot, user_id)

            canal_agenda = await obter_canal(bot, CHAT_AGENDAMENTOS)

            if canal_agenda is None:
                raise RuntimeError("CHAT_AGENDAMENTOS não encontrado")

            await canal_agenda.send(mensagem)

        
        await _executar_etapa(
            bot,
            "agendar remoção do cargo de novato",
            _agendar,
            bot,
            after.id,
        )

    
    finally:
        _em_processamento.discard(after.id)


# ---------------------------------------------------------------------------
# AVISO: MENSAGEM EM THREAD DE ACOLHIMENTO (thread trancada)
# ---------------------------------------------------------------------------

_REGEX_NOME_ACOLHIMENTO = re.compile(r"•\s*\d{15,20}$")


async def avisar_mensagem_em_thread_acolhimento(bot, message: discord.Message):
    canal = message.channel
    if message.author.bot:
        return
    if message.type not in (discord.MessageType.default, discord.MessageType.reply):
        return
    if not isinstance(canal, discord.Thread):
        return
    if canal.parent_id != CHAT_CONVERSAS or canal.type != discord.ChannelType.private_thread:
        return
    if not canal.locked or not _REGEX_NOME_ACOLHIMENTO.search(canal.name):
        return

    await enviar_logs(
        bot,
        f"⚠️ {message.author.mention} (`{message.author.id}`) enviou uma mensagem "
        f"na thread de acolhimento {canal.mention}: {message.jump_url}",
    )


def registrar(bot):
    """Chame uma vez no main: liga o aviso de mensagens nas threads de acolhimento."""

    async def _on_message(message: discord.Message):
        await avisar_mensagem_em_thread_acolhimento(bot, message)

    bot.add_listener(_on_message, "on_message")