"""
Gerenciador de agendamentos.

Lê o chat CHAT_AGENDAMENTOS três vezes por minuto (segundos :00, :20 e :40),
valida o formato das mensagens, interpreta data/horário e encaminha os dados
para a função da ação correspondente (dicionário AGENDAMENTOS).

O gerenciador controla e encaminha; os arquivos individuais executam.

Uso (por exemplo, no on_ready):

    from sistemas.agendamentos.gerenciador_agendamentos import rodar_agendamentos
    asyncio.create_task(rodar_agendamentos(bot))

IDs lidos de config.IDs:
    CHAT_AGENDAMENTOS               canal/thread onde os agendamentos são enviados
    CHAT_LOGS_COMPOSTO              lista de chats de log (mensagens erradas e execuções)
    CHAT_THREAD_LOGS_AGENDAMENTOS   thread onde as execuções bem-sucedidas são registradas
                                    (o registro, com o Motivo, também vai para CHAT_LOGS_COMPOSTO)

Formato de uma mensagem de agendamento:

    AGENDAR: DELETAR_THREAD
    QUANDO: 18/11/2026 20:57        (ou "20:57 18/11/2026", ou só "20:57" = dia do envio,
                                     ou relativo: "+60 min", "+2 h", "+1 dia")
    Motivo: por que está agendando isso   (opcional)
    Se_passar: Prosseguir           (ou Apagar)
    Link: https://discord.com/channels/...

Contrato das funções de ação (cada arquivo individual):

    async def executar(bot, dados, validar=False):
        - validar=True  -> NÃO executa nada; retorna None se o formato está certo
                           ou uma string explicando o que está errado.
        - validar=False -> executa a ação (levanta exceção se falhar).
                           Pode retornar um texto curto, que aparece como
                           "Resultado" no log de execuções.
"""
from __future__ import annotations

import asyncio
import io
import logging
import re
import time
import unicodedata
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import discord

# Importe aqui os arquivos de cada ação:
from . import agendar_cargos, agendar_deletar_mensagem, agendar_deletar_thread

# ----------------------------------------------------------------------------
# CONFIGURAÇÃO
# ----------------------------------------------------------------------------
# Não declare estes nomes de novo neste arquivo, senão o valor importado é sobrescrito.
from config.IDs import (  # noqa: E402
    CHAT_AGENDAMENTOS,
    CHAT_LOGS_COMPOSTO,
    CHAT_THREAD_LOGS_AGENDAMENTOS,
)

# Aceita lista, tupla, conjunto ou um ID único (número ou texto).
if isinstance(CHAT_LOGS_COMPOSTO, (int, str)):
    CHAT_LOGS_COMPOSTO = [CHAT_LOGS_COMPOSTO]
CHAT_LOGS_COMPOSTO = [int(c) for c in CHAT_LOGS_COMPOSTO]
CHAT_AGENDAMENTOS = int(CHAT_AGENDAMENTOS)
CHAT_THREAD_LOGS_AGENDAMENTOS = int(CHAT_THREAD_LOGS_AGENDAMENTOS)

FUSO = ZoneInfo("America/Sao_Paulo")   # fuso em que as datas/horas das mensagens são escritas
TOLERANCIA = timedelta(minutes=1)      # tolerância para o "Se_passar: Apagar"
DIAS_PARA_REENVIAR = 13                # mensagens com 13+ dias são apagadas e reenviadas
SE_PASSAR_PADRAO = "PROSSEGUIR"        # usado quando a mensagem não tem "Se_passar"
MOTIVO_OBRIGATORIO = False             # obrigatórios são só o título e o QUANDO; True exigiria também o "Motivo:"
INTERVALO_SEGUNDOS = 20                # lê o chat nos segundos :00, :20 e :40 (precisa dividir 60)
EMOJI_OK = "✅"

# Campos de texto livre: tudo que vier depois deles pertence a eles (multilinha).
CAMPOS_TEXTO_LIVRE = {"MENSAGEM"}

# ----------------------------------------------------------------------------
# TÍTULO -> FUNÇÃO
# ----------------------------------------------------------------------------
AGENDAMENTOS = {
    "DELETAR_THREAD": agendar_deletar_thread.executar,
    "APAGAR_THREAD": agendar_deletar_thread.executar,   # apelido da mesma ação
    "DELETAR_MENSAGEM": agendar_deletar_mensagem.executar,
    "APAGAR_MENSAGEM": agendar_deletar_mensagem.executar,   # apelido da mesma ação
    "CARGOS": agendar_cargos.executar,
    # "ENVIAR_MENSAGEM": agendar_enviar_mensagem.executar,
}

# ----------------------------------------------------------------------------
# INTERNOS
# ----------------------------------------------------------------------------
_log = logging.getLogger("agendamentos")

_TITULO_RE = re.compile(r"^AGENDAR(?:\s*:\s*|\s+)(.+)$", re.IGNORECASE)
_CAMPO_RE = re.compile(r"^\s*([A-Za-zÀ-ÿ_]+)\s*:(?!//)\s*(.*)$")
_DATA = r"(?P<dia>\d{1,2})/(?P<mes>\d{1,2})/(?P<ano>\d{4})"
_HORA = r"(?P<hora>\d{1,2}):(?P<minuto>\d{2})"
_QUANDO_RES = (
    re.compile(rf"^{_DATA}\s+{_HORA}$"),   # 18/11/2026 20:57
    re.compile(rf"^{_HORA}\s+{_DATA}$"),   # 20:57 18/11/2026
    re.compile(rf"^{_HORA}$"),             # 20:57 (mesmo dia da mensagem)
)
# QUANDO relativo: "+60 min", "+2 h", "+1 dia"... (h, hora(s), min, minuto(s), d, dia(s))
_RELATIVO_RE = re.compile(r"^\+\s*(\d{1,6})\s*(h|horas?|min|minutos?|d|dias?)$", re.IGNORECASE)
# Linha "Agendado_por: <@id>" que o próprio bot escreve ao reenviar um agendamento relativo.
_AUTOR_RE = re.compile(r"^\s*Agendado_por\s*:\s*<?@?!?(\d{15,20})", re.IGNORECASE | re.MULTILINE)
_AUTOR_LINHA_RE = re.compile(r"^\s*Agendado_por\s*:", re.IGNORECASE)
_QUANDO_LINHA_RE = re.compile(r"^(\s*QUANDO\s*:)", re.IGNORECASE)
_MOTIVO_LINHA_RE = re.compile(r"^(\s*MOTIVO\s*:)[ \t]*(.*)$", re.IGNORECASE)
_TIPOS_VALIDOS = (discord.MessageType.default, discord.MessageType.reply)

_tarefa: asyncio.Task | None = None
_loop_ativo = False
_listener_ok = False            # evita registrar o listener de on_ready várias vezes
_concluidos: set[int] = set()   # já executados/reenviados, mas cuja exclusão falhou (só tenta apagar de novo)
_avisados: set = set()          # problemas de configuração já avisados (evita repetir a cada ciclo)


class ErroAgendamento(Exception):
    """Mensagem de agendamento inválida."""


class SemTitulo(ErroAgendamento):
    """Mensagem sem título no formato AGENDAR: ACAO."""


# ---------------------------------------------------------------- interpretação
def _extrair_campos(linhas: list[str]) -> dict[str, str]:
    campos: dict[str, str] = {}
    atual = None
    for linha in linhas:
        m = _CAMPO_RE.match(linha)
        if m and atual not in CAMPOS_TEXTO_LIVRE:
            atual = m.group(1).upper()
            campos[atual] = m.group(2)
        elif atual is not None:
            campos[atual] += "\n" + linha
    return {k: v.strip() for k, v in campos.items()}


def _interpretar_quando(texto: str, msg: discord.Message) -> tuple[datetime, bool]:
    """Retorna (datetime, relativo). relativo=True para formatos como "+60 min"."""
    texto = texto.strip()

    rel = _RELATIVO_RE.match(texto)
    if rel:
        quantidade, unidade = int(rel.group(1)), rel.group(2).lower()
        if unidade.startswith("h"):
            delta = timedelta(hours=quantidade)
        elif unidade.startswith("m"):
            delta = timedelta(minutes=quantidade)
        else:
            delta = timedelta(days=quantidade)
        try:
            alvo = msg.created_at + delta   # a contagem parte do momento em que a mensagem foi enviada
        except OverflowError:
            raise ErroAgendamento("`QUANDO` relativo grande demais.")
        if alvo.second or alvo.microsecond:  # arredonda para cima: nunca executa antes do prazo pedido
            alvo = alvo.replace(second=0, microsecond=0) + timedelta(minutes=1)
        return alvo.astimezone(FUSO), True

    partes = None
    for padrao in _QUANDO_RES:
        m = padrao.match(texto)
        if m:
            partes = m.groupdict()
            break
    if partes is None:
        raise ErroAgendamento(
            "`QUANDO` inválido. Use `QUANDO: DD/MM/AAAA HH:MM`, `QUANDO: HH:MM DD/MM/AAAA`, "
            "`QUANDO: HH:MM` ou um prazo como `QUANDO: +60 min` (aceita h, horas, min, minutos, d, dias)."
        )
    try:
        if "dia" not in partes:  # só horário -> mesmo dia em que a mensagem foi enviada
            base = msg.created_at.astimezone(FUSO)
            partes.update(dia=base.day, mes=base.month, ano=base.year)
        quando = datetime(
            int(partes["ano"]), int(partes["mes"]), int(partes["dia"]),
            int(partes["hora"]), int(partes["minuto"]), tzinfo=FUSO,
        )
        return quando, False
    except ValueError:
        raise ErroAgendamento("`QUANDO` contém uma data ou horário que não existe.")


def interpretar(msg: discord.Message) -> dict:
    """Converte a mensagem em `dados`. Levanta ErroAgendamento se estiver errada."""
    # Troca "_>" por ">" em todo o conteúdo enviado ao executor.
    # (msg.content original não é alterado, para o reenvio de 13+ dias não modificar nada.)
    conteudo = unicodedata.normalize("NFC", (msg.content or "").replace("_>", ">"))  # NFC: "ç"/"ã" sempre iguais
    linhas = conteudo.strip().splitlines()
    if not linhas:
        raise SemTitulo("Mensagem sem título (conteúdo vazio).")

    titulo = linhas[0].strip().strip("*`#> \t")
    m = _TITULO_RE.match(titulo)
    if not m:
        raise SemTitulo("Título ausente ou fora do formato `AGENDAR: NOME_DA_ACAO`.")

    acao = re.sub(r"\s+", "_", m.group(1).strip()).upper()   # "deletar mensagem" == "DELETAR_MENSAGEM"
    if acao not in AGENDAMENTOS:
        disponiveis = ", ".join(f"`{a}`" for a in AGENDAMENTOS) or "nenhuma"
        raise ErroAgendamento(f"Ação `{acao}` não existe. Disponíveis: {disponiveis}.")

    campos = _extrair_campos(linhas[1:])

    if "QUANDO" not in campos or not campos["QUANDO"]:
        raise ErroAgendamento("Falta o campo `QUANDO`.")
    quando, relativo = _interpretar_quando(campos["QUANDO"], msg)

    se_passar = campos.get("SE_PASSAR", SE_PASSAR_PADRAO).strip().upper()
    if se_passar not in ("PROSSEGUIR", "APAGAR"):
        raise ErroAgendamento("`Se_passar` deve ser `Prosseguir` ou `Apagar`.")

    motivo = campos.get("MOTIVO", "").strip()
    if MOTIVO_OBRIGATORIO and not motivo:
        raise ErroAgendamento("Falta o campo `Motivo` (explique por que está agendando isso).")

    return {
        "mensagem": msg,
        "autor": msg.author,
        "guild": msg.guild,
        "acao": acao,
        "quando": quando,
        "relativo": relativo,   # True se veio como "+60 min"
        "se_passar": se_passar,
        "campos": campos,
        "motivo": motivo,
        "conteudo": conteudo,   # texto completo já com "_>" trocado por ">"
    }


# ---------------------------------------------------------------- utilitários
async def _obter_canal(bot, canal_id: int):
    canal = bot.get_channel(canal_id)
    if canal is None:
        try:
            canal = await bot.fetch_channel(canal_id)
        except discord.HTTPException:
            return None
    return canal


def _cortar(texto: str, limite: int = 2000) -> str:
    return texto if len(texto) <= limite else texto[: limite - 1] + "…"


def _avisar_uma_vez(chave, texto: str) -> None:
    """Registra um aviso de configuração só na primeira vez (não repete a cada ciclo)."""
    if chave not in _avisados:
        _avisados.add(chave)
        _log.warning(texto)


def _mesmo_servidor(canal, msg: discord.Message) -> bool:
    """True se o canal pertence ao mesmo servidor em que a mensagem foi enviada."""
    guild_canal = getattr(canal, "guild", None)
    return guild_canal is not None and msg.guild is not None and guild_canal.id == msg.guild.id


def _id_do_autor(bot, msg: discord.Message) -> int:
    """
    ID de quem agendou. Em mensagens reenviadas pelo bot (QUANDO relativo), o autor real
    vem da linha "Agendado_por". Essa linha só vale se a mensagem foi enviada pelo próprio
    bot, então ninguém consegue se passar por outra pessoa escrevendo-a à mão.
    """
    if msg.author.id == bot.user.id:
        m = _AUTOR_RE.search(msg.content or "")
        if m:
            return int(m.group(1))
    return msg.author.id


def _nome_autor(bot, msg: discord.Message, autor_id: int) -> str:
    if autor_id == msg.author.id:
        return str(msg.author)
    usuario = bot.get_user(autor_id)
    return str(usuario) if usuario else "usuário desconhecido"


async def _apagar(msg: discord.Message) -> bool:
    try:
        await msg.delete()
        return True
    except discord.NotFound:
        return True
    except discord.HTTPException as e:
        _log.warning("Falha ao apagar a mensagem %s: %s", msg.id, e)
        return False


# ---------------------------------------------------------------- logs de mensagens erradas
async def _enviar_logs(bot, msg: discord.Message, motivo: str) -> None:
    """
    Envia aos chats de log: cópia da mensagem original + outra mensagem com o motivo.
    A pessoa só é marcada no chat de log do servidor em que ela enviou a mensagem;
    nos demais servidores aparece apenas o nome e o ID (sem marcar).
    """
    quando_env = msg.created_at.astimezone(FUSO).strftime("%d/%m/%Y %H:%M:%S")
    autor_id = _id_do_autor(bot, msg)
    autor_nome = _nome_autor(bot, msg, autor_id)
    # Baixa os anexos antes da mensagem ser apagada (os links morrem junto com ela).
    baixados, links = [], []
    for a in msg.attachments:
        try:
            baixados.append((a.filename, await a.read()))
        except discord.HTTPException:
            links.append(a.url)

    corpo = msg.content or "*(sem texto)*"
    if links:
        corpo += "\n" + "\n".join(links)
    copia = _cortar(
        f"📋 **Mensagem removida** — autor: {autor_nome} (`{autor_id}`), enviada em {quando_env}\n>>> {corpo}"
    )
    sem_mencoes = discord.AllowedMentions.none()

    for canal_id in CHAT_LOGS_COMPOSTO:
        canal = await _obter_canal(bot, canal_id)
        if canal is None:
            _avisar_uma_vez(("log", canal_id), f"Canal de log {canal_id} não encontrado.")
            continue

        if _mesmo_servidor(canal, msg):
            aviso = _cortar(f"<@{autor_id}> {motivo}")
            mencoes_aviso = discord.AllowedMentions(users=[discord.Object(id=autor_id)])
        else:
            aviso = _cortar(f"**{autor_nome}** (`{autor_id}`) {motivo}")
            mencoes_aviso = sem_mencoes

        try:
            arquivos = [discord.File(io.BytesIO(dados), filename=nome) for nome, dados in baixados]
            try:
                await canal.send(copia, files=arquivos, allowed_mentions=sem_mencoes)
            except discord.HTTPException:
                if not arquivos:
                    raise
                # Anexos grandes demais para este canal: envia a cópia sem os arquivos.
                await canal.send(
                    _cortar(copia + f"\n*(anexos não enviados: {', '.join(n for n, _ in baixados)})*"),
                    allowed_mentions=sem_mencoes,
                )
            await canal.send(aviso, allowed_mentions=mencoes_aviso)
        except discord.HTTPException as e:
            _log.warning("Falha ao enviar log em %s: %s", canal_id, e)


async def _descartar(bot, msg: discord.Message, motivo: str) -> None:
    """Apaga a mensagem e registra nos chats de log."""
    try:
        await _enviar_logs(bot, msg, motivo)
    except Exception:
        _log.exception("Erro ao enviar os logs da mensagem %s", msg.id)  # não pode impedir a exclusão
    await _apagar(msg)


# ---------------------------------------------------------------- log de execuções
def _montar_embed_execucao(bot, canal, msg: discord.Message, dados: dict, resultado) -> discord.Embed:
    """Monta o embed de execução. A pessoa só é marcada se o canal for do mesmo servidor dela."""
    agora = datetime.now(FUSO)
    quando = dados["quando"]
    atraso_min = int((agora.replace(second=0, microsecond=0) - quando).total_seconds() // 60)

    embed = discord.Embed(
        title="📅 Agendamento executado",
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow(),
    )

    autor_id = dados.get("autor_id") or msg.author.id
    if autor_id == bot.user.id:
        pessoa = "🤖 O próprio bot (mensagem reenviada)"
    elif _mesmo_servidor(canal, msg):
        pessoa = f"<@{autor_id}>\n`{autor_id}`"
    else:
        pessoa = f"{_nome_autor(bot, msg, autor_id)} (`{autor_id}`)"

    embed.add_field(name="⚙️ Ação", value=f"`{dados['acao']}`", inline=True)
    embed.add_field(name="👤 Agendado por", value=pessoa, inline=True)
    embed.add_field(name="📋 Motivo", value=_cortar(dados["motivo"] or "Não informado.", 1024), inline=False)
    embed.add_field(name="⏰ Quando", value=quando.strftime("%d/%m/%Y %H:%M"), inline=False)
    embed.add_field(name="✅ Executado em", value=agora.strftime("%d/%m/%Y %H:%M:%S"), inline=True)
    if atraso_min >= 1:
        embed.add_field(name="⏱️ Atraso", value=f"{atraso_min} min", inline=True)

    detalhes = "\n".join(
        f"**{chave}**: {_cortar(valor, 300)}"
        for chave, valor in dados["campos"].items()
        if chave not in ("QUANDO", "SE_PASSAR", "MOTIVO", "AGENDADO_POR")
    )
    if detalhes:
        embed.add_field(name="📝 Dados", value=_cortar(detalhes, 1024), inline=False)

    if isinstance(resultado, str) and resultado.strip():
        embed.add_field(name="📊 Resultado", value=_cortar(resultado, 1024), inline=False)

    embed.add_field(name="🆔 ID do agendamento", value=f"`{msg.id}`", inline=False)
    return embed


async def _enviar_embed(canal, embed: discord.Embed) -> None:
    # Thread arquivada: desarquiva para conseguir escrever nela.
    if isinstance(canal, discord.Thread) and canal.archived:
        await canal.edit(archived=False)
    await canal.send(embed=embed)


async def _registrar_execucao(bot, msg: discord.Message, dados: dict, resultado) -> None:
    """
    Registra uma execução bem-sucedida (com o Motivo) na thread
    CHAT_THREAD_LOGS_AGENDAMENTOS e em todos os chats de CHAT_LOGS_COMPOSTO.
    """
    destinos = [CHAT_THREAD_LOGS_AGENDAMENTOS]
    destinos += [c for c in CHAT_LOGS_COMPOSTO if c not in destinos]

    for canal_id in destinos:
        canal = await _obter_canal(bot, canal_id)
        if canal is None:
            _avisar_uma_vez(("log_execucao", canal_id), f"Canal de log {canal_id} não encontrado.")
            continue
        try:
            await _enviar_embed(canal, _montar_embed_execucao(bot, canal, msg, dados, resultado))
        except discord.HTTPException as e:
            _log.warning("Falha ao registrar a execução em %s: %s", canal_id, e)


# ---------------------------------------------------------------- reenvio (13+ dias e QUANDO relativo)
def _nome_exibicao(autor) -> str:
    nome = getattr(autor, "display_name", None) or str(autor)
    return " ".join(str(nome).split())  # sem quebras de linha


def _texto_para_reenvio(bot, msg: discord.Message, dados: dict, quando_txt: str | None = None) -> str | None:
    """
    Texto que o bot vai reenviar. Como o reenvio sai em nome do bot, o autor original
    fica registrado no próprio texto:
      - o "Motivo:" passa a começar com o nome de quem agendou ("Jeftoide: ..."), uma única
        vez (mensagens que o bot já reenviou antes já têm o nome);
      - "Agendado_por: <@id>" guarda o ID, para marcar a pessoa e identificá-la nos logs;
      - se quando_txt for dado (QUANDO relativo), o valor do QUANDO é trocado por ele.
    Retorna None se não encontrar a linha do QUANDO.
    """
    autor_id = dados["autor_id"]
    prefixo = f"{_nome_exibicao(msg.author)}:" if msg.author.id != bot.user.id else None

    linhas: list[str] = []
    pos_quando = None
    motivo_feito = livre = False
    for linha in (msg.content or "").splitlines():
        if livre:  # dentro de um campo de texto livre (ex.: MENSAGEM): não mexe em nada
            linhas.append(linha)
            continue
        if _AUTOR_LINHA_RE.match(linha):
            continue  # sempre regravado abaixo (nunca reaproveita um escrito à mão)
        campo = _CAMPO_RE.match(linha)
        if campo and campo.group(1).upper() in CAMPOS_TEXTO_LIVRE:
            livre = True
            linhas.append(linha)
            continue

        m = _QUANDO_LINHA_RE.match(linha)
        if m and pos_quando is None:
            linhas.append(f"{m.group(1)} {quando_txt}" if quando_txt else linha)
            if autor_id != bot.user.id:
                linhas.append(f"Agendado_por: <@{autor_id}>")
            pos_quando = len(linhas)
            continue

        m = _MOTIVO_LINHA_RE.match(linha)
        if m and prefixo and not motivo_feito:
            motivo_feito = True
            valor = m.group(2)
            if not valor.lower().startswith(prefixo.lower()):
                linha = f"{m.group(1)} {prefixo} {valor}".rstrip()
        linhas.append(linha)

    if pos_quando is None:
        return None
    if prefixo and not motivo_feito:  # não havia "Motivo:": cria um só com o nome
        linhas.insert(pos_quando, f"Motivo: {prefixo}")
    return "\n".join(linhas)


async def _reenviar(msg: discord.Message, conteudo: str, conferida: bool = False) -> bool:
    """Envia uma cópia com o conteúdo dado (e os anexos) e apaga a original. True se deu certo."""
    try:
        arquivos = [await a.to_file() for a in msg.attachments]
        nova = await msg.channel.send(
            content=conteudo or None,
            files=arquivos,
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except discord.HTTPException as e:
        _log.warning("Falha ao reenviar a mensagem %s: %s", msg.id, e)
        return False  # original continua intacta; tenta de novo no próximo ciclo
    if conferida:
        try:
            await nova.add_reaction(EMOJI_OK)
        except discord.HTTPException:
            pass
    if not await _apagar(msg):
        _concluidos.add(msg.id)  # a cópia já existe: não reenviar de novo, só tentar apagar
    return True


async def _reenviar_se_antiga(bot, msg: discord.Message, dados: dict, conferida: bool) -> None:
    """
    Mensagens com 13+ dias são apagadas e reenviadas. O conteúdo fica igual, exceto o
    nome de quem agendou no início do Motivo (e a linha Agendado_por).
    """
    idade = discord.utils.utcnow() - msg.created_at
    if idade < timedelta(days=DIAS_PARA_REENVIAR):
        return
    novo = _texto_para_reenvio(bot, msg, dados)
    if novo is None or len(novo) > 2000:
        novo = msg.content  # não deu para reescrever: reenvia exatamente como está
    await _reenviar(msg, novo, conferida)


async def _reenviar_com_data(bot, msg: discord.Message, dados: dict) -> None:
    """QUANDO relativo ("+60 min"): apaga a mensagem e reenvia com a data e hora já calculadas."""
    novo = _texto_para_reenvio(bot, msg, dados, dados["quando"].strftime("%d/%m/%Y %H:%M"))
    if novo is None:
        await _descartar(bot, msg, "❌ Agendamento inválido: não consegui reescrever o campo `QUANDO`.")
        return
    if len(novo) > 2000:
        await _descartar(
            bot, msg,
            "❌ Agendamento inválido: a mensagem fica grande demais (limite de 2000 caracteres) ao reenviar com a data.",
        )
        return
    await _reenviar(msg, novo)


# ---------------------------------------------------------------- processamento
async def _executar(bot, msg: discord.Message, dados: dict, funcao) -> None:
    try:
        resultado = await funcao(bot, dados)
    except Exception as e:
        _log.exception("Erro ao executar o agendamento %s (%s)", msg.id, dados["acao"])
        await _descartar(bot, msg, f"❌ Erro ao executar `{dados['acao']}`: `{e}`")
        return

    _concluidos.add(msg.id)

    try:
        await _registrar_execucao(bot, msg, dados, resultado)
    except Exception:
        _log.exception("Erro ao registrar a execução do agendamento %s", msg.id)

    if await _apagar(msg):
        _concluidos.discard(msg.id)


async def _processar(bot, msg: discord.Message) -> None:
    if msg.type not in _TIPOS_VALIDOS:
        return

    # Já executada, mas a exclusão falhou antes: só tenta apagar de novo.
    if msg.id in _concluidos:
        if await _apagar(msg):
            _concluidos.discard(msg.id)
        return

    conferida = any(str(r.emoji) == EMOJI_OK and r.me for r in msg.reactions)

    # 1) Interpretação (título, QUANDO, Se_passar)
    try:
        dados = interpretar(msg)
    except ErroAgendamento as e:  # inclui SemTitulo e ação inexistente
        await _descartar(bot, msg, f"❌ Agendamento inválido: {e}")
        return

    dados["autor_id"] = _id_do_autor(bot, msg)

    # 1b) QUANDO relativo ("+60 min"): apaga e reenvia com a data e hora já calculadas.
    #     A mensagem reenviada (sem ✅) é validada normalmente no ciclo seguinte.
    if dados["relativo"]:
        await _reenviar_com_data(bot, msg, dados)
        return

    funcao = AGENDAMENTOS[dados["acao"]]

    # 2) Validação pelo executor (só mensagens sem ✅)
    if not conferida:
        erro = await funcao(bot, dados, validar=True)
        if erro:
            await _descartar(bot, msg, f"❌ Agendamento inválido: {erro}")
            return
        try:
            await msg.add_reaction(EMOJI_OK)
        except discord.HTTPException:
            pass
        conferida = True

    # 3) Chegou a hora?
    agora = datetime.now(FUSO)
    if agora >= dados["quando"]:
        atraso = agora.replace(second=0, microsecond=0) - dados["quando"]
        if atraso > TOLERANCIA and dados["se_passar"] == "APAGAR":
            await _descartar(
                bot, msg,
                f"⏰ Agendamento expirado (era para {dados['quando']:%d/%m/%Y %H:%M}) "
                f"e está com `Se_passar: Apagar`.",
            )
            return
        await _executar(bot, msg, dados, funcao)
        return

    # 4) Ainda não é a hora: mantém viva (reenvia se tiver 13+ dias)
    await _reenviar_se_antiga(bot, msg, dados, conferida)


async def _ciclo(bot) -> None:
    canal = await _obter_canal(bot, CHAT_AGENDAMENTOS)
    if canal is None:
        _avisar_uma_vez(
            "canal_agendamentos",
            f"Canal CHAT_AGENDAMENTOS ({CHAT_AGENDAMENTOS}) não encontrado.",
        )
        return

    mensagens = [m async for m in canal.history(limit=None, oldest_first=True)]
    for msg in mensagens:
        try:
            await _processar(bot, msg)
        except Exception:
            _log.exception("Erro ao processar a mensagem %s", msg.id)


# ---------------------------------------------------------------- loop
async def _loop(bot) -> None:
    """Garante que só exista UM loop rodando, mesmo se for chamado várias vezes."""
    global _loop_ativo
    if _loop_ativo:
        return
    _loop_ativo = True
    try:
        await _loop_interno(bot)
    finally:
        _loop_ativo = False


async def _loop_interno(bot) -> None:
    await bot.wait_until_ready()

    while not bot.is_closed():
        try:
            await _ciclo(bot)
        except Exception:
            _log.exception("Erro no ciclo de agendamentos")
        # Alinha com os segundos :00, :20 e :40 do relógio (+0,2s de margem).
        await asyncio.sleep(INTERVALO_SEGUNDOS - (time.time() % INTERVALO_SEGUNDOS) + 0.2)


# ---------------------------------------------------------------- entrada pública
def _configurar_ids(chat_agendamentos=None, chats_logs=None) -> None:
    """Sobrescreve os IDs do config, se forem passados."""
    global CHAT_AGENDAMENTOS, CHAT_LOGS_COMPOSTO
    if chat_agendamentos is not None:
        CHAT_AGENDAMENTOS = int(chat_agendamentos)
    if chats_logs is not None:
        if isinstance(chats_logs, (int, str)):
            chats_logs = [chats_logs]
        CHAT_LOGS_COMPOSTO = [int(c) for c in chats_logs]


def _ao_terminar(tarefa: asyncio.Task) -> None:
    """Se a tarefa morrer por um erro, registra o erro em vez de sumir em silêncio."""
    if tarefa.cancelled():
        return
    erro = tarefa.exception()
    if erro is not None:
        _log.error("A tarefa de agendamentos parou por um erro.", exc_info=erro)


def _garantir_tarefa(bot) -> None:
    global _tarefa
    if _tarefa is None or _tarefa.done():
        _tarefa = asyncio.get_running_loop().create_task(_loop(bot))
        _tarefa.add_done_callback(_ao_terminar)


def iniciar_agendamentos(bot, chat_agendamentos=None, chats_logs=None) -> None:
    """
    Alternativa síncrona: registra o início para quando o bot ficar online.
    Se não forem passados IDs, usa os do config.IDs.
    """
    global _listener_ok
    _configurar_ids(chat_agendamentos, chats_logs)

    async def _on_ready():
        _garantir_tarefa(bot)

    if not _listener_ok:
        bot.add_listener(_on_ready, "on_ready")
        _listener_ok = True
    if bot.is_ready():  # caso seja chamado depois do bot já estar online
        _garantir_tarefa(bot)


async def rodar_agendamentos(bot, chat_agendamentos=None, chats_logs=None) -> None:
    """
    Versão em corrotina. Exemplo (dentro de uma função async, como o on_ready):

        asyncio.create_task(rodar_agendamentos(bot))
    """
    _configurar_ids(chat_agendamentos, chats_logs)
    await _loop(bot)