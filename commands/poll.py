from asyncio import sleep as asleep
from datetime import datetime
from enum import Enum, auto

from discord import Color, Embed
from discord.ext import commands


class Poll(commands.Cog):
    _polls = {}
    _emoji_symbols = {"yes": "☑", "no": "❎"}
    _await_date = datetime.now()

    def __init__(self, bot):
        # Для работы с сообщениями, сообщения, которые выводить при опросе, минимальное кол-во проголосовавших за или против
        # Сделать временное голосование, по истечении голосование завершено неудачей, cancel работает так же,
        self._bot = bot

    # TODO: Make it usable with stop command, give to command some strings!
    async def run(self, ctx, need_for_voting=2, needed_role=None, timeout=60 * 60, remove_logs_after=None):
        start_msg = await ctx.send("@everyone, this man " + ctx.author.mention +
                                   " trying to delete some history of this channel. Will you let that happen?" +
                                   f" To win the poll need {str(need_for_voting)} votes! So keep it up! I'm waiting")
        poll_msg = await self.make_embed(ctx)
        current_poll = Poll.PollContent(ctx, need_for_voting, needed_role, remove_logs_after)
        self._polls[poll_msg.id] = current_poll
        seconds = 0
        while current_poll.state == Poll.States.NONE:
            await asleep(1)
            seconds += 1
            if timeout <= seconds:
                current_poll.cancel()
        await start_msg.delete()
        await poll_msg.delete()
        del self._polls[poll_msg.id]
        if current_poll.state == Poll.States.CANCELED:
            await ctx.send("Poll result: canceled!", delete_after=remove_logs_after)
            return None
        await ctx.send("Poll result: permission " +
                       ("granted" if current_poll.state == Poll.States.GRANTED else "refused") + "!",
                       delete_after=remove_logs_after)
        return current_poll.state == Poll.States.GRANTED

    async def make_embed(self, ctx):
        emb = Embed(title='Опрос. ГолосовалОЧКА!',
                    color=Color.orange())
        emb.add_field(name='yes', value=':ballot_box_with_check:')
        emb.add_field(name='no', value=':negative_squared_cross_mark:')
        add_reactions_to = await ctx.send(embed=emb)
        for emote in self._emoji_symbols.values():
            await add_reactions_to.add_reaction(emote)
        return add_reactions_to

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.message_id not in self._polls or payload.member.id == self._bot.user.id:
            return
        channel = self._bot.get_channel(payload.channel_id)
        current_poll = self._polls[payload.message_id]
        if payload.emoji.name not in self._emoji_symbols.values() \
                or not await current_poll.count_voice(channel, payload.member,
                                                      payload.emoji.name == self._emoji_symbols["yes"]):
            message = await channel.fetch_message(payload.message_id)
            await message.remove_reaction(payload.emoji, payload.member)

    async def timer(self, ctx, seconds: int):
        if (datetime.now() - self._await_date).seconds > seconds:  # Starting a poll
            self._await_date = datetime.now()
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
        def __init__(self, ctx, need_for_voting=2, needed_role=None, remove_logs_after=0):
            self.poll_yes = 0
            self.poll_no = 0
            self.poll_voted_uniq = set()
            self.ctx = ctx
            self.NFW = need_for_voting
            self.NR = needed_role
            self.RLA = remove_logs_after
            self.state = Poll.States.NONE

        async def count_voice(self, channel, user, to_left):
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
            if to_left:
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
