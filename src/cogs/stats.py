import discord
import sqlite3
import re
import asyncio
import time
from typing import Tuple
from datetime import datetime
from discord.ext import commands


class Stats(commands.Cog):

    PLAYERS = ['adam', 'ais', 'chilly', 'chris', 'fred',
               'fusion', 'jazz', 'josh', 'jsully', 'kenzo',
               'kt', 'maq', 'pringle', 'sam', 'shadow', 'swampy',
               'thunder', 'verley', 'yasu', 'yuna']

    def __init__(self, bot):
        self.bot = bot
        self.con = sqlite3.connect(r'C:\Users\akyuu\PycharmProjects\SakuraStatistics\sakura.db')
        self.cur = self.con.cursor()

    @staticmethod
    def parse_ui(input: str) -> dict:
        parsed = {}
        regex = r"^(?P<team>.+)\s+\[(?P<runner1>\w+),*\s*(?P<runner2>\w+)*,*\s*(?P<runner3>\w+)*,*\s*(?P<runner4>\w+)*\]\s+\[(?P<score1>\d{2,3}),*\s*(?P<score2>\d{2,3})*,*\s*(?P<score3>\d{2,3})*,*\s*(?P<score4>\d{2,3})*\]$"
        match = re.match(regex, input)
        if not match:
            raise commands.BadArgument

        parsed['opposing_team'] = match.group('team')
        for i in range(1, 5):
            if match.group(f'runner{i}') is None:
                break
            if match.group(f'score{i}') is None:
                raise commands.BadArgument

            parsed[f"{match.group(f'runner{i}').lower()}"] = int(match.group(f'score{i}'))

        return parsed

    @staticmethod
    def parse_pairs(input: str) -> Tuple[str, list]:
        pairlist = []
        regex = r"^(?P<result>W|w|L|l)\s+\[(?P<player1>\w+),\s+(?P<player2>\w+),\s+(?P<player3>\w+),\s+(?P<player4>\w+),\s+(?P<player5>\w+)\]$"
        match_list = re.findall(regex, input)
        if not match_list:
            raise commands.BadArgument
        else:
            match_list = list(match_list[0])

        result = match_list[0]
        player_list = match_list[1:]
        player_list.sort()
        for i in range(len(player_list)):
            for k in range(i+1,len(player_list)):
                if player_list[i].lower() not in Stats.PLAYERS or player_list[k].lower() not in Stats.PLAYERS:
                    raise commands.BadArgument
                pairlist.append(f"{player_list[i]} and {player_list[k]}")
        print(pairlist)
        return result, pairlist

    @staticmethod
    def parse_bagger(input: str) -> Tuple[str, str, str, int, int]:
        regex = r"^(\w+)\s+(\S+)\s+(\d+)\s+(\d+)$"
        match_list = re.findall(regex, input)
        if not match_list:
            raise commands.BadArgument
        else:
            match_list = list(match_list[0])

        player = match_list[0].lower()
        if player not in Stats.PLAYERS:
            raise commands.BadArgument
        date = datetime.fromtimestamp(int(time.time())).isoformat()
        team = match_list[1]
        our_shocks = int(match_list[2])
        their_shocks = int(match_list[3])
        return player, date, team, our_shocks, their_shocks

    @commands.command(aliases=['gi'])
    @commands.guild_only()
    async def getindivs(self, ctx: discord.ext.commands.Context, player: str):
        """Retrieves indiv scores of a player. Argument should just be a player name."""
        if player.lower() not in Stats.PLAYERS:
            await ctx.channel.send(f"{player} is not in the roster.")
            return

        sql_string = """select *
                        from IndivStats 
                        where Player=?
                        limit 10"""

        self.cur.execute(sql_string, (player,))
        rows = self.cur.fetchall()

        if not rows:
            await ctx.channel.send("This player doesn't have any wars in the database.")
            return

        t = "Team"
        d = "Date"
        s = "Score"
        msg = f"```{player}'s indivs over the last {len(rows)} wars:\n\n"
        msg += f"{d:<13}|{t:^8}|{s:^8}\n"
        msg += '-'*29 + '\n'

        for row in rows:
            truncated_date = row[1].split('T')[0]
            msg += f"{truncated_date:<13}|{row[2]:^8}|{row[3]:^8}\n"

        msg.rstrip()
        msg += "```"
        await ctx.channel.send(msg)
        return

    @commands.command(aliases=['gp'])
    @commands.guild_only()
    async def getpairs(self, ctx: discord.ext.commands.Context, player1: str, player2: str):
        """Retrieves pair data for two players. Argument should be two players in the roster."""
        player1 = player1.lower()
        player2 = player2.lower()
        if player2 < player1:
            tmp = player2
            player2 = player1
            player1 = tmp

        pair = f"{player1} and {player2}"
        if player1 not in Stats.PLAYERS or player2 not in Stats.PLAYERS:
            await ctx.channel.send(f"One or more of these players is not in the roster.")
            return

        sql_string = """select Wins, Losses, (Wins*1.0/(Wins+Losses))
                        from PairStats 
                        where Pair=? and Wins+Losses != 0"""

        self.cur.execute(sql_string, (pair,))
        rows = self.cur.fetchall()

        if not rows:
            await ctx.channel.send("These players do not have a recorded war in the database.")
            return

        w = "Wins"
        l = "Losses"
        r = "W/L Ratio"
        msg = f"```{pair}'s stats:\n\n"
        msg += f"{w:<6}|{l:^12}|{r:^12}\n"
        msg += '-' * 30 + '\n'

        for row in rows:
            msg += f"{row[0]:<6}|{row[1]:^12}|{row[2]:^12.2%}\n"

        msg.rstrip()
        msg += "```"
        await ctx.channel.send(msg)
        return

    @commands.command(aliases=['gb'])
    @commands.guild_only()
    async def getbagger(self, ctx: discord.ext.commands.Context, player: str):
        """Retrieves bagger scores of a player. Argument should just be a player name."""
        if player.lower() not in Stats.PLAYERS:
            await ctx.channel.send(f"{player} is not in the roster.")
            return

        sql_string = """select *
                        from BaggerStats 
                        where Player=?
                        limit 10"""

        self.cur.execute(sql_string, (player,))
        rows = self.cur.fetchall()

        if not rows:
            await ctx.channel.send("This player doesn't have any bagger data in the database.")
            return

        t = "Team"
        d = "Date"
        s = "Shocks"
        o = "Opponent Shocks"
        msg = f"```{player}'s bagging record over the last {len(rows)} wars:\n\n"
        msg += f"{d:<13}|{t:^8}|{s:^14}|{o:^20}\n"
        msg += '-' * 61 + '\n'

        for row in rows:
            truncated_date = row[1].split('T')[0]
            msg += f"{truncated_date:<13}|{row[2]:^8}|{row[3]:^14}|{row[4]:^20}\n"

        msg.rstrip()
        msg += "```"
        await ctx.channel.send(msg)
        return

    @commands.command(aliases=['ui'])
    @commands.guild_only()
    @commands.has_role('Reporter')
    async def updateindivs(self, ctx: discord.ext.commands.Context, *, arg: str):
        """Updates the indiv database. Arguments should be <opposing team tag> [<runner1>, <runner2>, <runner3>, <runner4>] [<score1>, <score2>, <score3>, <score4>]"""
        parsed = self.parse_ui(arg)
        msg = f"**Runner Scores vs {parsed['opposing_team']}**\n\n"
        for key in parsed:
            if key == 'opposing_team':
                continue
            msg += f"**{key+':':<15} **{parsed[key]:>3}\n"
        msg.strip()
        await ctx.channel.send(msg)
        await ctx.channel.send('Does this information look correct? (y/n)')

        def check(m: discord.Message):
            return (m.author == ctx.author) and (m.content == 'y' or m.content == 'Y' or m.content == 'n' or m.content == 'N')

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30.0)
            if msg.content.lower() == 'n':
                await ctx.channel.send('Ok, ignoring...')
                return
            await ctx.channel.send("Ok, updating...")
            for key in parsed:
                if key == 'opposing_team':
                    continue
                if key not in Stats.PLAYERS:
                    await ctx.channel.send(f"{key} is not in the roster. Ignoring...")
                    continue
                date = datetime.fromtimestamp(int(time.time())).isoformat()
                self.cur.execute("""INSERT INTO IndivStats VALUES (?, ?, ?, ?);""", (key, date, parsed['opposing_team'], parsed[key]))
            self.con.commit()
            await ctx.channel.send('Updated.')
        except asyncio.TimeoutError:
            pass

    @commands.command(aliases=['up'])
    @commands.guild_only()
    @commands.has_role('Reporter')
    async def updatepairs(self, ctx: discord.ext.commands.Context, *, arg: str):
        """Updates the pair database. This is only for MKPS players. Arguments should be W (or L) [<player1>, <player2>, <player3>, <player4>, <player5>]"""
        (result, pairs) = self.parse_pairs(arg)
        msg = "This will be reported as a **win**. Is that okay? (y/n)" if result.lower() == 'w' else "This will be reported as a **loss**. Is that okay? (y/n)"
        await ctx.channel.send(msg)

        def check(m: discord.Message):
            return (m.author == ctx.author) and (m.content == 'y' or m.content == 'Y' or m.content == 'n' or m.content == 'N')

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30.0)
            if msg.content.lower() == 'n':
                await ctx.channel.send('Ok, ignoring...')
                return
            await ctx.channel.send("Ok, updating...")
            if result.lower() == 'w':
                sql_string = """update PairStats
                                set Wins = Wins + 1
                                where Pair = ?"""
                for pair in pairs:
                    self.cur.execute(sql_string, (pair,))
            else:
                sql_string = """update PairStats
                                set Losses = Losses + 1
                                where Pair = ?"""
                for pair in pairs:
                    self.cur.execute(sql_string, (pair,))
            self.con.commit()
            await ctx.channel.send('Updated.')
        except asyncio.TimeoutError:
            pass

    @commands.command(aliases=['ub'])
    @commands.guild_only()
    @commands.has_role('Reporter')
    async def updatebaggers(self, ctx: discord.ext.commands.Context, *, arg: str):
        """Updates the bagger database. Arguments should be <bagger name> <team> <shocks obtained> <opponent shocks obtained>"""
        (player, date, team, our_shocks, their_shocks) = self.parse_bagger(arg)
        msg = f"{player}'s shock count vs {team} this war was {our_shocks}-{their_shocks}. Does that sound correct? (y/n)"
        await ctx.channel.send(msg)

        def check(m: discord.Message):
            return (m.author == ctx.author) and (m.content == 'y' or m.content == 'Y' or m.content == 'n' or m.content == 'N')
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30.0)
            if msg.content.lower() == 'n':
                await ctx.channel.send('Ok, ignoring...')
                return
            await ctx.channel.send('Ok, updating...')
            sql_string = """insert into BaggerStats
                            values (?, ?, ?, ?, ?)"""
            self.cur.execute(sql_string, (player, date, team, our_shocks, their_shocks))
            self.con.commit()
            await ctx.channel.send("Updated.")
        except asyncio.TimeoutError:
            pass


    @commands.command(aliases=['init'])
    @commands.guild_only()
    @commands.has_role('Reporter')
    async def initialize_pairs(self, ctx):
        """Initializes any new pairs in the database."""
        check_string = """select 1
                          from PairStats
                          where Pair = ?"""
        insert_string = """insert into PairStats
                           values (?, ?, ?)"""
        pairlist = []
        for i in range(len(Stats.PLAYERS)):
            for k in range(i+1, len(Stats.PLAYERS)):
                pairlist.append(f"{Stats.PLAYERS[i]} and {Stats.PLAYERS[k]}")

        await ctx.channel.send('Updating pair database...')
        for pair in pairlist:
            self.cur.execute(check_string, (pair,))
            check = self.cur.fetchall()
            if not check:
                self.cur.execute(insert_string, (pair, 0, 0))
        self.con.commit()
        await ctx.channel.send('Done.')


def setup(bot: commands.Bot):
    bot.add_cog(Stats(bot))
