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

Create following json fils in `data` folder with the following format for all the players

`player_map.json`
```
{
    "{18-digit discord user name}": {
        "username": "{discord user name}",
        "sheetName": "{Common name}",
        "runningTotal": 15,
        "pastScores": [
            5,
            5,
            5,
            ...
        ]
    }
    ...
}
```

`race_result_map.json`
```
{
    "{18-digit discord user name}": ["", "", "", "", ""],
    ...
}
```

`race_data_store.json` - This will start empty, and then gets autofilled with the help of race_result_map.json
```
[]
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
1. ~~Figure out a better way to export the results~~
1. ~~Create a datastore~~
1. ~~Create a leaderboard~~