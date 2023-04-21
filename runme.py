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
from typing import List, Optional, Dict

import points_calculator

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

#Player dict
with open('./data/player_map.json') as pm_json:
    player_map = json.load(pm_json)

#Race result map
with open('./data/race_result_map.json') as rrm_json:
    race_result_map = json.load(rrm_json)

#Poll result data store
with open('./data/race_data_store.json') as rds_json:
    rds = json.load(rds_json)


class DriverSelect(Select):
    def __init__(self, *, custom_id: str = ...,
                 placeholder: Optional[str] = None, 
                 min_values: int = 1, 
                 max_values: int = 1, 
                 options: List[SelectOption] = ..., 
                 disabled: bool = False, 
                 row: Optional[int] = None) -> None:

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
        print(f'{user_name} chose {driver} for P{int(position) + 1}')
        race_result_map[str(user_id)][int(position)] = driver
        await interaction.response.defer(ephemeral=True)


class PollView(View):
    def __init__(self, *, timeout: Optional[float] = 180, drivers):
        super().__init__(timeout=timeout)
        self.message = None
        self.driver_options = [self.option_gen(driver) for driver in drivers]
        for i in range(5):
            self.add_item(DriverSelect(custom_id=f'{i}', placeholder=f'Predict P{i+1}' , min_values=1, max_values=1, options=self.driver_options, disabled=False, row=i))

    def option_gen(self, driver) -> SelectOption:
        return SelectOption(label=driver["name"], value=driver["name"], emoji=PartialEmoji.from_str(driver["emocode"]))

    def get_message(self, message: Message, loc: str):
        self.loc = loc
        self.message = message

    async def on_timeout(self, poll_results) -> None:
        print("View Timeout")
        self.stop()
        selects: DriverSelect
        for selects in self.children:
            selects.disabled = True
        print(poll_results)
        await self.message.edit(content=(loc+' - Predictions Closed'), view=self)
        with open('./data/race_data_store.json', 'w') as f:
            rds.append(poll_results)
            json.dump(rds, f)
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
        return 'Not found'

    @tasks.loop(seconds=10, reconnect=True)
    async def poll_task(self):
        print("task loop started")
        if (not self.is_weekend()):
            return
        if (self.event == ''):
            print('Fresh bot. Who dis.')
            self.event = self.get_datetimes()
            print("Found datetimes")
        elif (self.event == 'Quali') and (datetime.now(timezone.utc) > (self.qlf_dt + timedelta(days=3))):
            print('Prime the bot for next event')
            self.event = self.get_datetimes()
        elif (self.event == 'Not found'):
            print('Bot start date found but rest of the data missing??')
            return
        self.time = datetime.now(timezone.utc).time()
        if (self.time < self.fp1_dt.time()):
            print(f'Not time yet, starting poll at {self.fp1_dt.time()}')
            self.poll_task.change_interval(time=self.fp1_dt.time())
            return
        elif (self.time > self.qlf_dt.time()) and (datetime.now(timezone.utc) < self.qlf_dt):
            print(f'Quali ends next day at {self.qlf_dt.time()}')
            return
        elif (not self.message_sent) and (self.event == 'FP1'):
            print("Time for predictions!")
            self.poll_results = { self.loc : race_result_map}
            self.message_sent = True
            self.poll_task.change_interval(seconds=10)
            self.message = await self.channel.send(content=f'{self.loc} - Predictions Open @everyone', view=self.poll_view)
            self.poll_view.get_message(self.message, self.loc)
            return
        elif (datetime.now(timezone.utc) > self.qlf_dt) and (self.event == 'FP1'):
            print('Quali started. Poll Closed.')
            await self.poll_view.on_timeout(self.poll_results)
            self.message_sent = False
            self.event = 'Quali'
            return
        else:
            if (self.event == 'FP1'):
                print('Bot waiting')
            else:
                print('Bot sleeping')
            return


bot = F1PollBot()

@bot.command("calculate")
async def calculate_race_result(ctx, P1:str, P2:str, P3:str, P4:str, P5:str):
    print("Race Result time")
    with open('./data/race_data_store.json') as f:
        rds = json.load(f)
    with open('./data/race_data_store.json', 'w') as f:
        list(rds[-1].values())[0]['race_result'] = [P1, P2, P3, P4, P5]
        json.dump(rds, f)
    points_calculator.calculate_points()

    em = discord.Embed(
        title = f'Leaderboard',
        description = 'After calculating the scores from the last race'
    )
    standings = points_calculator.leaderboard()

    for index, standing in enumerate(standings):
        for name, score in standing.items():
            em.add_field(name = f'{index + 1}: {name}', value = f'{score}', inline=False)
    await ctx.channel.send(embed=em)

bot.run(os.environ.get("BOT_TOKEN"))
