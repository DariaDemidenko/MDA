#C:\Users\Asus\Projects\Environments\flasksocketiochat\Scripts\activate.bat
#cd C:\Users\Asus\MDA
from flask import Flask
from flask import session, redirect, url_for, render_template, request
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_migrate import Migrate
from forms import LoginForm, SendMessageForm
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
import uuid

app = Flask(__name__)

app.debug = True
app.config['SECRET_KEY'] = 'gjr39dkjn344_!67#'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'

socketio = SocketIO(app)
db = SQLAlchemy(app)
migrate = Migrate(app,db)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(15), nullable=False)
    session_id = db.Column(db.String(200), nullable=False)
    isready = db.Column(db.Integer, default='0')
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'))
    def __repr__(self):
        return f"User('{self.username}', '{self.session_id}')"

class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(15), nullable=False)
    image_file = db.Column(db.String(20))
    room = db.relationship('Rooms', backref='place', lazy=False)
    def __repr__(self):
        return f"Location('{self.name}', '{self.image_file}')"

class Rooms(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    s_id = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    spy_id = db.Column(db.Integer, default=1)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'))
    users = db.relationship('User', backref='player', lazy=False)

    def __repr__(self):
        return f"Rooms('{self.location}', '{self.spy}')"

def RandomLocation():
    import random
    x = random.randint(1,3)
    r_location = db.session.query(Location).filter_by(id=x).first()
    loc_id = r_location.id
    return loc_id


def RandomSpy(room):
    import random
    A = []
    count = 0
    for user in room.users:
        A.append(user.id)
        count += 1
    x = random.randint(0,count-1)
    spy = db.session.query(User).filter_by(id=A[x]).first()
    spy.isready = 1


@app.route('/', methods=['GET', 'POST'])
def index():
    form = LoginForm()
    if form.validate_on_submit():
        session['name'] = form.name.data
        session['room'] = form.room.data
        room_empty = db.session.query(Rooms).filter_by(status='active').count()
        session_id = str(uuid.uuid1())
        if room_empty == 0:
            a_room = Rooms(s_id=session_id, status='active')
            db.session.add(a_room)
            db.session.commit()
            new_user = User(username='name', session_id=session_id, room_id=a_room.id)
            db.session.add(new_user)
            db.session.commit()
            a_room.location_id = RandomLocation()
            db.session.commit()
            session['room'] = a_room.s_id
        else:
            a_room = db.session.query(Rooms).filter_by(status='active').first()
            session['room'] = a_room.s_id
            new_user = User(username='name', session_id=session_id, room_id=a_room.id)
            db.session.add(new_user)
            db.session.commit()
            count = 0
            print(a_room.users)
            for user in a_room.users:
                count = count + 1
                print(count)
            if count >= 3:
                a_room.status = 'closed'
                db.session.commit()
            RandomSpy(a_room)
        session['cur_user_id'] = new_user.id
        return redirect(url_for('.game'))
    elif request.method == 'GET':
        form.name.data = session.get('name', '')
        form.room.data = session.get('room', '')
    return render_template('index.html', form=form)

@app.route('/rules')
def rules():
    return render_template('rules.html', title="Правила игры")

@app.route('/locations')
def locations():
    return render_template('locations.html', title="Локации")

@app.route('/about')
def about():
    return render_template('about.html', title="О разработчиках")

@app.route('/game')
def game():
    """Chat room. The user's name and room must be stored in
    the session."""
    form = SendMessageForm()
    name = session.get('name', '')
    room = session.get('room', '')
    cur_user_id = session.get('cur_user_id', '')
    current_user = db.session.query(User).filter_by(id=cur_user_id).first()
    #location = session.get('location', '')
    room1 = db.session.query(Rooms).filter_by(s_id=room).first()
    location_id = room1.location_id
    location = db.session.query(Location).filter_by(id=location_id).first()
    if name == '' or room == '':
        return redirect(url_for('.index'))
    return render_template('game.html', name=name, form=form, room=room, title="Игра",
                            current_user=current_user, location=location)

@socketio.on('joined', namespace='/game')
def joined(message):
    """Sent by clients when they enter a room.
    A status message is broadcast to all people in the room."""
    room = session.get('room')
    join_room(room)
    emit('status', {'msg': session.get('name') + ' присоединился/ась к игре ' + session.get('room')}, room=room)

@socketio.on('text', namespace='/game')
def text(message):
    """Sent by a client when the user entered a new message.
    The message is sent to all people in the room."""
    room = session.get('room')
    emit('message', {'msg': session.get('name') + ': ' + message['msg']}, room=room)

@socketio.on('left', namespace='/game')
def left(message):
    """Sent by clients when they leave a room.
    A status message is broadcast to all people in the room."""
    room = session.get('room')
    leave_room(room)
    emit('status', {'msg': session.get('name') + ' покинул/а чат.'}, room=room)


if __name__ == '__main__':
    socketio.run(app)


#from run import db
#db.create_all()
#from run import User, Rooms, Location, chats
