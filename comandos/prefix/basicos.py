from config.versao import VERSAO_ATUAL


def registrar_comandos_basicos(bot):
    # Comando ;ping
    @bot.command()
    async def ping(ctx):
        await ctx.send(f"""Pong!
-# Focus {VERSAO_ATUAL}""")

    # Comando ;help
    @bot.command()
    async def help(ctx):
        await ctx.send("Não tem comando de help.")

    # Comando ;ração
    @bot.command()
    async def ração(ctx):
        await ctx.send("https://klipy.com/gifs/cat-1282")

    # Comando ;gosminha
    @bot.command()
    async def gosminha(ctx):
        await ctx.send("https://tenor.com/view/black-slime-stim-oddly-satisfying-gif-gif-12598525")

    # Comando ;jeftoide
    @bot.command()
    async def jeftoide(ctx):
        await ctx.send("Papai")
