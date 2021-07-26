from asyncio import sleep as asleep
from datetime import datetime
from enum import Enum, auto

from discord import Color, Embed
from discord.ext import commands


class Poll(commands.Cog):
    polls = {}
    symbols = {"yes": "☑", "no": "❎"}
    await_date = datetime.now()

    def __init__(self, bot):
        # Для работы с сообщениями, сообщения, которые выводить при опросе, минимальное кол-во проголосовавших за или против
        # Сделать временное голосование, по истечении голосование завершено неудачей, cancel работает так же,
        self.__bot = bot

    # TODO: Make it useable with stop command, give to command some strings!
    async def run(self, ctx, needForVoting=2, neededRole=None, timeout=60 * 60, remove_logs_after=None):
        start_msg = await ctx.send("@everyone, this man " + ctx.author.mention +
                                   " trying to delete some history of this channel. Will you let that happen?" +
                                   " To win the poll need " + str(needForVoting) + " votes! So keep it up! I'm waiting")
        poll_msg = await self.makeEmb(ctx)
        currentPoll = Poll.PollContent(ctx, needForVoting, neededRole, remove_logs_after)
        self.polls[poll_msg.id] = currentPoll
        seconds = 0
        while currentPoll.state == Poll.States.NONE:
            await asleep(1)
            seconds += 1
            if timeout <= seconds:
                currentPoll.cancel()
        await start_msg.delete()
        await poll_msg.delete()
        del self.polls[poll_msg.id]
        if currentPoll.state == Poll.States.CANCELED:
            await ctx.send("Poll result: canceled!", delete_after=remove_logs_after)
            return None
        await ctx.send("Poll result: permission " +
                       ("granted" if currentPoll.state == Poll.States.GRANTED else "refused") + "!",
                       delete_after=remove_logs_after)
        return currentPoll.state == Poll.States.GRANTED

    async def makeEmb(self, ctx):
        emb = Embed(title='Опрос. ГолосовалОЧКА!',
                    color=Color.orange())
        emb.add_field(name='yes', value=':ballot_box_with_check:')
        emb.add_field(name='no', value=':negative_squared_cross_mark:')
        add_reactions_to = await ctx.send(embed=emb)
        await add_reactions_to.add_reaction(self.symbols["yes"])
        await add_reactions_to.add_reaction(self.symbols["no"])
        return add_reactions_to

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.message_id not in self.polls or payload.member.id == self.__bot.user.id:
            return
        channel = self.__bot.get_channel(payload.channel_id)
        currentPoll = self.polls[payload.message_id]
        if payload.emoji.name not in self.symbols.values() \
                or not await currentPoll.count_voice(channel, payload.member, payload.emoji.name == self.symbols["yes"]):
            message = await channel.fetch_message(payload.message_id)
            await message.remove_reaction(payload.emoji, payload.member)

    async def timer(self, ctx, seconds: int):
        if (datetime.now() - self.await_date).seconds > seconds:  # Starting a poll
            self.await_date = datetime.now()
            return True
        else:
            await ctx.send(ctx.author.mention + ", what are you doing? Time hasn't passed yet. I have " + str(seconds) +
                           " sec/s timer! Waiting...")
            return False

    class States(Enum):
        NONE = auto()
        GRANTED = auto()
        REFUSED = auto()
        CANCELED = auto()

    class PollContent:
        def __init__(self, ctx, needForVoting=2, neededRole=None, remove_logs_after=0):
            self.poll_yes = 0
            self.poll_no = 0
            self.poll_voted_uniq = set()
            self.ctx = ctx
            self.NFW = needForVoting
            self.NR = neededRole
            self.RLA = remove_logs_after
            self.state = Poll.States.NONE

        async def count_voice(self, channel, user, toLeft):
            if self.state is not Poll.States.NONE:
                await channel.send(user.mention + ", poll've already finished!", delete_after=self.RLA)
                return False
            if user.id in self.poll_voted_uniq:
                await channel.send(user.mention + ", you've already voted!", delete_after=self.RLA)
                return False
            if self.NR and self.NR not in (e.name for e in user.roles):
                await channel.send(user.mention + ", you don't have needed '" + self.NR + "' role",
                                   delete_after=self.RLA)
                return False
            self.poll_voted_uniq.add(user.id)
            if toLeft:
                self.poll_yes += 1
            else:
                self.poll_no += 1
            if self.poll_yes >= self.NFW:
                self.state = Poll.States.GRANTED
            elif self.poll_no >= self.NFW:
                self.state = Poll.States.REFUSED
            return True

        def cancel(self):
            self.state = Poll.States.CANCELED
