import json
import os

from flask import Flask, render_template, abort, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, HiddenField, RadioField, SelectField
from wtforms.validators import InputRequired

app = Flask(__name__)
csrf = CSRFProtect(app)
app.config['SECRET_KEY'] = "VeryVeryRandomStringForVeryVerySecurity"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

teachers_goals_association = db.Table('teachers_goals', db.metadata,
                                      db.Column('teacher_id', db.Integer, db.ForeignKey('teachers.id'), nullable=False),
                                      db.Column('goal_id', db.Integer, db.ForeignKey('goals.id'), nullable=False))


class Teacher(db.Model):
    __tablename__ = "teachers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    about = db.Column(db.String, nullable=False)
    rating = db.Column(db.Float, nullable=False)
    picture = db.Column(db.String, nullable=False)
    price = db.Column(db.Float, nullable=False)
    goals = db.relationship("Goal", secondary=teachers_goals_association, back_populates="teachers")
    free = db.Column(JSONB, nullable=False)
    bookings = db.relationship("Booking", back_populates="teachers")


class Booking(db.Model):
    __tablename__ = "bookings"
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String, nullable=False)
    client_phone = db.Column(db.String, nullable=False)
    time = db.Column(db.String, nullable=False)
    day = db.Column(db.String, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=False)
    teachers = db.relationship("Teacher", back_populates="bookings")


class Request(db.Model):
    __tablename__ = "requests"
    id = db.Column(db.Integer, primary_key=True)
    goal = db.Column(db.String, nullable=False)
    time = db.Column(db.String, nullable=False)
    client_name = db.Column(db.String, nullable=False)
    client_phone = db.Column(db.String, nullable=False)


class Day(db.Model):
    __tablename__ = "days"
    id = db.Column(db.Integer, primary_key=True)
    key_en = db.Column(db.String, nullable=False)
    value_ru = db.Column(db.String, nullable=False)
    value_en = db.Column(db.String, nullable=False)


class Goal(db.Model):
    __tablename__ = "goals"
    id = db.Column(db.Integer, primary_key=True)
    key_en = db.Column(db.String, nullable=False)
    value_ru = db.Column(db.String, nullable=False)
    icon = db.Column(db.String, nullable=False)
    teachers = db.relationship("Teacher", secondary=teachers_goals_association, back_populates="goals")


class BookingForm(FlaskForm):
    weekday = HiddenField()
    time = HiddenField()
    teacher = HiddenField()
    client_name = StringField("Ваc зовут", [InputRequired(message="Укажите ваше имя")])
    client_phone = StringField("Ваш телефон", [InputRequired(message="Укажите ваш телефон")])


class RequestForm(FlaskForm):
    goal = RadioField("Какая цель занятий?", choices=[
        ('travel', 'Для путешествий'),
        ('study', 'Для учебы'),
        ('work', 'Для работы'),
        ('relocate', 'Для переезда'),
    ])
    time = RadioField("Сколько времени есть?", choices=[
        ('1-2', '1-2 часа в неделю'),
        ('3-5', '3-5 часов в неделю'),
        ('5-7', '5-7 часов в неделю'),
        ('7-10', '7-10 часов в неделю')
    ])
    client_name = StringField("Ваc зовут", [InputRequired(message="Укажите ваше имя")])
    client_phone = StringField("Ваш телефон", [InputRequired(message="Укажите ваш телефон")])


class SortForm(FlaskForm):
    sort = SelectField("Сортировать", choices=[
        ('random', 'В случайном порядке'),
        ('by_rating', 'Сначала лучшие по рейтингу'),
        ('expensive_first', 'Сначала дорогие'),
        ('cheap_first', 'Сначала недорогие'),
    ])


def get_schedule(teacher):
    teacher_free = json.loads(teacher.free)
    schedule = {}
    for free in teacher_free:
        day_schedule = {}
        for time in teacher_free[free]:
            if teacher_free[free][time]:
                day_schedule.update({time: teacher_free[free][time]})
        schedule[free] = day_schedule

    return schedule


def get_days():
    all_days = db.session.query(Day).all()
    days = {}
    for day in all_days:
        days[day.key_en] = [day.value_ru, day.value_en]

    return days


@app.errorhandler(404)
def render_not_found(_):
    return "Ничего не нашлось! Вот неудача, отправляйтесь на главную!", 404


@app.route("/")
def render_main():
    goals = db.session.query(Goal).all()
    teachers = db.session.query(Teacher).order_by(func.random()).limit(6)
    return render_template("index.html", goals=goals,
                           teachers=teachers)


@app.route("/all/")
def render_all():
    form = SortForm(request.args, meta={'csrf': False})

    if not form.validate() and request.args.to_dict():
        return redirect(url_for("render_all"))

    sort_value = request.args.get("sort")
    if not sort_value or sort_value == "random":
        teachers = db.session.query(Teacher).order_by(func.random()).all()
        return render_template("all.html", form=form,
                               teachers=teachers)

    elif sort_value == "by_rating":
        teachers = db.session.query(Teacher).order_by(Teacher.rating.desc()).all()
        return render_template("all.html", form=form,
                               teachers=teachers)

    elif sort_value == "expensive_first":
        teachers = db.session.query(Teacher).order_by(Teacher.price.desc()).all()
        return render_template("all.html", form=form,
                               teachers=teachers)

    elif sort_value == "cheap_first":
        teachers = db.session.query(Teacher).order_by(Teacher.price).all()
        return render_template("all.html", form=form,
                               teachers=teachers)


@app.route("/goals/<goal>/")
def render_goals(goal):
    goals = db.session.query(Goal).filter(Goal.key_en == goal).first()
    goal_name = f"{goals.value_ru[0].lower()}{goals.value_ru[1:].lower()}"
    icon = goals.icon
    teachers = db.session.query(Teacher).join(teachers_goals_association, Goal)\
        .filter(Goal.key_en == goal).all()
    return render_template("goal.html", goal=goal,
                           icon=icon,
                           goal_name=goal_name,
                           teachers=teachers)


@app.route("/profiles/<int:teacher_id>/")
def render_profiles(teacher_id):
    teacher = db.session.query(Teacher).get_or_404(teacher_id)
    goals = teacher.goals
    schedule = get_schedule(teacher)
    days = get_days()
    return render_template("profile.html", teacher=teacher,
                           goals=goals,
                           days=days,
                           schedule=schedule)


@app.route("/request/", methods=["GET", "POST"])
def render_request():
    form = RequestForm(goal="travel", time="5-7")
    if not form.validate_on_submit():
        return render_template("request.html", form=form)

    goal_choices = dict(form.goal.choices)
    time_choices = dict(form.time.choices)
    session['request'] = {
        "goal": form.goal.data,
        "goal_label": goal_choices[form.goal.data],
        "time": form.time.data,
        "time_label": time_choices[form.time.data],
        "client_name": form.client_name.data,
        "client_phone": form.client_phone.data
    }

    rec = Request(goal=session['request']['goal'],
                  time=session['request']['time'],
                  client_name=session['request']['client_name'],
                  client_phone=session['request']['client_phone'])
    db.session.add(rec)
    db.session.commit()
    return redirect(url_for("render_request_done"))


@app.route("/request_done/")
def render_request_done():
    return render_template("request_done.html", goal=session['request']['goal_label'],
                           time=session['request']['time_label'],
                           name=session['request']['client_name'],
                           phone=session['request']['client_phone'])


@app.route("/booking/<int:teacher_id>/<day>/<time>/", methods=["GET", "POST"])
def render_booking(teacher_id, day, time):
    teacher = db.session.query(Teacher).get_or_404(teacher_id)
    schedule = get_schedule(teacher)
    days = get_days()
    day = day[:3]

    if not schedule.get(day) or f"{time}:00" not in schedule.get(day):
        abort(404)

    form = BookingForm()
    if not form.validate_on_submit():
        return render_template("booking.html", form=form,
                               teacher=teacher,
                               days=days,
                               day=day,
                               time=time)

    session['booking'] = {
        "day": form.weekday.data,
        "time": form.time.data,
        "teacher_id": form.teacher.data,
        "client_name": form.client_name.data,
        "client_phone": form.client_phone.data
    }

    rec = Booking(client_name=session['booking']['client_name'],
                  client_phone=session['booking']['client_phone'],
                  time=session['booking']['time'],
                  day=session['booking']['day'],
                  teacher_id=session['booking']['teacher_id'])
    db.session.add(rec)
    db.session.commit()
    return redirect(url_for("render_booking_done"))


@app.route("/booking_done/")
def render_booking_done():
    days = get_days()
    return render_template("booking_done.html", days=days,
                           day=session['booking']['day'],
                           time=session['booking']['time'],
                           name=session['booking']['client_name'],
                           phone=session['booking']['client_phone'])


if __name__ == '__main__':
    app.run()
