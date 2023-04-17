import os
import json
from os.path import join, dirname
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

import discord
import discord.ext.commands as commands
import discord.ext.tasks as tasks
from discord import SelectOption, Interaction, PartialEmoji, Message
from discord.ui import View, Select
from icalendar import Calendar, Event
from typing import List, Optional, Dict, TypedDict

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

#Calendar dict to sort the mess
f1_calendar:Dict[str, Dict[str, datetime]] = {}
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

bot_start_dates = [f1_calendar[loc]['Practice 1'].date() for loc in f1_calendar]

#Driver dict
drivers : List[Dict[str,str]]
with open('./data/drivers.json') as d_json:
    drivers = json.load(d_json)


class PollResults(TypedDict):
    username: str
    sheetName: str
    predictions: Dict[str, str]


#Player dict
poll_results : Dict[str, PollResults]
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
        await interaction.response.send_message(content=f'You chose {driver} for {position}', ephemeral=True)
        # await interaction.response.defer(ephemeral=True)


class PollView(View):
    def __init__(self, *, timeout: Optional[float] = 180, drivers):
        super().__init__(timeout=timeout)
        self.message = None
        self.driver_options = [self.option_gen(driver) for driver in drivers]
        self.add_item(DriverSelect(custom_id='P1', placeholder='Predict P1', min_values=1, max_values=1, options=self.driver_options, disabled=False, row=0)) \
            .add_item(DriverSelect(custom_id='P2', placeholder='Predict P2', min_values=1, max_values=1, options=self.driver_options, disabled=False, row=1)) \
            .add_item(DriverSelect(custom_id='P3', placeholder='Predict P3', min_values=1, max_values=1, options=self.driver_options, disabled=False, row=2)) \
            .add_item(DriverSelect(custom_id='P4', placeholder='Predict P4', min_values=1, max_values=1, options=self.driver_options, disabled=False, row=3)) \
            .add_item(DriverSelect(custom_id='P5', placeholder='Predict P5', min_values=1, max_values=1, options=self.driver_options, disabled=False, row=4))

    def option_gen(self, driver) -> SelectOption:
        return SelectOption(label=driver["name"], value=driver["name"], emoji=PartialEmoji.from_str(driver["emocode"]))

    def get_message(self, message: Message, loc: str):
        self.loc = loc
        self.message = message

    async def on_timeout(self) -> None:
        print("View Timeout")
        self.stop()
        selects: DriverSelect
        for selects in self.children:
            selects.disabled = True
        print(poll_results)
        await self.message.edit(content=(loc+' - Predictions Closed'), view=self)
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
        self.event = ''
        self.message_sent = False
        self.poll_view = PollView(drivers=drivers)
        self.poll_task.start()

    def cog_unload(self) -> None:
        self.poll_task.cancel()

    def is_weekend(self) -> bool:
        self.date = datetime.now(timezone.utc).date()
        if self.date not in bot_start_dates:
            print(f'No FP1 today')
            return False
        else:
            return True

    def get_datetimes(self) -> str:
        for loc in f1_calendar:
            if self.date == f1_calendar[loc]['Practice 1'].date():
                print(f'Race weekend at {loc}')
                self.loc = loc
                self.fp1_dt = f1_calendar[loc]['Practice 1']
                self.qlf_dt = f1_calendar[loc]['Qualifying']
                self.poll_view.timeout = (self.qlf_dt - self.fp1_dt).total_seconds()
                return 'FP1'
            else:
                return 'Not found'

    @tasks.loop(seconds=10, reconnect=True)
    async def poll_task(self):
        print("task loop started")
        if not self.is_weekend():
            return
        if self.event == '':
            print('Fresh bot. Who dis.')
            self.event = self.get_datetimes()
        elif self.event == 'Quali' and datetime.now(timezone.utc) > (f1_calendar[self.loc]['Qualifying'] + timedelta(days=3)):
            print('Prime the bot for next event')
            self.event = self.get_datetimes()
        elif self.event == 'Not found':
            print('Bot start date found but rest of the data missing??')
            return
        self.time = datetime.now(timezone.utc).time()
        if self.time < self.fp1_dt.time():
            print(f'Not time yet, starting poll at {self.fp1_dt.time()}')
            self.poll_task.change_interval(time=self.fp1_dt.time())
            return
        elif self.time > self.qlf_dt.time() and self.date == f1_calendar[loc]['Practice 1'].date():
            print(f'Quali ends next day at {self.qlf_dt.time()}')
            self.poll_task.change_interval(time=self.qlf_dt.time())
            return
        elif not self.message_sent and self.event == 'FP1':
            print("Time for predictions!")
            self.message_sent = True
            self.poll_task.change_interval(time=self.qlf_dt.time())
            self.message = await self.channel.send(content=f'{self.loc} - Predictions Open', view=self.poll_view)
            self.poll_view.get_message(self.message, self.loc)
            return
        elif datetime.now(timezone.utc) > f1_calendar[self.loc]['Qualifying'] and self.event == 'FP1':
            print('Quali started. Poll Closed.')
            await self.poll_view.on_timeout()
            self.message_sent = False
            self.event = 'Quali'
            self.poll_task.change_interval(seconds=10)
            return
        else:
            print('Bot sleeping')
            return


bot = F1PollBot()
bot.run(os.environ.get("BOT_TOKEN"))
