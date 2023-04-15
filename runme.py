from datetime import datetime, timezone
import os
import json
from os.path import join, dirname
from dotenv import load_dotenv

import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
from icalendar import Calendar, Event
from typing import List

dotenv_path = join(dirname(__file__), ".env")
load_dotenv(dotenv_path)

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Global variables to store poll data
polls = {}
poll_results = {}
FP1_START = []
QUALI_START = []
LOCATION = []

drivers = [
    {"emocode": "<:VER:1094758174780817549>", "name": "VER"},
    {"emocode": "<:PER:1094758171383439371>", "name": "PER"},
    {"emocode": "<:ALO:1094758169516982292>", "name": "ALO"},
    {"emocode": "<:STR:1094758161132552192>", "name": "STR"},
    {"emocode": "<:LEC:1094758144057544774>", "name": "LEC"},
    {"emocode": "<:SAI:1094758163116458125>", "name": "SAI"},
    {"emocode": "<:HAM:1094758166119583774>", "name": "HAM"},
    {"emocode": "<:RUS:1094758157663879209>", "name": "RUS"},
    {"emocode": "<:NOR:1094758149195575406>", "name": "NOR"},
    {"emocode": "<:PIA:1094758136889479310>", "name": "PIA"},
    {"emocode": "<:BOT:1094758141792624733>", "name": "BOT"},
    {"emocode": "<:ZHO:1094758130442838127>", "name": "ZHO"},
    {"emocode": "<:HUL:1094758147467526164>", "name": "HUL"},
    {"emocode": "<:MAG:1094758124470157423>", "name": "MAG"},
    {"emocode": "<:ALB:1094758120959512627>", "name": "ALB"},
    {"emocode": "<:SAR:1094758118849781830>", "name": "SAR"},
    {"emocode": "<:TSU:1094758128077250591>", "name": "TSU"},
    {"emocode": "<:DEV:1094758115376893994>", "name": "DEV"},
    {"emocode": "<:OCO:1094758139133448242>", "name": "OCO"},
    {"emocode": "<:GAS:1094758133794082957>", "name": "GAS"},
]


class DriverButton(Button["MyView"]):
    def __init__(self, label, custom_id, emoji):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label=label,
            custom_id=custom_id,
            emoji=emoji,
        )
        self.label = label
        self.custom_id = custom_id
        self.emoji = emoji

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: MyView = self.view
        print("hey there")
        custom_id = interaction.data["custom_id"]
        poll_name, option = custom_id.split(":")
        user_id = interaction.user.id
        polls[poll_name]["votes"][user_id] = option
        print(polls[poll_name])
        # await interaction.response.defer()
        view.stop()
        await interaction.response.send_message(
            f"Your vote has been recorded.", ephemeral=True, view=view
        )


class MyView(View):
    children: List[DriverButton]

    def __init__(self, poll_name):
        super().__init__()
        for driver in drivers:
            self.add_item(
                DriverButton(
                    label=driver["name"],
                    custom_id=f'{poll_name}:{driver["name"]}',
                    emoji=driver["emocode"],
                )
            )


# Function to read F1 calendar and get start time of FP1 and Qualifying rounds
def get_round_start_time():
    CALENDAR_URL = open(
        ".\\f1-calendar_p1_qualifying.ics",
        "r",
    )
    cal = Calendar.from_ical(CALENDAR_URL.read())
    for event in cal.walk("vevent"):
        if "FP1" in event["SUMMARY"]:
            FP1_START.append(event["DTSTART"].dt)
        if "Qualifying" in event["SUMMARY"]:
            QUALI_START.append(event["DTSTART"].dt)
        LOCATION.append(event["LOCATION"])


# Function to create polls
async def create_polls():
    global polls
    for i in range(1, 6):
        poll_name = f"P{i}"
        polls[poll_name] = {"question": f"Who will win P{i}?", "votes": {}}
        view = MyView(poll_name)
        channel = bot.get_channel(int(os.environ.get("CHANNEL_ID")))
        await channel.send(f'**{polls[poll_name]["question"]}**', view=view)


# Function to close polls and generate results
def close_polls():
    global poll_results
    for poll_name, poll_data in polls.items():
        poll_results[poll_name] = {}
        for user_id, vote in poll_data["votes"].items():
            if vote not in poll_results[poll_name]:
                poll_results[poll_name][vote] = []
            poll_results[poll_name][vote].append(user_id)
    with open("poll_results.json", "w") as f:
        json.dump(poll_results, f)


# Task to check if it's time to create or close polls
@tasks.loop(seconds=10)
async def poll_task():
    for fp1_start_time, qualifying_start_time in zip(FP1_START, QUALI_START):
        if fp1_start_time <= datetime.now(timezone.utc) < qualifying_start_time:
            await create_polls()
        elif datetime.now(timezone.utc) >= qualifying_start_time:
            close_polls()
            poll_task.cancel()


@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")
    get_round_start_time()
    poll_task.start()


bot.run(os.environ.get("BOT_TOKEN"))
