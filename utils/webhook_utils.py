import re
import discord

NOME_WEBHOOK_PADRAO = "Espelho"
_cache_webhooks: dict[int, discord.Webhook] = {}


def limpar_nome(nome: str | None) -> str:
    """O Discord recusa nomes de webhook com 'discord' ou 'clyde' e limita a 80 caracteres."""
    nome = (nome or "").strip() or "Usuário"
    nome = re.sub(
        r"(?i)(discord|clyde)",
        lambda m: m.group(0)[0] + "\u200b" + m.group(0)[1:],
        nome,
    )
    return nome[:80]


async def obter_webhook(bot, canal, nome: str = NOME_WEBHOOK_PADRAO) -> discord.Webhook:
    """Pega (ou cria) um webhook CRIADO PELO BOT no canal.
    Só webhooks criados pelo bot conseguem enviar botões."""
    if isinstance(canal, discord.Thread):
        canal = canal.parent

    if canal.id in _cache_webhooks:
        return _cache_webhooks[canal.id]

    webhook = None
    for w in await canal.webhooks():
        if w.user and w.user.id == bot.user.id and w.token:
            webhook = w
            break

    if webhook is None:
        webhook = await canal.create_webhook(name=nome)

    _cache_webhooks[canal.id] = webhook
    return webhook


async def enviar_como_autor(
    bot,
    destino,
    autor: discord.abc.User,
    *,
    content: str | None = None,
    embeds: list[discord.Embed] | None = None,
    files: list[discord.File] | None = None,
    view: discord.ui.View | None = None,
) -> discord.WebhookMessage:
    """Envia uma mensagem em `destino` (canal ou thread) com o nome (apelido) e a foto de `autor`."""
    thread = destino if isinstance(destino, discord.Thread) else None

    if thread and thread.archived:
        await thread.edit(archived=False)

    webhook = await obter_webhook(bot, destino)

    kwargs = dict(
        username=limpar_nome(autor.display_name),
        avatar_url=autor.display_avatar.url,
        allowed_mentions=discord.AllowedMentions.none(),
        wait=True,
    )
    if content:
        kwargs["content"] = content
    if embeds:
        kwargs["embeds"] = embeds
    if files:
        kwargs["files"] = files
    if view:
        kwargs["view"] = view
    if thread:
        kwargs["thread"] = thread

    try:
        return await webhook.send(**kwargs)
    except discord.NotFound:
        # webhook apagado: limpa o cache para ser recriado na próxima vez
        _cache_webhooks.pop(webhook.channel_id, None)
        raise