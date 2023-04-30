import json

def calculate_points():
    with open("./data/race_data_store.json") as rds_json:
        rds = json.load(rds_json)

    with open("./data/player_map.json") as pm_json:
        pm = json.load(pm_json)

    last_race = list(rds[-1].values())[0]

    race_result = last_race["race_result"]

    for user_id, preds in last_race.items():
        total_points = 0
        if user_id != "race_result":
            if preds[0] == race_result[0]:
                total_points += 8
            if preds[1] == race_result[1]:
                total_points += 9
            if preds[2] == race_result[2]:
                total_points += 10
            if preds[3] == race_result[3]:
                total_points += 12
            if preds[4] == race_result[4]:
                total_points += 15

            if preds[0] == race_result[1]:
                total_points += 5
            if preds[1] == race_result[0]:
                total_points += 5

            if preds[0] == race_result[2]:
                total_points += 4
            if preds[2] == race_result[0]:
                total_points += 4

            if preds[0] == race_result[3]:
                total_points += 2
            if preds[3] == race_result[0]:
                total_points += 2

            if preds[0] == race_result[4]:
                total_points += 1
            if preds[4] == race_result[0]:
                total_points += 1

            if preds[1] == race_result[2]:
                total_points += 3
            if preds[2] == race_result[1]:
                total_points += 3

            if preds[1] == race_result[3]:
                total_points += 2
            if preds[3] == race_result[1]:
                total_points += 2

            if preds[1] == race_result[4]:
                total_points += 1
            if preds[4] == race_result[1]:
                total_points += 1

            if preds[2] == race_result[3]:
                total_points += 2
            if preds[3] == race_result[2]:
                total_points += 2

            if preds[2] == race_result[4]:
                total_points += 1
            if preds[4] == race_result[2]:
                total_points += 1

            if preds[3] == race_result[4]:
                total_points += 2
            if preds[4] == race_result[3]:
                total_points += 2

            pm[user_id]["runningTotal"] = pm[user_id]["runningTotal"] + total_points
            pm[user_id]["pastScores"].append(total_points)

    with open("./data/player_map.json", "w") as f:
        json.dump(pm, f)
 

def leaderboard():
    with open("./data/player_map.json") as pm_json:
        pm = json.load(pm_json)

    leaders = sorted(pm.items(), key=lambda item: item[1]["runningTotal"], reverse=True)
    standings = []
    for leader in leaders:
        standings.append({leader[1]["sheetName"]: f'> {str(leader[1]["runningTotal"])} \n> {"🦆" if leader[1]["pastScores"][-1] == 0 else "🚀"} {str(leader[1]["pastScores"][-1])}'})

    return standings
