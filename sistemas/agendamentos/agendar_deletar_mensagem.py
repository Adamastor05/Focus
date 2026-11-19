"""
Ação: DELETAR_MENSAGEM  (também aceita o apelido APAGAR_MENSAGEM)

Apaga uma mensagem no horário agendado. Só pede um campo: Link.

Formato:
    AGENDAR: DELETAR_MENSAGEM
    QUANDO: 18/11/2026 20:57
    Motivo: Mensagem com informação desatualizada
    Se_passar: Prosseguir
    Link: https://discord.com/channels/123456789012345678/987654321098765432/111222333444555666

Para pegar o link: botão direito na mensagem -> "Copiar link da mensagem".
(Mensagens dentro de threads também funcionam.)
"""
import re

import discord

_LINK_RE = re.compile(
    r"https?://(?:\w+\.)?discord(?:app)?\.com/channels/(\d+)/(\d+)/(\d+)",
    re.IGNORECASE,
)


async def _resolver_mensagem(bot, dados):
    """Retorna (mensagem, erro). Se der certo, erro é None."""
    link = dados["campos"].get("LINK", "")
    m = _LINK_RE.search(link)
    if not m:
        return None, (
            "Campo `Link` ausente ou inválido. Use o link de uma **mensagem** "
            "(botão direito na mensagem > Copiar link da mensagem)."
        )

    guild_id, canal_id, mensagem_id = (int(g) for g in m.groups())

    try:
        canal = bot.get_channel(canal_id) or await bot.fetch_channel(canal_id)
    except discord.NotFound:
        return None, "Canal da mensagem não encontrado."
    except discord.Forbidden:
        return None, "O bot não tem acesso ao canal dessa mensagem."
    except discord.HTTPException as e:
        return None, f"Não foi possível consultar o canal: {e}"

    if not hasattr(canal, "fetch_message"):
        return None, "O link não aponta para um canal de texto ou thread."

    guild = getattr(canal, "guild", None)
    if guild is None or guild.id != guild_id:
        return None, "O servidor do link não corresponde ao do canal."

    try:
        alvo = await canal.fetch_message(mensagem_id)
    except discord.NotFound:
        return None, "Mensagem não encontrada (talvez já tenha sido apagada)."
    except discord.Forbidden:
        return None, "O bot não tem permissão para ler essa mensagem."
    except discord.HTTPException as e:
        return None, f"Não foi possível consultar a mensagem: {e}"

    # Para apagar mensagens de outras pessoas, o bot precisa de "Gerenciar Mensagens".
    if alvo.author.id != bot.user.id:
        if not canal.permissions_for(guild.me).manage_messages:
            return None, "O bot não tem a permissão **Gerenciar Mensagens** nesse canal."

    return alvo, None


async def executar(bot, dados, validar=False):
    alvo, erro = await _resolver_mensagem(bot, dados)

    if validar:
        return erro  # None = formato correto

    if erro:
        raise RuntimeError(erro)

    local = getattr(alvo.channel, "mention", None) or f"`{alvo.channel.id}`"
    await alvo.delete()

    # Aparece como "Resultado" no log de execuções.
    return f"Mensagem de {alvo.author} (`{alvo.author.id}`) em {local} apagada."