## Installation

```
pip install -r requirements.txt
```
If you have [poetry](https://python-poetry.org/) installed then
```bash
poetry install
```
To enable virtual environment
```bash
poetry shell
```

Create a `player_map.json` in `data` folder with the following format for all the players

```
{
    "{18-digit discord user name}": {
        "username": "{discord user name}",
        "predictions": {
            "P1": "",
            "P2": "",
            "P3": "",
            "P4": "",
            "P5": ""
        }
    }
    ....
}
```

Change the `DTSTART` of `FP1` and `Qualifying` of the *same* Grand prix before testing the bot.

## Run
```
python runme.py
```

## TODO
1. ~~Fix the button interaction failure~~
1. ~~Change the messages~~
1. ~~Improve the JSON output~~
1. Figure out a better way to export the results
1. Connect gSheets to autofill the results (will probably have to create a map the discord users to users in the sheet)