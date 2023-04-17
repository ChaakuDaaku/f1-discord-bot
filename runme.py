import os
import json
from os.path import join, dirname
from datetime import datetime, timezone
from dotenv import load_dotenv

import discord
import discord.ext.commands as commands
import discord.ext.tasks as tasks
from discord import SelectOption, Interaction, PartialEmoji
from discord.ui import View, Select
from icalendar import Calendar, Event
from typing import List, Optional

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

#Calendar dict to sort the mess
f1_calendar = {}
with open('./data/Formula_1.ics', 'r', encoding="utf-8") as F1_CAL:
    cal: Calendar = Calendar.from_ical(F1_CAL.read())
    wknd_event: Event
    for wknd_event in cal.walk('VEVENT'):
        loc, typ = wknd_event['SUMMARY'].split(' - ')
        tim:datetime = wknd_event['DTSTART'].dt
        loc:str = loc[2:].strip().title()
        typ:str = typ.strip()
        if typ in ['Practice 1', 'Qualifying']:
            if loc not in f1_calendar:
                f1_calendar[loc] = {typ:tim}
            else:
                f1_calendar[loc][typ] = tim

events : List[str] = []
bot_start : List[datetime] = []
view_end  : List[datetime] = []
for loc in f1_calendar:
    events.append(loc)
    bot_start.append(f1_calendar[loc]['Practice 1'])
    view_end.append(f1_calendar[loc]['Qualifying'])
bot_start_dates = [day.date() for day in bot_start]


#Driver dict
with open('./data/drivers.json') as d_json:
    drivers = json.load(d_json)

#Player dict
with open('./data/player_map.json') as pm_json:
    poll_results = json.load(pm_json)

class DriverSelect(Select):
    def __init__(self, *, custom_id: str = ..., placeholder: Optional[str] = None, min_values: int = 1, max_values: int = 1, options: List[SelectOption] = ..., disabled: bool = False, row: Optional[int] = None) -> None:

        super().__init__(
            custom_id=custom_id,
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            options=options,
            disabled=disabled,
            row=row
        )
        self.custom_id = custom_id
        self.placeholder = placeholder
        self.min_values = min_values
        self.max_values = max_values
        self.options = options
        self.disabled = disabled
        self.row = row

    async def callback(self, interaction: Interaction) -> None:
        assert self.view is not None
        user_id = interaction.user.id
        user_name = interaction.user.name
        position = interaction.data['custom_id']
        driver = interaction.data['values'][0]
        print(f'{user_name} chose {driver} for {position}')
        poll_results[str(user_id)]["predictions"][position] = driver
        # await asyncio.sleep(1)
        # await interaction.response.send_message(content=f'You chose {driver} for {position}', ephemeral=True)
        await interaction.response.defer(ephemeral=True)


class PollView(View):
    def __init__(self, *, timeout: Optional[float] = 180, drivers):
        super().__init__(timeout=timeout)
        self.driver_options = [self.option_gen(driver) for driver in drivers]
        self.add_item(DriverSelect(custom_id='P1', placeholder='Predict P1', min_values=1, max_values=1, options=self.driver_options, disabled=False, row=0))
        self.add_item(DriverSelect(custom_id='P2', placeholder='Predict P2', min_values=1, max_values=1, options=self.driver_options, disabled=False, row=1))
        self.add_item(DriverSelect(custom_id='P3', placeholder='Predict P3', min_values=1, max_values=1, options=self.driver_options, disabled=False, row=2))
        self.add_item(DriverSelect(custom_id='P4', placeholder='Predict P4', min_values=1, max_values=1, options=self.driver_options, disabled=False, row=3))
        self.add_item(DriverSelect(custom_id='P5', placeholder='Predict P5', min_values=1, max_values=1, options=self.driver_options, disabled=False, row=4))

    def option_gen(self, driver) -> SelectOption:
        return SelectOption(label=driver["name"], value=driver["name"], emoji=PartialEmoji.from_str(driver["emocode"]))

    async def on_timeout(self) -> None:
        print("View Timeout")
        self.stop()
        selects: DriverSelect
        for selects in self.children:
            selects.disabled = True
            print(selects.disabled)
        print(poll_results)
        with open('./poll_results.json', 'w') as f:
            json.dump(poll_results, f)
        return await super().on_timeout()

class F1PollBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        intents.message_content = True
        self.command_prefix = '!'
        super().__init__(command_prefix=self.command_prefix, intents=intents)

    async def on_ready(self):
        await self.add_cog(Poller(self))
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')


class Poller(commands.Cog):
    def __init__(self, bot:F1PollBot):
        super().__init__()
        self.bot = bot
        self.time = datetime.now(timezone.utc).time()
        self.date = datetime.now(timezone.utc).date()
        self.channel = self.bot.get_channel(int(os.environ.get("CHANNEL_ID")))
        # self.guild: Guild = self.bot.guilds[0]
        # self.emojis = self.guild.emojis[:10:-1]
        self.event = str('')
        self.message_sent = False
        self.poll_task.start()

    def cog_unload(self) -> None:
        self.poll_task.cancel()

    @tasks.loop(seconds=10, reconnect=True)
    async def poll_task(self):
        print("Understood! We are checking...")
        self.date = datetime.now(timezone.utc).date()
        self.time = datetime.now(timezone.utc).time()
        if self.date not in bot_start_dates:
            print(f'No rawe ceek!')
            return
        else:
            for i, dt in enumerate(bot_start):
                if self.date == dt.date():
                    if self.time < dt.time():
                        print(f'Not time yet. Poll starting at {dt.time()}')
                        self.poll_task.change_interval(time=dt.time())
                        return
                    elif (self.time < view_end[i].time()) and not self.message_sent:
                        assert self.channel is not None
                        print("Time for predictions!")
                        self.event = events[i]
                        self.duration: float = (view_end[i] - bot_start[i]).total_seconds()
                        print(f"Predictions closing in {self.duration} seconds")
                        self.poll_view = PollView(timeout=self.duration, drivers=drivers)
                        self.poll_task.change_interval(time=view_end[i].time())
                        self.message_sent = True
                        break
                    elif datetime.now(timezone.utc) > view_end[i]:
                        await self.poll_view.on_timeout()
                        self.message_sent = False
                        self.poll_task.change_interval(seconds=10)
            if self.message_sent:
                await self.channel.send(content=f'{self.event} - Predictions', view=self.poll_view)
        return


bot = F1PollBot()
bot.run(os.environ.get("BOT_TOKEN"))
