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
               'kt', 'maq', 'pringle', 'ruko', 'sam', 'shadow',
               'swampy', 'thunder', 'verley', 'yasu', 'yuna']

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
        regex = r"^(?P<result>W|w|L|l|T|t)\s+\[(?P<player1>\w+),\s+(?P<player2>\w+),\s+(?P<player3>\w+),\s+(?P<player4>\w+),\s+(?P<player5>\w+)\]$"
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
                    continue
                pairlist.append(f"{player_list[i].lower()} and {player_list[k].lower()}")
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
        date = datetime.fromtimestamp(int(time.time())).isoformat()
        team = match_list[1]
        our_shocks = int(match_list[2])
        their_shocks = int(match_list[3])
        return player, date, team, our_shocks, their_shocks

    @staticmethod
    def parse_all(arg: str) -> Tuple[str, str, str, str]:
        regex = (
            r'^(?P<result>W|w|L|l|T|t)\s+(?P<team>.+)\s+\[(?P<runner1>\w+),\s+(?P<runner2>\w+),\s+(?P<runner3>\w+),\s+(?P<runner4>\w+)\]\s+'
            r'\[(?P<score1>\d{2,3}),\s+(?P<score2>\d{2,3}),\s+(?P<score3>\d{2,3}),\s+(?P<score4>\d{2,3})\]\s+'
            r'(?P<bagger>\w+)\s+(?P<shocks_pulled>\d+)\s+(?P<opponent_shocks>\d+)$')
        match = re.match(regex, arg)
        if not match:
            raise commands.BadArgument

        result = match.group('result')
        team = match.group('team')
        runners = []
        scores = []
        for i in range(1, 5):
            runners.append(match.group(f"runner{i}"))
            scores.append(match.group(f"score{i}"))
        bagger = match.group('bagger')
        shocks_pulled = int(match.group('shocks_pulled'))
        opponent_shocks = int(match.group('opponent_shocks'))
        indiv_arg = f"{team} [{', '.join(runners)}] [{', '.join(scores)}]"
        pair_arg = f"{result} [{', '.join(runners)}, {bagger}]"
        bagger_arg = f"{bagger} {team} {shocks_pulled} {opponent_shocks}"
        war_arg = f"{team} {result}"
        return indiv_arg, pair_arg, bagger_arg, war_arg

    @commands.command(aliases=['gi'])
    @commands.guild_only()
    async def getindivs(self, ctx: discord.ext.commands.Context, player: str):
        """Retrieves indiv scores of a player. Argument should just be a player name."""
        player = player.lower()
        sql_string = """select I.Player, I.Date, I.Team, I.Score, W.Win, W.Loss
                        from IndivStats I, WarStats W
                        where Player=? and I.WarID = W.WarID
                        order by I.Date desc
                        limit 25"""

        self.cur.execute(sql_string, (player,))
        rows = self.cur.fetchall()

        if not rows:
            await ctx.channel.send("This player doesn't have any wars in the database.")
            return

        wins = 0
        losses = 0
        average = 0
        t = "Team"
        d = "Date"
        s = "Score"
        r = "Result"
        msg = f"```{player}'s indivs over the last {len(rows)} wars:\n\n"
        msg += f"{d:<13}|{t:^8}|{s:^8}|{r:^8}\n"
        msg += '-'*38 + '\n'

        for row in rows:
            average += row[3]
            wins += row[4]
            losses += row[5]
            truncated_date = row[1].split('T')[0]
            result = 'W' if row[4] else 'L' if row[5] else 'T'
            msg += f"{truncated_date:<13}|{row[2]:^8}|{row[3]:^8}|{result:^8}\n"

        msg.rstrip()
        average /= len(rows)
        msg += f"\n\nAverage: {average:.2f}\n"
        msg += f"W/L Ratio: {wins/(wins+losses):.2%}"
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

        sql_string = """select B.Player, B.Date, B.Team, B.OurShocks, B.TheirShocks, W.Win, W.Loss
                        from BaggerStats B, WarStats W
                        where Player=? AND B.WarID = W.WarID
                        order by B.Date desc
                        limit 25"""

        self.cur.execute(sql_string, (player,))
        rows = self.cur.fetchall()

        if not rows:
            await ctx.channel.send("This player doesn't have any bagger data in the database.")
            return

        wins = 0
        losses = 0
        total_wars = 0
        average = 0
        t = "Team"
        d = "Date"
        s = "Shocks"
        o = "Opponent Shocks"
        r = "Result"
        msg = f"```{player}'s bagging record over the last {len(rows)} wars (0-0 means count was unknown):\n\n"
        msg += f"{d:<13}|{t:^8}|{s:^10}|{o:^17}|{r:^8}\n"
        msg += '-' * 58 + '\n'

        for row in rows:
            truncated_date = row[1].split('T')[0]
            result = 'W' if row[5] else 'L' if row[6] else 'T'
            wins += row[5]
            losses += row[6]
            if row[3] != 0 and row[4] != 0:
                total_wars += 1
            average += row[3]
            msg += f"{truncated_date:<13}|{row[2]:^8}|{row[3]:^10}|{row[4]:^17}|{result:^8}\n"

        msg.rstrip()
        average /= total_wars
        msg += f"\n\nAverage: {average:.2f}\n"
        msg += f"W/L Ratio: {wins / (wins + losses):.2%}"
        msg += "```"
        await ctx.channel.send(msg)
        return

    @commands.command(aliases=['gw'])
    @commands.guild_only()
    async def getwars(self, ctx: discord.ext.commands.Context, team: str=None):
        """Gets the war record against a team. You can provide a tag, or no arguments to get the first 10 records."""
        if team:
            sql_string = """select Date, Team, Win, Loss, Tie, WarID
                            from WarStats WS
                            where WS.Team=?
                            order by Date desc"""
            self.cur.execute(sql_string, (team,))
        else:
            sql_string = """select Date, Team, Win, Loss, Tie, WarID
                            from WarStats WS
                            order by Date desc
                            limit 25"""
            self.cur.execute(sql_string)

        rows = self.cur.fetchall()
        if not rows:
            await ctx.channel.send("No record found.")
            return

        wins = 0
        losses = 0
        ties = 0
        w = "War ID"
        d = "Date"
        t = "Team"
        res = "Result"
        msg = f"```Record vs {team}:\n\n" if team else f"```Latest records:\n\n"
        msg += f"{w:<10}|{d:^15}|{t:^9}|{res:^8}\n"
        msg += '-' * 42 + '\n'

        for row in rows:
            result = 'W' if row[2] else 'L' if row[3] else 'T'
            wins += row[2]
            losses += row[3]
            ties += row[4]
            truncated_date = row[0].split('T')[0]
            msg += f"{row[5]:<10}|{truncated_date:^15}|{row[1]:^9}|{result:^8}\n"

        msg += '\n'
        msg += f"Record: {wins} - {ties} - {losses}\n"
        msg += f"W/L Ratio: {wins/(wins+losses):.2%}"
        msg += "```"
        await ctx.channel.send(msg)
        return

    @commands.command(aliases=['ui'])
    @commands.guild_only()
    @commands.max_concurrency(1)
    @commands.has_role('Reporter')
    async def updateindivs(self, ctx: discord.ext.commands.Context, war_id: int, *, arg: str):
        """Updates the indiv database. Arguments should be <war_id> <opposing team tag> [<runner1>, <runner2>, <runner3>, <runner4>] [<score1>, <score2>, <score3>, <score4>]"""
        parsed = self.parse_ui(arg)
        msg = f"```Runner Scores vs {parsed['opposing_team']}\n\n"
        for key in parsed:
            if key == 'opposing_team':
                continue
            msg += f"{key:<12}{parsed[key]:>12}\n"
        msg.strip()
        msg += '```'
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
                date = datetime.fromtimestamp(int(time.time())).isoformat()
                self.cur.execute("""INSERT INTO IndivStats VALUES (?, ?, ?, ?, ?);""", (war_id, key, date, parsed['opposing_team'], parsed[key]))
            self.con.commit()
            await ctx.channel.send('Updated.')
        except asyncio.TimeoutError:
            pass

    @commands.command(aliases=['up'])
    @commands.guild_only()
    @commands.max_concurrency(1)
    @commands.has_role('Reporter')
    async def updatepairs(self, ctx: discord.ext.commands.Context, *, arg: str):
        """Updates the pair database. This is only for MKPS players. Arguments should be W/L/T [<player1>, <player2>, <player3>, <player4>, <player5>]"""
        (result, pairs) = self.parse_pairs(arg)
        msg = f"This will be reported as a **win** with these pairs. Is that okay? (y/n)" if result.lower() == 'w' \
            else f"This will be reported as a **loss** with these pairs. Is that okay? (y/n)" if result.lower() == 'l' \
            else f"This will be reported as a **tie** with these pairs. Is that okay? (y/n)"
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
            elif result.lower() == 'l':
                sql_string = """update PairStats
                                set Losses = Losses + 1
                                where Pair = ?"""
                for pair in pairs:
                    self.cur.execute(sql_string, (pair,))
            else:
                sql_string = """update PairStats
                                set Ties = Ties + 1
                                where Pair = ?"""
                for pair in pairs:
                    self.cur.execute(sql_string, (pair,))
            self.con.commit()
            await ctx.channel.send('Updated.')
        except asyncio.TimeoutError:
            pass

    @commands.command(aliases=['ub'])
    @commands.guild_only()
    @commands.max_concurrency(1)
    @commands.has_role('Reporter')
    async def updatebaggers(self, ctx: discord.ext.commands.Context, war_id: int, *, arg: str):
        """Updates the bagger database. Arguments should be <war_id> <bagger name> <team> <shocks obtained> <opponent shocks obtained>"""
        (player, date, team, our_shocks, their_shocks) = self.parse_bagger(arg)
        if player not in Stats.PLAYERS:
            await ctx.channel.send(f"{player} isn't in the roster. Ignoring...")
            return

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
                            values (?, ?, ?, ?, ?, ?)"""
            self.cur.execute(sql_string, (war_id, player, date, team, our_shocks, their_shocks))
            self.con.commit()
            await ctx.channel.send("Updated.")
        except asyncio.TimeoutError:
            pass

    @commands.command(aliases=['uw'])
    @commands.guild_only()
    @commands.max_concurrency(1)
    @commands.has_role('Reporter')
    async def updatewars(self, ctx: discord.ext.commands.Context, *, arg: str) -> int:
        """Updates the war record. Syntax is <opposing_team_tag> <W/L/T>"""
        regex = r"(?P<team>\S+)\s+(?P<result>W|w|L|l|T|t)"
        match = re.match(regex, arg)
        if not match:
            raise commands.BadArgument
        team = match.group('team')
        result = match.group('result')

        msg = f"This will be reported as a **win** against {team}. Is that okay? (y/n)" if result.lower() == 'w' \
              else f"This will be reported as a **loss** against {team}. Is that okay? (y/n)" if result.lower() == 'l' \
              else f"This will be reported as a **tie** against {team}. Is that okay? (y/n)"
        await ctx.channel.send(msg)

        def check(m: discord.Message):
            return (m.author == ctx.author) and (m.content == 'y' or m.content == 'Y' or m.content == 'n' or m.content == 'N')
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30.0)
            if msg.content.lower() == 'n':
                await ctx.channel.send('Ok, ignoring...')
                return -1
            await ctx.channel.send('Ok, updating...')
            sql_string = """insert into WarStats(Team, Date, Win, Loss, Tie) 
                            values(?, ?, ?, ?, ?)"""
            date = datetime.fromtimestamp(int(time.time())).isoformat()
            if result.lower() == 'w':
                self.cur.execute(sql_string, (team, date, 1, 0, 0))
            elif result.lower() == 'l':
                self.cur.execute(sql_string, (team, date, 0, 1, 0))
            else:
                self.cur.execute(sql_string, (team, date, 0, 0, 1))
            self.con.commit()
            self.cur.execute("select max(WarID) from WarStats")
            row = self.cur.fetchone()
            await ctx.channel.send('Updated')
            return row[0]
        except asyncio.TimeoutError:
            pass

    @commands.command(aliases=['ua'])
    @commands.guild_only()
    @commands.max_concurrency(1)
    @commands.has_role('Reporter')
    async def updateall(self, ctx: discord.ext.commands.Context, *, arg: str):
        """Updates everything at once. Syntax is complex. Check https://github.com/akyuus/FlanBot for an example."""
        (indiv_arg, pair_arg, bagger_arg, war_arg) = self.parse_all(arg)
        war_id = await self.updatewars(ctx, arg=war_arg)
        await self.updateindivs(ctx, war_id=war_id, arg=indiv_arg)
        await self.updatepairs(ctx, arg=pair_arg)
        await self.updatebaggers(ctx, war_id=war_id, arg=bagger_arg)
        return


#    @commands.command(aliases=['init_w'])
#    @commands.guild_only()
#    @commands.has_role('Reporter')
#    async def initialize_wars(self, ctx):
#        """Initializes the war database. This is just for prototyping."""
#        update_string = """update WarStats
#                           set Win = 1
#                               Loss = 0
#                               Tie = 0"""
#        self.cur.execute(update_string)
#        self.con.commit()

    @commands.command(aliases=['init'])
    @commands.guild_only()
    @commands.has_role('Reporter')
    async def initialize_pairs(self, ctx):
        """Initializes any new pairs in the database."""
        check_string = """select 1
                          from PairStats
                          where Pair = ?"""
        insert_string = """insert into PairStats
                           values (?, ?, ?, ?)"""
        pairlist = []
        for i in range(len(Stats.PLAYERS)):
            for k in range(i+1, len(Stats.PLAYERS)):
                pairlist.append(f"{Stats.PLAYERS[i]} and {Stats.PLAYERS[k]}")

        await ctx.channel.send('Updating pair database...')
        for pair in pairlist:
            self.cur.execute(check_string, (pair,))
            check = self.cur.fetchall()
            if not check:
                self.cur.execute(insert_string, (pair, 0, 0, 0))
        self.con.commit()
        await ctx.channel.send('Done.')


def setup(bot: commands.Bot):
    bot.add_cog(Stats(bot))
