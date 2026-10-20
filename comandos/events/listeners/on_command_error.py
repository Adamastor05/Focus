from discord.ext import commands


def registrar_evento_on_command_error(bot):
    @bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return

        raise error
