"""
Ação: DELETAR_THREAD  (também aceita o apelido APAGAR_THREAD)

Apaga uma thread no horário agendado. Só pede um campo: Link.

Formato:
    AGENDAR: DELETAR_THREAD
    QUANDO: 18/11/2026 20:57
    Se_passar: Prosseguir
    Link: https://discord.com/channels/123456789012345678/987654321098765432

Para pegar o link: botão direito na thread -> "Copiar link da thread".
(Link de uma mensagem dentro da thread também funciona.)
"""
import re

import discord

_LINK_RE = re.compile(
    r"https?://(?:\w+\.)?discord(?:app)?\.com/channels/(\d+)/(\d+)(?:/\d+)?",
    re.IGNORECASE,
)


async def _resolver_thread(bot, dados):
    """Retorna (thread, erro). Se der certo, erro é None."""
    link = dados["campos"].get("LINK", "")
    m = _LINK_RE.search(link)
    if not m:
        return None, (
            "Campo `Link` ausente ou inválido. "
            "Use `Link: https://discord.com/channels/<servidor>/<thread>`."
        )

    guild_id, thread_id = int(m.group(1)), int(m.group(2))

    try:
        canal = bot.get_channel(thread_id) or await bot.fetch_channel(thread_id)
    except discord.NotFound:
        return None, "Thread não encontrada (talvez já tenha sido apagada)."
    except discord.Forbidden:
        return None, "O bot não tem acesso a essa thread."
    except discord.HTTPException as e:
        return None, f"Não foi possível consultar a thread: {e}"

    if not isinstance(canal, discord.Thread):
        return None, "O link não aponta para uma thread (parece ser um canal comum)."

    if canal.guild.id != guild_id:
        return None, "O servidor do link não corresponde ao da thread."

    # O bot precisa de "Gerenciar Tópicos" (a menos que a thread seja dele).
    if canal.owner_id != bot.user.id:
        if not canal.permissions_for(canal.guild.me).manage_threads:
            return None, "O bot não tem a permissão **Gerenciar Tópicos** nessa thread."

    return canal, None


async def executar(bot, dados, validar=False):
    thread, erro = await _resolver_thread(bot, dados)

    if validar:
        return erro  # None = formato correto

    if erro:
        raise RuntimeError(erro)

    autor = dados["autor"]
    await thread.delete(reason=f"Agendamento de {autor} ({autor.id})")