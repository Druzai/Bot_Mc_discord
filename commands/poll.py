from asyncio import sleep as asleep
from datetime import datetime
from enum import Enum, auto

from discord import Color, Embed
from discord.ext import commands

from components.localization import get_translation
from config.init_config import Config


class Poll(commands.Cog):
    _polls = {}
    _emoji_symbols = {"yes": "☑", "no": "❎"}
    _await_date = {}

    def __init__(self, bot: commands.Bot):
        self._bot: commands.Bot = bot

    def add_awaiting_command(self, command: str):
        self._await_date[command] = datetime.now()

    async def run(self, ctx, message: str, command: str, need_for_voting=2, needed_role=None,
                  timeout=60 * 60, remove_logs_after=None):
        start_msg = await ctx.send("@everyone, " + message + " " +
                                   get_translation("To win the poll needed {0} votes!").format(str(need_for_voting)))
        poll_msg = await self.make_embed(ctx)
        current_poll = Poll.PollContent(ctx, command, need_for_voting, needed_role, remove_logs_after)
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
            await ctx.send("`" + get_translation("Poll result: canceled!") + "`", delete_after=remove_logs_after)
            return
        poll_res = get_translation("granted") if current_poll.state == \
                                                 Poll.States.GRANTED else get_translation("refused")
        await ctx.send("`" + get_translation("Poll result: permission {0}!").format(poll_res) + "`",
                       delete_after=remove_logs_after)
        return current_poll.state == Poll.States.GRANTED

    async def make_embed(self, ctx):
        emb = Embed(title=get_translation("Survey. Voting!"),
                    color=Color.orange())
        emb.add_field(name=get_translation("yes"), value=self._emoji_symbols.get("yes"))
        emb.add_field(name=get_translation("no"), value=self._emoji_symbols.get("no"))
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
        emoji = self._emoji_symbols["yes"] if payload.emoji.name == \
                                              self._emoji_symbols["yes"] else self._emoji_symbols["no"]
        if payload.emoji.name not in self._emoji_symbols.values() \
                or not await current_poll.count_add_voice(channel, payload.member, emoji,
                                                          payload.emoji.name == self._emoji_symbols["yes"]):
            message = await channel.fetch_message(payload.message_id)
            await message.remove_reaction(payload.emoji, payload.member)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.message_id not in self._polls or payload.user_id == self._bot.user.id:
            return
        current_poll = self._polls[payload.message_id]
        if payload.emoji.name not in [v for k, v in current_poll.poll_voted_uniq.items() if k == payload.user_id]:
            return
        channel = self._bot.get_channel(payload.channel_id)
        member = await self._bot.guilds[0].fetch_member(payload.user_id)
        await current_poll.count_del_voice(channel, member, payload.emoji.name == self._emoji_symbols["yes"])

    async def timer(self, ctx, seconds: int, command: str):
        if (datetime.now() - self._await_date[command]).seconds > seconds:  # Starting a poll
            self._await_date[command] = datetime.now()
            return True
        else:
            await ctx.send(f"{ctx.author.mention}, " +
                           get_translation("what are you doing? Time hasn't passed yet. Waiting {0} sec...")
                           .format((datetime.now() - self._await_date[command]).seconds),
                           delete_after=Config.get_awaiting_times_settings().await_seconds_before_message_deletion)
            return False

    def get_polls(self):
        return self._polls

    class States(Enum):
        NONE = auto()
        GRANTED = auto()
        REFUSED = auto()
        CANCELED = auto()

    class PollContent:
        def __init__(self, ctx, command: str, need_for_voting=2, needed_role=None, remove_logs_after=0):
            self.poll_yes = 0
            self.poll_no = 0
            self.poll_voted_uniq = {}
            self.ctx = ctx
            self.NFW = need_for_voting
            self.NR = needed_role
            self.RLA = remove_logs_after
            self.state = Poll.States.NONE
            self.command = command

        async def count_add_voice(self, channel, user, emoji, to_left):
            if self.state is not Poll.States.NONE:
                await channel.send(f"{user.mention}, " + get_translation("poll've already finished!"),
                                   delete_after=self.RLA)
                return False
            if user.id in self.poll_voted_uniq.keys():
                await channel.send(f"{user.mention}, " + get_translation("you've already voted!"),
                                   delete_after=self.RLA)
                return False
            if self.NR and self.NR not in (e.name for e in user.roles):
                await channel.send(f"{user.mention}, " +
                                   get_translation("you don't have needed '{0}' role").format(self.NR),
                                   delete_after=self.RLA)
                return False
            self.poll_voted_uniq.update({user.id: emoji})
            if to_left:
                self.poll_yes += 1
            else:
                self.poll_no += 1
            if self.poll_yes >= self.NFW:
                self.state = Poll.States.GRANTED
            elif self.poll_no >= self.NFW:
                self.state = Poll.States.REFUSED
            return True

        async def count_del_voice(self, channel, user, to_left):
            if self.state is not Poll.States.NONE:
                await channel.send(f"{user.mention}, " + get_translation("poll've already finished!"),
                                   delete_after=self.RLA)
                return
            if self.NR and self.NR not in (e.name for e in user.roles):
                await channel.send(f"{user.mention}, " +
                                   get_translation("you don't have needed '{0}' role").format(self.NR),
                                   delete_after=self.RLA)
                return
            self.poll_voted_uniq.pop(user.id)
            if to_left:
                self.poll_yes -= 1
            else:
                self.poll_no -= 1

        def cancel(self):
            self.state = Poll.States.CANCELED
