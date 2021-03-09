import discord
from discord.ext import commands
from decouple import config


bot = commands.Bot(command_prefix='~', description='Statistics bot for SA.')
extensions = ['cogs.stats']
token = config('BOT_TOKEN')

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    for extension in extensions:
        bot.load_extension(extension)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    await bot.change_presence(activity=discord.Game("with apples"))

@bot.event
async def on_command_error(ctx, error: discord.ext.commands.CommandError):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await(await ctx.send("Your command is missing an argument: `%s`" %
                       str(error.param))).delete(delay=10)
        return
    if isinstance(error, commands.CommandOnCooldown):
        await(await ctx.send("This command is on cooldown; try again in %.0fs"
                       % error.retry_after)).delete(delay=5)
        return
    if isinstance(error, commands.MissingRole):
        await ctx.send(f"You need the following role to use this command: {error.missing_role}")
        return
    if isinstance(error, commands.BadArgument):
        await ctx.send("Malformed arguments. Try the help command if you're not sure what to do.")
        return
    if isinstance(error, commands.BotMissingPermissions):
        await ctx.send(f"I need the following permissions to use this command: {', '.join(error.missing_perms)}")
        return
    if isinstance(error, commands.NoPrivateMessage):
        await(await ctx.send("You can't use this command in DMs!")).delete(delay=5)
        return
    raise error

bot.run(token, bot=True, reconnect=True)
