import json

from app import db, Teacher, Goal, Day, days, icons
from data import teachers, goals

for key, value in days.items():
    day = Day(key_en=key, value_ru=value[0], value_en=value[1])
    db.session.add(day)
db.session.commit()

for key, value in goals.items():
    goal = Goal(key_en=key, value_ru=value, icon=icons[key])
    db.session.add(goal)
db.session.commit()

for teacher in teachers:
    teacher_rec = Teacher(id=teacher['id'],
                  name=teacher['name'],
                  about=teacher['about'],
                  rating=teacher['rating'],
                  picture=teacher['picture'],
                  price=teacher['price'],
                  free=json.dumps(teacher['free']))
    for goal in teacher['goals']:
        goal_rec = db.session.query(Goal).filter(Goal.key_en == goal).first()
        teacher_rec.goals.append(goal_rec)
    db.session.add(teacher_rec)
db.session.commit()
