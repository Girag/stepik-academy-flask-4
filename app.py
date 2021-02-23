import json
import os

from flask import Flask, render_template, abort, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSON
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect, CSRFError
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
                                      db.Column('teacher_id', db.Integer, db.ForeignKey('teachers.id')),
                                      db.Column('goal_id', db.Integer, db.ForeignKey('goals.id')))


class Teacher(db.Model):
    __tablename__ = "teachers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    about = db.Column(db.String, nullable=False)
    rating = db.Column(db.Float, nullable=False)
    picture = db.Column(db.String, nullable=False)
    price = db.Column(db.Float, nullable=False)
    goals = db.relationship("Goal", secondary=teachers_goals_association, back_populates="teachers")
    free = db.Column(JSON)
    bookings = db.relationship("Booking", back_populates="teachers")


class Booking(db.Model):
    __tablename__ = "bookings"
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String, nullable=False)
    client_phone = db.Column(db.String, nullable=False)
    time = db.Column(db.String, nullable=False)
    day = db.Column(db.String, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"))
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


days = {
    "mon": ["Понедельник", "monday"],
    "tue": ["Вторник", "tuesday"],
    "wed": ["Среда", "wednesday"],
    "thu": ["Четверг", "thursday"],
    "fri": ["Пятница", "friday"],
    "sat": ["Суббота", "saturday"],
    "sun": ["Воскресенье", "sunday"]
}

icons = {"travel": "⛱",
         "study": "🏫",
         "work": "🏢",
         "relocate": "🚜"}


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


@app.errorhandler(404)
def render_not_found(_):
    return "Ничего не нашлось! Вот неудача, отправляйтесь на главную!", 404


@app.errorhandler(CSRFError)
def handle_csrf_error(_):
    return "И кто это тут у нас про CSRF token забыл?", 400


@app.route("/")
def render_main():
    goals, teachers = db.session.query(Goal).all(), db.session.query(Teacher).order_by(func.random()).limit(6)
    return render_template("index.html", goals=goals,
                           teachers=teachers)


@app.route("/all/")
def render_all():
    form = SortForm(request.args, meta={'csrf': False})

    if form.validate() or not request.args.to_dict():
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

    else:
        return redirect(url_for("render_all"))


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
    teacher_free = json.loads(teacher.free)
    schedule = {}
    for free in teacher_free:
        day_schedule = {}
        for time in teacher_free[free]:
            if teacher_free[free][time]:
                day_schedule.update({time: teacher_free[free][time]})
        schedule[free] = day_schedule
    all_days, days = db.session.query(Day).all(), {}
    for day in all_days:
        days[day.key_en] = [day.value_ru, day.value_en]
    return render_template("profile.html", teacher=teacher,
                           goals=goals,
                           days=days,
                           schedule=schedule)


@app.route("/request/", methods=["GET", "POST"])
def render_request():
    form = RequestForm(goal="travel", time="5-7")

    if form.validate_on_submit():
        goal_choices = dict(form.goal.choices)
        time_choices = dict(form.time.choices)
        session['request_goal'] = form.goal.data
        session['request_goal_label'] = goal_choices[form.goal.data]
        session['request_time'] = form.time.data
        session['request_time_label'] = time_choices[form.time.data]
        session['request_client_name'] = form.client_name.data
        session['request_client_phone'] = form.client_phone.data

        rec = Request(goal=session['request_goal'],
                      time=session['request_time'],
                      client_name=session['request_client_name'],
                      client_phone=session['request_client_phone'])
        db.session.add(rec)
        db.session.commit()
        return redirect(url_for("render_request_done"))
    return render_template("request.html", form=form)


@app.route("/request_done/")
def render_request_done():
    return render_template("request_done.html", goal=session['request_goal_label'],
                           time=session['request_time_label'],
                           name=session['request_client_name'],
                           phone=session['request_client_phone'])


@app.route("/booking/<int:teacher_id>/<day>/<time>/", methods=["GET", "POST"])
def render_booking(teacher_id, day, time):
    teacher = db.session.query(Teacher).get_or_404(teacher_id)
    teacher_free = json.loads(teacher.free)
    schedule = {}
    for free in teacher_free:
        day_schedule = {}
        for t in teacher_free[free]:
            if teacher_free[free][t]:
                day_schedule.update({t: teacher_free[free][t]})
        schedule[free] = day_schedule
    all_days, days = db.session.query(Day).all(), {}
    for d in all_days:
        days[d.value_en] = [d.value_ru, d.key_en]

    if schedule.get(days[day][1]) and f"{time}:00" in schedule.get(days[day][1]):
        form = BookingForm()
        if form.validate_on_submit():
            session['booking_day'] = form.weekday.data
            session['booking_time'] = form.time.data
            session['booking_teacher_id'] = form.teacher.data
            session['booking_client_name'] = form.client_name.data
            session['booking_client_phone'] = form.client_phone.data

            rec = Booking(client_name=session['booking_client_name'],
                          client_phone=session['booking_client_phone'],
                          time=session['booking_time'],
                          day=session['booking_day'],
                          teacher_id=session['booking_teacher_id'])
            db.session.add(rec)
            db.session.commit()
            return redirect(url_for("render_booking_done"))

        return render_template("booking.html", form=form,
                               teacher=teacher,
                               days=days,
                               day=day,
                               time=time)
    abort(404)


@app.route("/booking_done/")
def render_booking_done():
    return render_template("booking_done.html", days=days,
                           day=session['booking_day'],
                           time=session['booking_time'],
                           name=session['booking_client_name'],
                           phone=session['booking_client_phone'])


if __name__ == '__main__':
    app.run()
