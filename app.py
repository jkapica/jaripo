import os
import json
from hashlib import md5

from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy


this_dir = os.path.dirname(__file__)

app = Flask(__name__)
app.secret_key = md5(__file__.encode()).hexdigest()
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{this_dir}/test.db'
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    passwd = db.Column(db.String(80), nullable=False)
    logged = db.Column(db.Boolean, default=False)
    vote = db.Column(db.String(32))
    is_master = db.Column(db.Boolean, default=False)


class Option(db.Model):
    name = db.Column(db.String(64), primary_key=True, nullable=False)
    value = db.Column(db.String(64))


try:
    db.create_all()
except Exception as ex:
    print(ex)


def show_votes(value=None):
    if value is None:
        if User.query.filter_by(vote=None).count() == 0:
            value = True

    if value is not None:
        value = str(bool(value))

    name = 'show_votes'
    opt = Option.query.filter_by(name=name).first()
    if opt is None:
        opt = Option(name=name, value=value)
        db.session.add(opt)
        db.session.commit()
        return bool(value)

    if value is not None and opt.value != value:
        opt.value = value
        db.session.commit()

    return opt.value == str(True)


def passwd(plain):
    return md5(plain.encode()).hexdigest()


@app.before_request
def setup_user():
    uid = session.get('uid')
    request.user = User.query.filter_by(id=uid).first()
    print(f'{uid=}, {request.user=}, {request.path=}')
    if any((
        'login' in request.path,
        'css' in request.path,
        request.user and request.user.logged,
    )):
        return  # No redirect

    return redirect(url_for('login'))


@app.route('/')
def index():
    return redirect(url_for('scoreboard'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    user = None

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        session.pop('username', None)

        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username, passwd=passwd(password))
            user.logged = True
            db.session.add(user)
        elif passwd(password) == user.passwd:
            user.logged = True
        else:
            user.logged = False
            error = 'Wrong password!'

        user.is_master = bool(user.logged and request.form.get('is_master'))
        db.session.commit()
        if user.logged:
            session['uid'] = user.id
        return redirect(url_for('index'))
    return render_template(
        'login.html',
        error=error,
        user=user
    )


@app.route('/logout')
def logout():
    if request.user:
        request.user.logged = False
        db.session.commit()
    session.clear()
    return redirect(url_for('login'))


@app.route('/vote', methods=['GET', 'POST'])
def vote():
    if request.method == 'POST':
        request.user.vote = request.form.get('vote')
        db.session.commit()
        return redirect(url_for('scoreboard'))

    return render_template(
        'vote.html',
        user=request.user
    )


@app.route('/scoreboard', methods=['GET', 'POST'])
def scoreboard():
    show = None
    reset = request.form.get('reset')

    users = User.query.filter_by(logged=True).all()
    stats = {}
    if request.method == 'POST':
        print(f'POST={dict(request.form)}')
        if request.form.get('show') and request.user.is_master:
            show = show_votes(True)
        if reset and request.user.is_master:
            show = show_votes(False)
            for u in users:
                u.vote = None
            db.session.commit()
        return redirect(url_for('scoreboard'))

    values = []
    for u in users:
        try:
            values.append(float(u.vote))
        except:
            pass
    if values:
        stats['min'] = min(values)
        stats['max'] = max(values)
        stats['avg'] = sum(values) / len(values)

    if show is None:
        show = show_votes()

    return render_template(
        'scoreboard.html',
        users=users,
        show=show,
        stats=stats,
    )


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
