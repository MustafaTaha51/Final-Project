from flask import Flask, render_template, request, session, redirect, url_for
from flask_mail import Mail, Message
from flask_socketio import join_room, leave_room, send, SocketIO
from random import choice
from re import findall
from datetime import datetime
import sqlite3
from string import ascii_uppercase
from werkzeug.security import check_password_hash, generate_password_hash
import os
from dotenv import load_dotenv

# Environment variable to hide username and password
load_dotenv()
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

app = Flask(__name__)
app.config['MAIL_SERVER'] = "smtp.fastmail.com"
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = USERNAME
app.config['MAIL_PASSWORD'] = PASSWORD
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config["SECRET_KEY"] = "hello"
socketio = SocketIO(app)
mail = Mail(app)  # Initialize Flask-Mail with Flask application

# List of active rooms
rooms = {}

# Generates string of ASCII characters as room code, only returns if code doesn't already exist
def code_generate(length):
    while True:
        code = ""
        for _ in range(length):
            code += choice(ascii_uppercase)
        
        if code not in rooms:
            return code

# Generates string of ASCII characters as chat_id code, only returns if code doesn't already exist
def chat_id_generate(length):
    conn = sqlite3.connect('logs.db')
    cur = conn.cursor()
    while True:
        code = ""
        for _ in range(length):
            code += choice(ascii_uppercase)
        
        # Checking that chat_id code doesn't already exist
        cur.execute("SELECT DISTINCT chat_id FROM chatlogs WHERE chat_id = ?", (code,))
        rows = cur.fetchall()
        list = [item for row in rows for item in row]
        if code not in list:
            return code

# Add alert to database (user has joined or left room)
def alert(id, name, message):
    conn = sqlite3.connect('logs.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO chatlogs (chat_id, name, message, time) VALUES (?, ?, ?, ?)", (id, name, message, datetime.now()))
    conn.commit()
    conn.close()
    return

@app.route("/", methods=["GET", "POST"])
def home():
    # Clear specific session variables when user returns from chat room
    session.pop("room", None)
    session.pop("name", None)

    # Getting user's username if they have registered or logged in
    username = session.get("username")
    
    # User has submitted form data
    if request.method == "POST":
        # Extracting form data
        name = request.form.get("name")
        code = request.form.get("code")

        # Default to False if nothing has been detected
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        # Checking if user has entered a name
        if not name:
            return render_template("index.html", error="Please enter a name", code=code, name=name, logusername=username)

        # Checking if user has entered a code if they clicked join
        if join != False and not code:
            return render_template("index.html", error="Please enter a room code", code=code, name=name, logusername=username)
        
        room = code

        # Checking if user clicked create, user clicked join otherwise
        if create != False:
            # Checking if user has already entered a custom code, generates random 4-character code if not
            if not code:
                room = code_generate(4)
            rooms[room] = {"members": 0, "messages": [], "chat_id": chat_id_generate(5)}
        elif code not in rooms:
            return render_template("index.html", error="Room does not exist", code=code, name=name, logusername=username)
        
        session["room"] = room
        session["name"] = name

        return redirect(url_for("room"))

    # User accessed page via GET
    return render_template("index.html", logusername=username)

@app.route("/room")
def room():
    room = session.get("room")
    username = session.get("username")

    # Ensures user cannot access room page without first going through home page
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))
    
    return render_template("room.html", code=room, name=session["name"], messages=rooms[room]["messages"], logusername=username)

@app.route("/login", methods=["GET", "POST"])
def login():
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure all input fields were populated
        username = request.form.get("username")
        password = request.form.get("password")
        if not username or not password:
            return render_template("login.html", error="Missing username and/or password", username=username)
        
        # Check if user inputs correspond with an account that exists
        conn = sqlite3.connect('logs.db')
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        rows = cur.fetchall()
        conn.close()
        
        if len(rows) != 1 or not check_password_hash(rows[0][2], password):
            return render_template("login.html", error="Incorrect username and/or password", username=username)

        # Log user in after passing validation (uses session to remember which user is logged in)
        session["username"] = username
        session["user_id"] = rows[0][0]
        print(f"Session created: {session.get('user_id')}")

        # Redirect user to home page with username variable
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")
    
@app.route("/logout")
def logout():
    # Clear user's session
    session.pop("username", None)
    session.pop("user_id", None)

    # Redirect user to home page
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Ensure all input fields were populated
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        if not username or not password or not confirmation:
            return render_template("register.html", error="Missing username and/or password", username=username)
        
        # Check if both passwords are identical
        elif password != confirmation:
            return render_template("register.html", error="Passwords do not match", username=username)

        # Check if username already exists
        conn = sqlite3.connect('logs.db')
        cur = conn.cursor()
        cur.execute("SELECT id, username FROM users")
        rows = cur.fetchall()

        for row in rows:
            if username == row[1]:
                conn.close()
                print("Username already in use")
                return render_template("register.html", error="Username already in use", username=username)

        # Remember which user is logged in
        session["username"] = username

        # Add user to users database with hashed password
        passHash = generate_password_hash(password, method="pbkdf2", salt_length=16)
        cur.execute("INSERT INTO users (username, hash) VALUES (?, ?)", (username, passHash))
        cur.execute("SELECT id FROM users where username = ?", (username,))
        userId = cur.fetchall()[0][0]
        session["user_id"] = userId
        print(f"Session created: {session.get('user_id')}")
        conn.commit()
        conn.close()

        # Redirect user to home page
        return redirect(url_for("home"))
    

    # If user attempts to reach page via post, they will only be granted access if they aren't logged in
    if session.get("username"):
        return redirect(url_for("home"))
    
    return render_template("register.html")

@app.route("/chatlogs", methods=["GET", "POST"])
def chatlogs():
    # Ensures user cannot access room page if they aren't logged in
    username = session.get("username")
    if not username:
        return redirect(url_for("home"))

    # Gets ids and times of all chats (just for testing purposes)
    conn = sqlite3.connect('logs.db')
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT chat_id FROM logaccess WHERE username = ?", (username,))

    # Fetches all ids returned and puts them into a list of elements (not tuples)
    rows = cur.fetchall()
    id_list = [item for row in rows for item in row]

    idTimeList = []
    # Getting date of creation for all chats
    for id in id_list:
        cur.execute("SELECT DISTINCT time FROM chatlogs WHERE chat_id = ? LIMIT 1", (id,))
        time = cur.fetchall()[0][0]
        # Extract date and time excluding seconds
        pattern = r'\b\d{4}-\d{2}-\d{2} \d{2}:\d{2}\b'  
        date = findall(pattern, time)[0]
        idTimeList.append({"chat_id": id, "time": date})

    return render_template("chatlogs.html", logusername=username, idTimeList=idTimeList)

# Sends user's feedback message
@app.route("/send_email", methods=["GET", "POST"])
def send_email():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        message = request.form.get("message")
        
        # Sending email
        msg = Message(subject="Flask Chatroom Feedback",
                    sender=email,
                    recipients=[USERNAME])
        msg.body = f"Name: {name}\nEmail: {email}\n\n{message}"

        mail.send(msg)

    return redirect(url_for("home"))

# User deletes chatlog
@app.route("/delete", methods=["GET", "POST"])
def delete():
    if request.method == "POST":
        # Check if user is logged in
        username = session.get("username")
        if not username:
            return redirect(url_for("home"))

        # Gets chat_id of form submitted
        buttonText = request.form["delete"]

        # Deletes user's logaccess to selected chat_id from database
        conn = sqlite3.connect('logs.db')
        cur = conn.cursor()
        cur.execute("DELETE FROM logaccess WHERE chat_id = ? AND username = ?", (buttonText, username))
        conn.commit()
        conn.close()

        return redirect(url_for("chatlogs"))
    
    return redirect(url_for("home"))

# User views chatlog
@app.route("/chatlog_view", methods=["GET", "POST"])
def chatlog_view():
    if request.method == "POST":
        # Check if user is logged in
        username = session.get("username")
        if not username:
            return redirect(url_for("home"))
        
        # Gets chat_id of form submitted
        chat_id = request.form["logview"]
        print(f"id: {chat_id}")

        # Getting all chatlogs associated with selected chat_id
        conn = sqlite3.connect("logs.db")
        cur = conn.cursor()
        cur.execute("SELECT name, message FROM chatlogs WHERE chat_id = ?", (chat_id,))
        rows = cur.fetchall()
        logs = [row for row in rows]

        return render_template("chatlog.html", logusername=username, logs=logs)

    return redirect(url_for("home"))

# User connects to room
@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")

    # Security measure to ensure user cannot access room without going through home page
    if not room or not name:
        return
    # If room doesn't exist, user cannot join room
    if room not in rooms:
        leave_room(room)
        return
    
    # Enters user into room and send alert message indicating this to members of room
    join_room(room)
    message = "has entered the room"
    send({"name": name, "message": message}, to=room)

    # Add alert to database
    chat_id = rooms[room]["chat_id"]
    alert(chat_id, name, message)

    # Change number of members in room
    rooms[room]["members"] += 1
    print(f"{name} joined room {room} id {chat_id}")

    # Grant user access to the chatlogs of the room they just joined if they are logged in
    username = session.get("username")
    if username:
        conn = sqlite3.connect('logs.db')
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO logaccess (username, chat_id) VALUES (?, ?)", (username, chat_id))
        conn.commit()
        conn.close()

# User disconnects from room
@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    chat_id = rooms[room]["chat_id"]
    message = "has left the room"
    
    # User leaves room that exists
    if room in rooms:
        # -1 member count
        rooms[room]["members"] -= 1
        # Delete room if everyone leaves
        if rooms[room]["members"] <= 0:
            del rooms[room]

    # Add alert to database
    alert(chat_id, name, message)

    # Prints alert that user has left
    send({"name": name, "message": message}, to=room)
    print(f"{name} has left the room {room} id {chat_id}")

# User sends a message
@socketio.on("message")
def message(data):
    room = session.get("room")
    name = session.get("name")

    # Check if user is actually in a room
    if room not in rooms:
        return

    # Get content and send
    content = {
        "name": session.get("name"),
        "message": data["data"]
    }

    send(content, to=room)
    # Add message to dictionary
    rooms[room]["messages"].append(content)
    print(f"{session.get('name')} said: {data['data']}")

    # Add message to chatlogs database
    conn = sqlite3.connect('logs.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO chatlogs (chat_id, name, message, time) VALUES (?, ?, ?, ?)", (rooms[room]["chat_id"], name, data["data"], datetime.now()))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    socketio.run(app, debug=True)   