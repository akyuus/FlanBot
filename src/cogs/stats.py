import discord
import sqlite3
import re
import asyncio
import time
import json
from typing import Tuple
from datetime import datetime
from discord.ext import commands


class Stats(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.connections = {}
        self.players = {}
        self.refresh_fields()

    def refresh_fields(self):
        with open(r'C:\Users\akyuu\PycharmProjects\SakuraStatistics\src\cogs\teams.json') as f:
            team_data = json.load(f)
        for key in team_data:
            self.connections[int(key)] = sqlite3.connect(team_data[key]['connection_string'])
            self.players[int(key)] = team_data[key]['players']

    @staticmethod
    def add_check(message):
        return lambda reaction, user: user == message.author and (str(reaction.emoji) == '➡' or str(reaction.emoji) == '⬅')

    @staticmethod
    def remove_check(message):
        return lambda reaction, user : user == message.author and str(reaction.emoji) == '⬅'

    @staticmethod
    def parse_ui(arg: str) -> dict:
        parsed = {}
        regex = r"^(?P<team>.+)\s+\[(?P<runner1>\w+),*\s*(?P<runner2>\w+)*,*\s*(?P<runner3>\w+)*,*\s*(?P<runner4>\w+)*\]\s+\[(?P<score1>\d{2,3}),*\s*(?P<score2>\d{2,3})*,*\s*(?P<score3>\d{2,3})*,*\s*(?P<score4>\d{2,3})*\]$"
        match = re.match(regex, arg)
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

    def parse_pairs(self, arg: str, id: int) -> Tuple[str, list]:
        pairlist = []
        regex = r"^(?P<result>W|w|L|l|T|t)\s+\[(?P<player1>\w+),\s+(?P<player2>\w+),\s+(?P<player3>\w+),\s+(?P<player4>\w+),\s+(?P<player5>\w+)\]$"
        match_list = re.findall(regex, arg)
        if not match_list:
            raise commands.BadArgument
        else:
            match_list = list(match_list[0])

        result = match_list[0]
        player_list = match_list[1:]
        player_list.sort()
        for i in range(len(player_list)):
            for k in range(i+1,len(player_list)):
                if player_list[i].lower() not in self.players[id] or player_list[k].lower() not in self.players[id]:
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
            r'(?P<bagger>\w+)\s+(?P<shocks_pulled>\d+)\s+(?P<opponent_shocks>\d+)\s*(?P<mkps>(?<=\s)mkps)?$')
        match = re.match(regex, arg)
        if not match:
            raise commands.BadArgument

        result = match.group('result')
        team = match.group('team')
        mkps = match.group('mkps')
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
        if mkps:
            war_arg += f" {mkps}"
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
                        """
        aggregate_string = """select (SUM(Score)*1.0)/COUNT(*) as average, SUM(W.Win) as Wins, SUM(W.Loss) as Losses
                              from IndivStats I, WarStats W
                              where Player=? and I.WarID = W.WarID
                              order by I.Date desc"""

        con = self.connections[ctx.guild.id]
        cur = con.cursor()
        cur.execute(sql_string, (player,))
        rows = cur.fetchall()

        if not rows:
            await ctx.channel.send("This player doesn't have any wars in the database.")
            return

        cur.execute(aggregate_string, (player,))
        aggregate = cur.fetchall()[0]
        wins = aggregate[1]
        losses = aggregate[2]
        average = aggregate[0]

        t = "Team"
        d = "Date"
        s = "Score"
        r = "Result"
        msg = f"```{player}'s indivs over the last {len(rows)} wars:\n\n"
        msg += f"{d:<13}|{t:^8}|{s:^8}|{r:^8}\n"
        msg += '-'*38 + '\n'
        msg_header = (msg + '.')[:-1]
        page_num = 0
        page = rows[25*page_num:25*(page_num + 1)]
        for row in page:
            truncated_date = row[1].split('T')[0]
            result = 'W' if row[4] else 'L' if row[5] else 'T'
            msg += f"{truncated_date:<13}|{row[2]:^8}|{row[3]:^8}|{result:^8}\n"

        msg.rstrip()
        msg += f"\n\nAverage: {average:.2f}\n"
        msg += f"W/L Ratio: {wins/(wins+losses):.2%}"
        msg += "```"
        sent_msg = await ctx.channel.send(msg)
        await sent_msg.add_reaction("⬅")
        await sent_msg.add_reaction("➡")

        while True:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=10.0, check=self.add_check(ctx.message))
            except asyncio.TimeoutError:
                break
            else:
                pages = len(rows)//25
                if str(reaction.emoji) == '➡':
                    page_num = min(page_num+1, pages)
                else:
                    page_num = max(page_num-1, 0)
                print(page_num)
                msg = msg_header
                page = rows[25 * page_num:25 * (page_num + 1)]
                if len(page) == 0:
                    continue
                for row in page:
                    truncated_date = row[1].split('T')[0]
                    result = 'W' if row[4] else 'L' if row[5] else 'T'
                    msg += f"{truncated_date:<13}|{row[2]:^8}|{row[3]:^8}|{result:^8}\n"

                msg.rstrip()
                msg += f"\n\nAverage: {average:.2f}\n"
                msg += f"W/L Ratio: {wins / (wins + losses):.2%}"
                msg += "```"
                await sent_msg.edit(content=msg)
        return

    @commands.command(aliases=['gp'])
    @commands.guild_only()
    async def getpairs(self, ctx: discord.ext.commands.Context, player1: str, player2: str):
        """Retrieves pair data for two players. Argument should be two players in the roster."""
        roster = self.players[ctx.guild.id]
        player1 = player1.lower()
        player2 = player2.lower()
        if player2 < player1:
            tmp = player2
            player2 = player1
            player1 = tmp

        pair = f"{player1} and {player2}"

        # there has to be a better way to do this lmao
        sql_string = """select IFNULL(INDIV.Player1, BAGGER.Player1) as P1, IFNULL(BAGGER.Player2, INDIV.PLAYER2) as P2, (SUM(IFNULL(INDIV.Wins, 0)) + SUM(IFNULL(BAGGER.Wins, 0))) as Wins, (SUM(IFNULL(INDIV.Losses, 0)) + SUM(IFNULL(BAGGER.Losses, 0))) as Losses, (((SUM(IFNULL(INDIV.Wins, 0)) + SUM(IFNULL(BAGGER.Wins, 0)))*1.0)/(SUM(IFNULL(INDIV.Wins, 0)) + SUM(IFNULL(BAGGER.Wins, 0)) + SUM(IFNULL(INDIV.Losses, 0)) + SUM(IFNULL(BAGGER.Losses, 0)))) as WL
                        from
                        (select I1.Player as Player1, I2.Player as Player2, SUM(WS.Win) as Wins, SUM(WS.Loss) as Losses, (Sum(WS.Win)*1.0)/(Sum(WS.Loss) + Sum(WS.Win)) as WL
                        from (select WarID, Player, IFNULL(Score, 0) from IndivStats where Player = ?) I1,
                        (select WarID, Player, IFNULL(Score, 0) from IndivStats where Player = ?) I2,
                        WarStats WS
                        WHERE I1.WarID = I2.WarID AND I1.WarID = WS.WarID) INDIV,
                        (select I1.Player as Player1, I2.Player as Player2, SUM(WS.Win) as Wins, SUM(WS.Loss) as Losses, (Sum(WS.Win)*1.0)/(Sum(WS.Loss) + Sum(WS.Win)) as WL
                        from (select * from IndivStats where Player = ? OR Player = ?) I1,
                        (select * from BaggerStats where Player = ? OR Player = ?) I2,
                        WarStats WS
                        WHERE I1.WarID = I2.WarID AND I1.WarID = WS.WarID) BAGGER"""

        con = self.connections[ctx.guild.id]
        cur = con.cursor()
        cur.execute(sql_string, (player1, player2, player1, player2, player1, player2))
        rows = cur.fetchall()

        if rows[0][0] is None:
            await ctx.channel.send("These players do not have a recorded war in the database.")
            return

        w = "Wins"
        l = "Losses"
        r = "W/L Ratio"
        msg = f"```{pair}'s stats:\n\n"
        msg += f"{w:<6}|{l:^12}|{r:^12}\n"
        msg += '-' * 30 + '\n'

        for row in rows:
            msg += f"{row[2]:<6}|{row[3]:^12}|{row[4]:^12.2%}\n"

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
                        """

        con = self.connections[ctx.guild.id]
        cur = con.cursor()
        cur.execute(sql_string, (player.lower(),))
        rows = cur.fetchall()

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
        msg_header = (msg + '.')[:-1]

        #this is just to get the wins/losses/average correct
        for row in rows:
            wins += row[5]
            losses += row[6]
            if row[3] != 0 or row[4] != 0:
                total_wars += 1
            average += row[3]

        page_num = 0
        page = rows[25 * page_num:25 * (page_num + 1)]
        for row in page:
            truncated_date = row[1].split('T')[0]
            result = 'W' if row[5] else 'L' if row[6] else 'T'
            msg += f"{truncated_date:<13}|{row[2]:^8}|{row[3]:^10}|{row[4]:^17}|{result:^8}\n"

        msg.rstrip()

        try:
            average /= total_wars
        except ZeroDivisionError:
            average = 0
            pass
        msg += f"\n\nAverage: {average:.2f}\n"
        msg += f"W/L Ratio: {wins / (wins + losses):.2%}"
        msg += "```"
        sent_msg = await ctx.channel.send(msg)
        await sent_msg.add_reaction("⬅")
        await sent_msg.add_reaction("➡")

        while True:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=10.0,
                                                         check=self.add_check(ctx.message))
            except asyncio.TimeoutError:
                break
            else:
                pages = len(rows)//25
                if str(reaction.emoji) == '➡':
                    page_num = min(page_num + 1, pages)
                else:
                    page_num = max(page_num - 1, 0)
                msg = msg_header
                page = rows[25 * page_num:25 * (page_num + 1)]
                if len(page) == 0:
                    continue
                for row in page:
                    truncated_date = row[1].split('T')[0]
                    result = 'W' if row[5] else 'L' if row[6] else 'T'
                    msg += f"{truncated_date:<13}|{row[2]:^8}|{row[3]:^10}|{row[4]:^17}|{result:^8}\n"

                msg.rstrip()
                msg += f"\n\nAverage: {average:.2f}\n"
                msg += f"W/L Ratio: {wins / (wins + losses):.2%}"
                msg += "```"
                await sent_msg.edit(content=msg)
        return

    @commands.command(aliases=['gw'])
    @commands.guild_only()
    async def getwars(self, ctx: discord.ext.commands.Context, team: str=None):
        """Gets the war record against a team. You can provide a tag, or no arguments to get the first 10 records."""
        con = self.connections[ctx.guild.id]
        cur = con.cursor()
        if team:
            sql_string = """select Date, Team, Win, Loss, Tie, WarID, MKPS
                            from WarStats WS
                            where WS.Team=?
                            order by Date desc"""
            cur.execute(sql_string, (team,))
        else:
            sql_string = """select Date, Team, Win, Loss, Tie, WarID, MKPS
                            from WarStats WS
                            order by Date desc
                            """
            cur.execute(sql_string)

        rows = cur.fetchall()
        if not rows:
            await ctx.channel.send("No record found.")
            return

        wins = 0
        losses = 0
        ties = 0
        w = "War ID"
        d = "Date"
        t = "Team"
        m = "MKPS?"
        res = "Result"
        msg = f"```Record vs {team}:\n\n" if team else f"```Latest records:\n\n"
        msg += f"{w:<10}|{d:^15}|{t:^9}|{res:^8}|{m:^8}\n"
        msg += '-' * 52 + '\n'
        msg_header = (msg + '.')[:-1]

        #just to get the stats
        for row in rows:
            wins += row[2]
            losses += row[3]
            ties += row[4]

        page_num = 0
        page = rows[25 * page_num:25 * (page_num + 1)]
        for row in page:
            result = 'W' if row[2] else 'L' if row[3] else 'T'
            truncated_date = row[0].split('T')[0]
            mkps = 'Yes' if row[6] else 'No'
            msg += f"{row[5]:<10}|{truncated_date:^15}|{row[1]:^9}|{result:^8}|{mkps:^8}\n"

        msg += '\n'
        msg += f"Record: {wins} - {ties} - {losses}\n"
        msg += f"W/L Ratio: {wins/(wins+losses):.2%}"
        msg += "```"
        sent_msg = await ctx.channel.send(msg)
        await sent_msg.add_reaction("⬅")
        await sent_msg.add_reaction("➡")

        while True:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=10.0,
                                                         check=self.add_check(ctx.message))
            except asyncio.TimeoutError:
                break
            else:
                pages = len(rows) // 25
                if str(reaction.emoji) == '➡':
                    page_num = min(page_num + 1, pages)
                else:
                    page_num = max(page_num - 1, 0)
                print(page_num)
                msg = msg_header
                page = rows[25 * page_num:25 * (page_num + 1)]
                if len(page) == 0:
                    continue
                for row in page:
                    result = 'W' if row[2] else 'L' if row[3] else 'T'
                    truncated_date = row[0].split('T')[0]
                    mkps = 'Yes' if row[6] else 'No'
                    msg += f"{row[5]:<10}|{truncated_date:^15}|{row[1]:^9}|{result:^8}|{mkps:^8}\n"

                msg += '\n'
                msg += f"Record: {wins} - {ties} - {losses}\n"
                msg += f"W/L Ratio: {wins / (wins + losses):.2%}"
                msg += "```"
                await sent_msg.edit(content=msg)
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
            con = self.connections[ctx.guild.id]
            cur = con.cursor()
            for key in parsed:
                if key == 'opposing_team':
                    continue
                date = datetime.fromtimestamp(int(time.time())).isoformat()
                cur.execute("""INSERT INTO IndivStats VALUES (?, ?, ?, ?, ?);""", (war_id, key, date, parsed['opposing_team'], parsed[key]))
            con.commit()
            await ctx.channel.send('Updated.')
        except asyncio.TimeoutError:
            pass

    @commands.command(aliases=['up'])
    @commands.guild_only()
    @commands.max_concurrency(1)
    @commands.has_role('Reporter')
    async def updatepairs(self, ctx: discord.ext.commands.Context, *, arg: str):
        """Updates the pair database. This is only for MKPS players. Arguments should be W/L/T [<player1>, <player2>, <player3>, <player4>, <player5>]"""
        (result, pairs) = self.parse_pairs(arg, ctx.guild.id)
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
            con = self.connections[ctx.guild.id]
            cur = con.cursor()
            if result.lower() == 'w':
                sql_string = """update PairStats
                                set Wins = Wins + 1
                                where Pair = ?"""
                for pair in pairs:
                    cur.execute(sql_string, (pair,))
            elif result.lower() == 'l':
                sql_string = """update PairStats
                                set Losses = Losses + 1
                                where Pair = ?"""
                for pair in pairs:
                    cur.execute(sql_string, (pair,))
            else:
                sql_string = """update PairStats
                                set Ties = Ties + 1
                                where Pair = ?"""
                for pair in pairs:
                    cur.execute(sql_string, (pair,))
            con.commit()
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
            con = self.connections[ctx.guild.id]
            cur = con.cursor()
            cur.execute(sql_string, (war_id, player, date, team, our_shocks, their_shocks))
            con.commit()
            await ctx.channel.send("Updated.")
        except asyncio.TimeoutError:
            pass

    @commands.command(aliases=['uw'])
    @commands.guild_only()
    @commands.max_concurrency(1)
    @commands.has_role('Reporter')
    async def updatewars(self, ctx: discord.ext.commands.Context, *, arg: str) -> int:
        """Updates the war record. Syntax is <opposing_team_tag> <W/L/T>"""
        regex = r"(?P<team>\S+)\s+(?P<result>W|w|L|l|T|t)\s*(?P<mkps>(?<=\s)mkps)?"
        match = re.match(regex, arg)
        if not match:
            raise commands.BadArgument
        team = match.group('team')
        result = match.group('result')
        mkps = match.group('mkps')
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
            con = self.connections[ctx.guild.id]
            cur = con.cursor()
            sql_string = """insert into WarStats(Team, Date, Win, Loss, Tie) 
                            values(?, ?, ?, ?, ?)"""
            date = datetime.fromtimestamp(int(time.time())).isoformat()
            if result.lower() == 'w':
                cur.execute(sql_string, (team, date, 1, 0, 0))
            elif result.lower() == 'l':
                cur.execute(sql_string, (team, date, 0, 1, 0))
            else:
                cur.execute(sql_string, (team, date, 0, 0, 1))
            con.commit()
            cur.execute("select max(WarID) from WarStats")
            row = cur.fetchone()
            if mkps:
                await ctx.channel.send("This will be marked as an MKPS match.")
                cur.execute("update WarStats set MKPS=? where WarID=?", (1, row[0]))
                con.commit()
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
    async def initialize_pairs(self, ctx: discord.ext.commands.Context):
        """Initializes any new pairs in the database."""
        check_string = """select 1
                          from PairStats
                          where Pair = ?"""
        insert_string = """insert into PairStats
                           values (?, ?, ?, ?)"""
        pairlist = []
        self.refresh_fields()
        roster = self.players[ctx.guild.id]
        for i in range(len(roster)):
            for k in range(i+1, len(roster)):
                pairlist.append(f"{roster[i]} and {roster[k]}")

        print(pairlist)
        await ctx.channel.send('Updating pair database...')
        con = self.connections[ctx.guild.id]
        cur = con.cursor()
        for pair in pairlist:
            cur.execute(check_string, (pair,))
            check = cur.fetchall()
            if not check:
                cur.execute(insert_string, (pair, 0, 0, 0))
        con.commit()
        await ctx.channel.send('Done.')


def setup(bot: commands.Bot):
    bot.add_cog(Stats(bot))
