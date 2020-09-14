import datetime
import csv
import random

import gurobipy as gp
from gurobipy import GRB

# Base data
n_teams = 4
n_matchdays = 6

teams = {team+1: random.choice((1,3,5))  for team in range(n_teams)}  # team number: popularity
print(teams)
games = [(t_1, t_2) for t_1 in teams for t_2 in teams if t_1 != t_2]
matchdays = [matchday+1 for matchday in range(n_matchdays)]
due_dates = {1: 1, 2: 3, 3: 5, 4: 7, 5: 9, 6: 11}
matchday_times = {
    (1, 0): 1,
    (1, 1): 3,
    (2, 2): 1,
    (2, 3): 3,
    (2, 4): 3,
    (3, 5): 1,
    (3, 6): 3,
    (4, 7): 1,
    (4, 8): 1,
    (4, 9): 3,
    (5, 10): 1,
    (5, 11): 1,
    (6, 12): 1,
    (6, 13): 3
}  # (matchday, time): revenue potential

k = 2
target_revenue = 100
theta_1, theta_2 = 0, 1
min_rest = 1
max_cons_home_or_away = 5

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
    date_0 = datetime.datetime.now()
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
        with open('4_team_result.csv', 'w') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
            writer.writeheader()
            for data in dict_data:
                writer.writerow(data)
    except IOError:
        print("I/O error")
