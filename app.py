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


try:
    db.create_all()
except Exception as ex:
    print(ex)


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

    print('redirect to login')
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

        db.session.commit()
        session['is_master'] = user.logged and request.form.get('is_master')
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
    show = request.form.get('show')
    reset = request.form.get('reset')
    refresh = request.form.get('refresh')
    print(f'{show=}, {reset=}, {refresh=}')

    users = User.query.filter_by(logged=True).all()
    stats = {}
    if request.method == 'POST' and request.form.get('reset'):
        for u in users:
            u.vote = None
        db.session.commit()
    else:
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

    return render_template(
        'scoreboard.html',
        user=request.user,
        users=users,
        show=request.form.get('show'),
        stats=stats,
    )


if __name__ == '__main__':
    app.run(debug=True)
