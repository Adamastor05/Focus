"""
Gerenciador de agendamentos.

Lê o chat CHAT_AGENDAMENTOS duas vezes por minuto (segundos :00 e :30),
valida o formato das mensagens, interpreta data/horário e encaminha os dados
para a função da ação correspondente (dicionário AGENDAMENTOS).

O gerenciador controla e encaminha; os arquivos individuais executam.

Uso no main (sem cogs):

    from sistemas.agendamentos.gerenciador_agendamentos import iniciar_agendamentos
    iniciar_agendamentos(bot)      # chamar antes do bot.run() ou dentro do setup_hook

Formato de uma mensagem de agendamento:

    AGENDAR: APAGAR_THREAD
    QUANDO: 18/11/2026 20:57        (ou só "20:57" -> mesmo dia do envio da mensagem)
    Se_passar: Prosseguir           (ou Apagar)
    THREAD: 123456789012345678

Contrato das funções de ação (cada arquivo individual):

    async def executar(bot, dados, validar=False):
        - validar=True  -> NÃO executa nada; retorna None se o formato está certo
                           ou uma string explicando o que está errado.
        - validar=False -> executa a ação (levanta exceção se falhar).
"""
from __future__ import annotations

import asyncio
import io
import re
import time
import traceback
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import discord

# Importe aqui os arquivos de cada ação:
from . import agendar_deletar_thread

# ----------------------------------------------------------------------------
# CONFIGURAÇÃO
# ----------------------------------------------------------------------------
# IDs vêm do seu config (não declare CHAT_AGENDAMENTOS/CHAT_LOGS_COMPOSTO de novo
# neste arquivo, senão o valor importado é sobrescrito).
from config.IDs import CHAT_AGENDAMENTOS, CHAT_LOGS_COMPOSTO  # noqa: E402

# Aceita lista, tupla, conjunto ou um ID único (número ou texto).
if isinstance(CHAT_LOGS_COMPOSTO, (int, str)):
    CHAT_LOGS_COMPOSTO = [CHAT_LOGS_COMPOSTO]
CHAT_LOGS_COMPOSTO = [int(c) for c in CHAT_LOGS_COMPOSTO]
CHAT_AGENDAMENTOS = int(CHAT_AGENDAMENTOS)

FUSO = ZoneInfo("America/Sao_Paulo")   # fuso em que as datas/horas das mensagens são escritas
TOLERANCIA = timedelta(minutes=1)      # tolerância para o "Se_passar: Apagar"
DIAS_PARA_REENVIAR = 13                # mensagens com 13+ dias são apagadas e reenviadas
SE_PASSAR_PADRAO = "PROSSEGUIR"        # usado quando a mensagem não tem "Se_passar"
EMOJI_OK = "✅"
DEBUG = True                           # imprime no console o que o gerenciador está fazendo (ponha False depois)

# Campos de texto livre: tudo que vier depois deles pertence a eles (multilinha).
CAMPOS_TEXTO_LIVRE = {"MENSAGEM"}

# ----------------------------------------------------------------------------
# TÍTULO -> FUNÇÃO
# ----------------------------------------------------------------------------
AGENDAMENTOS = {
    "DELETAR_THREAD": agendar_deletar_thread.executar,
    "APAGAR_THREAD": agendar_deletar_thread.executar,   # apelido da mesma ação
    # "ENVIAR_MENSAGEM": agendar_enviar_mensagem.executar,
}

# ----------------------------------------------------------------------------
# INTERNOS
# ----------------------------------------------------------------------------
_TITULO_RE = re.compile(r"^AGENDAR(?:\s*:\s*|\s+)([A-Za-z0-9_]+)$", re.IGNORECASE)
_CAMPO_RE = re.compile(r"^\s*([A-Za-z_]+)\s*:(?!//)\s*(.*)$")
_DATA = r"(?P<dia>\d{1,2})/(?P<mes>\d{1,2})/(?P<ano>\d{4})"
_HORA = r"(?P<hora>\d{1,2}):(?P<minuto>\d{2})"
_QUANDO_RES = (
    re.compile(rf"^{_DATA}\s+{_HORA}$"),   # 18/11/2026 20:57
    re.compile(rf"^{_HORA}\s+{_DATA}$"),   # 20:57 18/11/2026
    re.compile(rf"^{_HORA}$"),             # 20:57 (mesmo dia da mensagem)
)
_TIPOS_VALIDOS = (discord.MessageType.default, discord.MessageType.reply)

_tarefa: asyncio.Task | None = None
_listener_ok = False            # evita registrar o listener de on_ready várias vezes
_concluidos: set[int] = set()   # executados, mas cuja exclusão falhou (evita executar de novo)


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


def _interpretar_quando(texto: str, msg: discord.Message) -> datetime:
    texto = texto.strip()
    partes = None
    for padrao in _QUANDO_RES:
        m = padrao.match(texto)
        if m:
            partes = m.groupdict()
            break
    if partes is None:
        raise ErroAgendamento(
            "`QUANDO` inválido. Use `QUANDO: DD/MM/AAAA HH:MM`, `QUANDO: HH:MM DD/MM/AAAA` "
            "ou apenas `QUANDO: HH:MM`."
        )
    try:
        if "dia" not in partes:  # só horário -> mesmo dia em que a mensagem foi enviada
            base = msg.created_at.astimezone(FUSO)
            partes.update(dia=base.day, mes=base.month, ano=base.year)
        return datetime(
            int(partes["ano"]), int(partes["mes"]), int(partes["dia"]),
            int(partes["hora"]), int(partes["minuto"]), tzinfo=FUSO,
        )
    except ValueError:
        raise ErroAgendamento("`QUANDO` contém uma data ou horário que não existe.")


def interpretar(msg: discord.Message) -> dict:
    """Converte a mensagem em `dados`. Levanta ErroAgendamento se estiver errada."""
    # Troca "_>" por ">" em todo o conteúdo enviado ao executor.
    # (msg.content original não é alterado, para o reenvio de 13+ dias não modificar nada.)
    conteudo = (msg.content or "").replace("_>", ">")
    linhas = conteudo.strip().splitlines()
    if not linhas:
        raise SemTitulo("Mensagem sem título (conteúdo vazio).")

    titulo = linhas[0].strip().strip("*`#> \t")
    m = _TITULO_RE.match(titulo)
    if not m:
        raise SemTitulo("Título ausente ou fora do formato `AGENDAR: NOME_DA_ACAO`.")

    acao = m.group(1).upper()
    if acao not in AGENDAMENTOS:
        disponiveis = ", ".join(f"`{a}`" for a in AGENDAMENTOS) or "nenhuma"
        raise ErroAgendamento(f"Ação `{acao}` não existe. Disponíveis: {disponiveis}.")

    campos = _extrair_campos(linhas[1:])

    if "QUANDO" not in campos or not campos["QUANDO"]:
        raise ErroAgendamento("Falta o campo `QUANDO`.")
    quando = _interpretar_quando(campos["QUANDO"], msg)

    se_passar = campos.get("SE_PASSAR", SE_PASSAR_PADRAO).strip().upper()
    if se_passar not in ("PROSSEGUIR", "APAGAR"):
        raise ErroAgendamento("`Se_passar` deve ser `Prosseguir` ou `Apagar`.")

    return {
        "mensagem": msg,
        "autor": msg.author,
        "guild": msg.guild,
        "acao": acao,
        "quando": quando,
        "se_passar": se_passar,
        "campos": campos,
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


async def _apagar(msg: discord.Message) -> bool:
    try:
        await msg.delete()
        return True
    except discord.NotFound:
        return True
    except discord.HTTPException as e:
        print(f"[agendamentos] Falha ao apagar mensagem {msg.id}: {e}")
        return False


async def _enviar_logs(bot, msg: discord.Message, motivo: str) -> None:
    """Envia aos chats de log: cópia da mensagem original + outra mensagem com o motivo."""
    quando_env = msg.created_at.astimezone(FUSO).strftime("%d/%m/%Y %H:%M:%S")
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
        f"📋 **Mensagem removida** — autor: {msg.author} (`{msg.author.id}`), enviada em {quando_env}\n>>> {corpo}"
    )
    aviso = _cortar(f"{msg.author.mention} {motivo}")
    sem_mencoes = discord.AllowedMentions.none()

    for canal_id in CHAT_LOGS_COMPOSTO:
        canal = await _obter_canal(bot, canal_id)
        if canal is None:
            print(f"[agendamentos] Canal de log {canal_id} não encontrado.")
            continue
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
            await canal.send(aviso, allowed_mentions=discord.AllowedMentions(users=True))
        except discord.HTTPException as e:
            print(f"[agendamentos] Falha ao enviar log em {canal_id}: {e}")


async def _descartar(bot, msg: discord.Message, motivo: str) -> None:
    """Apaga a mensagem e registra nos chats de log."""
    if DEBUG:
        print(f"[agendamentos] descartando mensagem {msg.id}: {motivo}")
    try:
        await _enviar_logs(bot, msg, motivo)
    except Exception:
        traceback.print_exc()   # um erro nos logs não pode impedir a exclusão
    await _apagar(msg)


async def _reenviar_se_antiga(msg: discord.Message, conferida: bool) -> None:
    """Mensagens com 13+ dias são apagadas e reenviadas sem modificar o conteúdo."""
    idade = discord.utils.utcnow() - msg.created_at
    if idade < timedelta(days=DIAS_PARA_REENVIAR):
        return
    try:
        arquivos = [await a.to_file() for a in msg.attachments]
        nova = await msg.channel.send(
            content=msg.content or None,
            files=arquivos,
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except discord.HTTPException as e:
        print(f"[agendamentos] Falha ao reenviar {msg.id}: {e}")
        return  # original continua intacto
    if conferida:
        try:
            await nova.add_reaction(EMOJI_OK)
        except discord.HTTPException:
            pass
    await _apagar(msg)


# ---------------------------------------------------------------- processamento
async def _executar(bot, msg: discord.Message, dados: dict, funcao) -> None:
    try:
        await funcao(bot, dados)
    except Exception as e:
        traceback.print_exc()
        await _descartar(bot, msg, f"❌ Erro ao executar `{dados['acao']}`: `{e}`")
        return
    _concluidos.add(msg.id)
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

    funcao = AGENDAMENTOS[dados["acao"]]

    # 2) Validação pelo executor (só mensagens sem ✅)
    if not conferida:
        erro = await funcao(bot, dados, validar=True)
        if erro:
            await _descartar(bot, msg, f"❌ Agendamento inválido: {erro}")
            return
        try:
            await msg.add_reaction(EMOJI_OK)
        except discord.HTTPException as e:
            print(f"[agendamentos] Não consegui reagir à mensagem {msg.id}: {e}")
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
    await _reenviar_se_antiga(msg, conferida)


async def _ciclo(bot) -> None:
    canal = await _obter_canal(bot, CHAT_AGENDAMENTOS)
    if canal is None:
        print(f"[agendamentos] Canal CHAT_AGENDAMENTOS ({CHAT_AGENDAMENTOS}) não encontrado.")
        return

    mensagens = [m async for m in canal.history(limit=None, oldest_first=True)]
    if DEBUG:
        print(f"[agendamentos] ciclo {datetime.now(FUSO):%H:%M:%S}: {len(mensagens)} mensagem(ns) lida(s) no canal.")
    for msg in mensagens:
        try:
            await _processar(bot, msg)
        except Exception:
            traceback.print_exc()


async def _diagnostico(bot) -> None:
    """Imprime no console tudo que costuma impedir o sistema de funcionar."""
    canal = await _obter_canal(bot, CHAT_AGENDAMENTOS)
    if canal is None:
        print(
            f"[agendamentos] ❌ Canal de agendamentos ({CHAT_AGENDAMENTOS}) NÃO encontrado. "
            "Confira o ID e se o bot enxerga o canal."
        )
    else:
        print(f"[agendamentos] ✅ Monitorando {canal} (id {CHAT_AGENDAMENTOS}). Logs em: {CHAT_LOGS_COMPOSTO}")

        if getattr(bot.intents, "message_content", False):
            print("[agendamentos] ✅ Intent message_content: ligada.")
        else:
            print("[agendamentos] ❌ Intent message_content DESLIGADA: o bot não lê o texto das mensagens.")

        guild = getattr(canal, "guild", None)
        if guild is not None and guild.me is not None:
            p = canal.permissions_for(guild.me)
            checagens = [
                ("Ver Canal", p.view_channel),
                ("Ler Histórico de Mensagens", p.read_message_history),
                ("Gerenciar Mensagens", p.manage_messages),
                ("Adicionar Reações", p.add_reactions),
            ]
            faltando = [nome for nome, ok in checagens if not ok]
            if faltando:
                print(f"[agendamentos] ❌ Permissões que FALTAM no canal de agendamentos: {', '.join(faltando)}")
            else:
                print("[agendamentos] ✅ Permissões no canal de agendamentos: OK.")

    for log_id in CHAT_LOGS_COMPOSTO:
        if await _obter_canal(bot, log_id) is None:
            print(f"[agendamentos] ❌ Canal de log ({log_id}) NÃO encontrado.")


_loop_ativo = False


async def _loop(bot) -> None:
    """Garante que só exista UM loop rodando, mesmo se for chamado várias vezes."""
    global _loop_ativo
    if _loop_ativo:
        print("[agendamentos] Já está rodando; ignorando a chamada repetida.")
        return
    _loop_ativo = True
    try:
        await _loop_interno(bot)
    finally:
        _loop_ativo = False


async def _loop_interno(bot) -> None:
    await bot.wait_until_ready()

    try:
        await _diagnostico(bot)
    except Exception:
        traceback.print_exc()

    while not bot.is_closed():
        try:
            await _ciclo(bot)
        except Exception:
            traceback.print_exc()
        # Alinha com os segundos :00 e :30 do relógio (+0,2s de margem).
        await asyncio.sleep(30 - (time.time() % 30) + 0.2)


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
    """Se a tarefa morrer por um erro, mostra o erro em vez de sumir em silêncio."""
    if tarefa.cancelled():
        print("[agendamentos] ⚠️ A tarefa de agendamentos foi cancelada.")
        return
    erro = tarefa.exception()
    if erro is not None:
        print("[agendamentos] ❌ A tarefa de agendamentos PAROU por um erro:")
        traceback.print_exception(type(erro), erro, erro.__traceback__)


def _garantir_tarefa(bot) -> None:
    global _tarefa
    if _tarefa is None or _tarefa.done():
        print("[agendamentos] Bot online: iniciando a tarefa de monitoramento...")
        _tarefa = asyncio.get_running_loop().create_task(_loop(bot))
        _tarefa.add_done_callback(_ao_terminar)


def iniciar_agendamentos(bot, chat_agendamentos=None, chats_logs=None) -> None:
    """
    Chame uma vez no main. Inicia o monitoramento quando o bot ficar pronto.

        iniciar_agendamentos(bot, CHAT_AGENDAMENTOS, CHAT_LOGS_COMPOSTO)

    chat_agendamentos: ID do canal de agendamentos.
    chats_logs: lista de IDs dos canais de log (aceita também um ID único).
    Se não forem passados, usa as constantes do topo deste arquivo.
    """
    global _listener_ok
    _configurar_ids(chat_agendamentos, chats_logs)

    print("[agendamentos] iniciar_agendamentos() chamado. Aguardando o bot ficar online...")

    async def _on_ready():
        _garantir_tarefa(bot)

    if not _listener_ok:
        bot.add_listener(_on_ready, "on_ready")
        _listener_ok = True
    if bot.is_ready():  # caso seja chamado depois do bot já estar online
        _garantir_tarefa(bot)


async def rodar_agendamentos(bot, chat_agendamentos=None, chats_logs=None) -> None:
    """
    Versão em corrotina, no mesmo estilo do antigo `iniciar_agendador`.
    Use do MESMO jeito que você já iniciava o sistema antigo, por exemplo:

        bot.loop.create_task(rodar_agendamentos(bot))
        # ou, dentro de uma função async (setup_hook / on_ready):
        asyncio.create_task(rodar_agendamentos(bot))
    """
    _configurar_ids(chat_agendamentos, chats_logs)
    print("[agendamentos] rodar_agendamentos() chamado.")
    await _loop(bot)