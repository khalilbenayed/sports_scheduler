import datetime
import csv
import random

import gurobipy as gp
from gurobipy import GRB

# Base data
n_teams = 20
n_matchdays = 2 * (n_teams - 1)

teams = {team+1: random.choice((1,3,5))  for team in range(n_teams)}  # team number: popularity
print(teams)

games = [(t_1, t_2) for t_1 in teams for t_2 in teams if t_1 != t_2]
matchdays = [matchday+1 for matchday in range(n_matchdays)]

due_dates = {
    1: 3, 2: 5, 3: 8, 4: 10, 5: 13, 6: 15, 7: 18, 8: 20, 9: 23,
    10: 33, 11: 35, 12: 38, 13: 40, 14: 43, 15: 45, 16: 48, 17: 50,
    18: 53, 19: 55, 20: 58, 21: 60, 22: 63, 23: 65, 24: 68, 25: 70,
    26: 73, 27: 75, 28: 83, 29: 85, 30: 88, 31: 90, 32: 93, 33: 95,
    34: 98, 35: 100, 36: 103, 37: 105, 38: 107
}
vacations = {i for i in range(22, 30)} | {i for i in range(76, 81)}
matchday_times = {
    (i, j): random.choice((1,3,5)) for i in matchdays for j in range(due_dates[i-1] if i > 1 else 0, due_dates[i]+3) if j not in vacations
}  # (matchday, time): revenue potential

k = 10
target_revenue = 4500
theta_1, theta_2 = 0.75, 0.25
min_rest = 1
max_cons_home_or_away = 4

# Create optimization model
m = gp.Model('sport_scheduling')
m.ModelSense = GRB.MINIMIZE


# Create variables
z = m.addVar(lb=0)
schedule = m.addVars(games, matchday_times, vtype=GRB.BINARY)


# set objective function
m.setObjective(theta_1 * z +
               theta_2 * (target_revenue -
                          gp.quicksum(schedule[i, j, r, s]*matchday_times[(r, s)]*(teams[i]+teams[j])/2
                                      for i in teams for j in teams if j != i for r, s in matchday_times.keys())),
               GRB.MINIMIZE)


# constraints
# 1) each team plays every other teams at home once
m.addConstrs(
    (schedule.sum(i, j, '*', '*') == 1 for i, j in games))

# 2) each team plays one game per matchday
m.addConstrs(
    (schedule.sum(i, '*', r, '*')+schedule.sum('*', i, r, '*') == 1 for i in teams for r in matchdays))

# 3) each team has enough rest between games
m.addConstrs(
    (((gp.quicksum(schedule[i, j, r, s]*s for j in teams if j != i for rr, s in matchday_times if rr == r)) +
      (gp.quicksum(schedule[j, i, r, s]*s for j in teams if j != i for rr, s in matchday_times if rr == r))) -
     ((gp.quicksum(schedule[i, j, r-1, s]*s for j in teams if j != i for rr, s in matchday_times if rr == r-1)) +
      (gp.quicksum(schedule[j, i, r-1, s]*s for j in teams if j != i for rr, s in matchday_times if rr == r-1))) >= min_rest
     for i in teams for r in matchdays[1:]))

# 4) each team plays no more than m consecutive home or away games
m.addConstrs(
    ((gp.quicksum(schedule[i, j, r, s]
                  for j in teams if j != i
                  for r, s in matchday_times if r in matchdays[t:t+max_cons_home_or_away+1]
                  ) <= max_cons_home_or_away
      for i in teams for t in range(1, n_matchdays-max_cons_home_or_away))))
m.addConstrs(
    ((gp.quicksum(schedule[j, i, r, s]
                  for j in teams if j != i
                  for r, s in matchday_times if r in matchdays[t:t+max_cons_home_or_away+1]
                  ) <= max_cons_home_or_away
      for i in teams for t in range(1, n_matchdays-max_cons_home_or_away))))

# 5) no more than k simultaneous games
m.addConstrs(schedule.sum('*', '*', r, s) <= k for r, s in matchday_times)

# 6) z is at least the maximum lateness
m.addConstrs(
    (z >= schedule[i, j, r, s]*s-due_dates[r] for i, j in games for r, s in matchday_times))


# Compute optimal solution
m.optimize()

# Print solution
if m.status == GRB.OPTIMAL:
    solution = m.getAttr('x', schedule)
    dict_data = []
    date_0 = datetime.date(2017, 10, 28)
    for r, s in matchday_times:
        for i, j in games:
            if solution[i, j, r, s] == 1:
                dict_data.append({
                    'matchday': r,
                    'date': date_0 + datetime.timedelta(days=s),
                    'game': f'{i} vs {j}'
                })
                print(f'Matchday {r} at time {s}: {i} vs {j}')
    csv_columns = ['matchday', 'date', 'game']
    try:
        with open('CBA_result.csv', 'w') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
            writer.writeheader()
            for data in dict_data:
                writer.writerow(data)
    except IOError:
        print("I/O error")
