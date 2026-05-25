# Credit: CS50x finance assignment for the template code!
from flask import Flask, redirect, render_template, request, session, flash, g
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required
from functools import wraps
import sqlite3
import csv
import io
import os

app = Flask("Flaskcard")

default_deck_title = "New Deck"
default_front_text = ""
default_back_text = ""

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect("data.db")
        db.execute("PRAGMA foreign_keys = ON")
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# For use in rendering the positions of a card in deck.html
@app.template_filter('int_display')
def int_display_filter(value):
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return value

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/login", methods=["GET", "POST"])
def login():
    # We don't clear the session, instead it doesn't do anything unless they logout first.
    if request.method == "GET":
        if session.get("userid"):
            return redirect("/")
        else:
            return render_template("login.html")
    elif request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if not username or not password:
            # Force them back into /login
            flash("Username and password must be provided!")
            return redirect("/login")
        
        # Now do password checking
        cursor = get_db().cursor()
        cursor.execute(
            "SELECT id, passhash FROM users WHERE username = ?", (username,)
        )
        row = cursor.fetchone()
        if not row or not check_password_hash(row[1], password):
            flash("Username or password incorrect!, please try again or register a new account!")
            return redirect("/login")
        
        # Green light
        session["userid"] = row[0]
        return redirect("/")
        
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    elif request.method == "POST":
        # Perform registration
        username = request.form.get("username")
        password = request.form.get("password")
        confirmp = request.form.get("confirmation")
        
        if not username or not password or not confirmp:
            flash("Username, Password and Password confirmation must be provided!")
            return redirect("/register")
        if not password == confirmp:
            flash("Password and Password confirmation must be same!")
            return redirect("/register")
        
        db_connection = get_db()
        cursor = db_connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, passhash) VALUES (?, ?)",
                (username, generate_password_hash(password))
            )
            db_connection.commit()
        except sqlite3.IntegrityError:
            flash("Username already exists!")
            return redirect("/register")

        # Registration done
        if session.get("userid")is None:
            flash("Registration complete, you can now login to your new account!")
            return redirect("/")
        else:
            flash("Registration for new account complete!")
            return redirect("/login")

@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect("/login")

@app.route("/passchange", methods=["GET", "POST"])
@login_required
def passchange():
    # This is used in both cases either way.
    db_connection = get_db()
    cursor = db_connection.cursor()

    if request.method == "GET":
        cursor.execute(
            "SELECT username FROM users WHERE id = ?",
            (session["userid"],)
        )
        username = cursor.fetchone()[0]
        return render_template("passchange.html", username=username)
    elif request.method == "POST":
        old_password = request.form.get("curr_password")
        new_password = request.form.get("password")
        new_password_confirm = request.form.get("confirmation")

        if not old_password or not new_password or not new_password_confirm:
            flash("Current password, New password and Password confirmation must be provided!")
            return redirect("/passchange")
        if not new_password == new_password_confirm:
            flash("New password and Password confirmation must be same!")
            return redirect("/passchange")

        # Check old_password
        cursor.execute(
            "SELECT passhash FROM users WHERE id = ?",
            (session["userid"],)
        )
        row = cursor.fetchone()
        # It should be impossible for a user to have no passhash
        if not check_password_hash(row[0], old_password):
            flash("Current password is incorrect!")
            return redirect("/passchange")
        
        # Perform password change
        cursor.execute(
            "UPDATE users SET passhash = ? WHERE id = ?",
            (generate_password_hash(new_password), session["userid"],)
        )
        db_connection.commit()
        flash("Password changed successfully!")
        return redirect("/")


@app.route("/")
@login_required
def index():
    db_connection = get_db()
    cursor = db_connection.cursor()
    
    # Get all decks
    cursor.execute(
        "SELECT id, title FROM decks WHERE ownerid = ?",
        (session["userid"],)
    )

    return render_template("index.html", decks=cursor.fetchall())

@app.route("/viewdeck/<int:deck_id>")
@login_required
def viewdeck(deck_id):
    db_connection = get_db()
    cursor = db_connection.cursor()

    # Verify if the owner even has access (owns) to this deck
    cursor.execute(
        "SELECT title FROM decks WHERE id = ? AND ownerid = ?",
        (deck_id, session["userid"],)
    )

    deck_row = cursor.fetchone()
    if not deck_row:
        flash("Deck cannot be accessed!")
        return redirect("/")
    
    # Get number of cards in deck
    cursor.execute(
        "SELECT COUNT(*) FROM cards WHERE deckid = ?",
        (deck_id,)
    )
    deck_size = cursor.fetchone()[0]

    # Get all cards in this deck
    cursor.execute(
        "SELECT id, front, back FROM cards WHERE deckid = ? ORDER BY position ASC",
        (deck_id,)
    )

    return render_template("deck.html", deck_title=deck_row[0], deck_size=deck_size, cards=cursor.fetchall(), deck_id=deck_id)

@app.route("/viewcard/<int:card_id>")
@login_required
def viewcard(card_id):
    db_connection = get_db()
    cursor = db_connection.cursor()

    # Get owning deck_id
    cursor.execute(
        "SELECT deckid FROM cards WHERE id = ?",
        (card_id,)
    )
    deckid_row = cursor.fetchone()
    if not deckid_row:
        flash("Card doesn't exist!")
        return redirect("/")
    deck_id = deckid_row[0]

    # Verify if the owner even has access (owns) to this deck
    cursor.execute(
        "SELECT title FROM decks WHERE id = ? AND ownerid = ?",
        (deck_id, session["userid"],)
    )

    deck_row = cursor.fetchone()
    if not deck_row:
        flash("Item cannot be accessed!")
        return redirect("/")

    # Get deck size
    cursor.execute(
        "SELECT COUNT(*) FROM cards WHERE deckid = ?",
        (deck_id,)
    )
    deck_size = cursor.fetchone()[0]

    # Get the contents of the card
    cursor.execute(
        "SELECT front, back, position FROM cards WHERE id = ?",
        (card_id,)
    )
    card_row = cursor.fetchone()
    if not card_row:
        flash("Such card doesn't exist!")
        return redirect("/")

    # Get the number of the card
    # I just count how many cards have a position <= to this one
    position = card_row[2]
    cursor.execute(
        "SELECT COUNT(*) FROM cards WHERE deckid = ? AND position <= ?",
        (deck_id, position,)
    )
    card_number = cursor.fetchone()[0]

    # Get the ids of the previous and next one
    cursor.execute(
        "SELECT id FROM cards WHERE deckid = ? AND position < ? ORDER BY position DESC LIMIT 1",
        (deck_id, position,)
    )
    prev_card_row = cursor.fetchone()
    isnt_prev_able = (prev_card_row == None)

    cursor.execute(
        "SELECT id FROM cards WHERE deckid = ? AND position > ? ORDER BY position ASC LIMIT 1",
        (deck_id, position,)
    )
    next_card_row = cursor.fetchone()
    isnt_next_able = (next_card_row == None)

    return render_template("card.html", 
                           deck_id=deck_id, 
                           deck_title=deck_row[0], 
                           deck_size=deck_size, 
                           card_number=card_number, 
                           card=card_row,
                           isnt_prev_able=isnt_prev_able,
                           prev_card_id="" if isnt_prev_able else prev_card_row[0],
                           isnt_next_able=isnt_next_able,
                           next_card_id="" if isnt_next_able else next_card_row[0])

def renumber_deck(deck_id):
    db_connection = get_db()
    cursor = db_connection.cursor()

    cursor.execute(
        "SELECT id FROM cards WHERE deckid = ? ORDER BY position ASC",
        (deck_id,)
    )
    cards = cursor.fetchall()

    try:
        for idx, card in enumerate(cards, start=1):
            cursor.execute("" \
                "UPDATE cards SET position = ? WHERE id = ?",
                (idx, card[0],)
            )
        db_connection.commit()
        return True
    except Exception as e:
        db_connection.rollback()
        print(f"Failed to renumber: {e}")


@app.route("/editcard/<int:card_id>", methods=["GET", "POST"])
@login_required
def editcard(card_id):
    db_connection = get_db()
    cursor = db_connection.cursor()

    # Get owning deck_id
    cursor.execute(
        "SELECT deckid FROM cards WHERE id = ?",
        (card_id,)
    )
    deckid_row = cursor.fetchone()
    if not deckid_row:
        flash("Card doesn't exist!")
        return redirect("/")
    deck_id = deckid_row[0]

    # Verify if the owner even has access (owns) to this deck
    cursor.execute(
        "SELECT title FROM decks WHERE id = ? AND ownerid = ?",
        (deck_id, session["userid"],)
    )

    deck_row = cursor.fetchone()
    if not deck_row:
        flash("Item cannot be accessed!")
        return redirect("/")
    
    if request.method == "GET":
        cursor.execute(
            "SELECT front, back FROM cards WHERE id = ?",
            (card_id,)
        )
        return render_template("editcard.html", card=cursor.fetchone(), card_id=card_id, deck_id=deck_id)
    
    elif request.method == "POST":
        front = request.form.get("front")
        back  = request.form.get("back")
        cursor.execute(
            "UPDATE cards SET front = ?, back = ? WHERE id = ?",
            (front, back, card_id,)
        )
        db_connection.commit()
        return redirect(f"/viewdeck/{deck_id}")
    
@app.route("/deletecard/<int:card_id>")
@login_required
def deletecard(card_id):
    db_connection = get_db()
    cursor = db_connection.cursor()

    # Get owning deck_id
    cursor.execute(
        "SELECT deckid FROM cards WHERE id = ?",
        (card_id,)
    )
    deckid_row = cursor.fetchone()
    if not deckid_row:
        flash("Card doesn't exist!")
        return redirect("/")
    deck_id = deckid_row[0]

    # Verify if the owner even has access (owns) to this deck
    cursor.execute(
        "SELECT title FROM decks WHERE id = ? AND ownerid = ?",
        (deck_id, session["userid"],)
    )

    deck_row = cursor.fetchone()
    if not deck_row:
        flash("Item cannot be accessed!")
        return redirect("/")
    
    cursor.execute(
        "DELETE FROM cards WHERE id = ?",
        (card_id,)
    )
    db_connection.commit()
    return redirect(f"/viewdeck/{deck_id}")
    

@app.route("/addcard/<int:after_id>")
@login_required
def addcard(after_id):
    # Add a card with a position of an average between the card before and after
    # then redirect to the /editcard page
    db_connection = get_db()
    cursor = db_connection.cursor()

    # Get owning deck_id
    cursor.execute(
        "SELECT deckid, position FROM cards WHERE id = ?",
        (after_id,)
    )
    deckid_row = cursor.fetchone()
    if not deckid_row:
        flash("Card doesn't exist!")
        return redirect("/")
    deck_id = deckid_row[0]

    # Verify if the owner even has access (owns) to this deck
    cursor.execute(
        "SELECT title FROM decks WHERE id = ? AND ownerid = ?",
        (deck_id, session["userid"],)
    )

    deck_row = cursor.fetchone()
    if not deck_row:
        flash("Item cannot be accessed!")
        return redirect("/")

    # Get position of card that came after it (the one before it the one we already fetched in the previous call)
    pre_position = deckid_row[1]
    cursor.execute(
        "SELECT position FROM cards WHERE position > ? AND deckid = ?",
        (pre_position, deck_id,)
    )
    post_position_row = cursor.fetchone()
    if post_position_row:
        post_position = post_position_row[0]
    else:
        post_position = pre_position + 2

    # New position is average
    new_position = (pre_position + post_position)/2

    cursor.execute(
        "INSERT INTO cards (deckid, front, back, position) VALUES (?, ?, ?, ?)",
        (deck_id, default_front_text, default_back_text, new_position,)
    )
    db_connection.commit()

    return redirect(f"/editcard/{cursor.lastrowid}")


@app.route("/addcardpost/<int:deck_id>")
def addcardpost(deck_id):
    db_connection = get_db()
    cursor = db_connection.cursor()

    # Verify if the owner even has access (owns) to this deck
    cursor.execute(
        "SELECT title FROM decks WHERE id = ? AND ownerid = ?",
        (deck_id, session["userid"],)
    )

    deck_row = cursor.fetchone()
    if not deck_row:
        flash("Item cannot be accessed!")
        return redirect("/")
    
    # Get the last position
    cursor.execute(
        "SELECT position FROM cards WHERE deckid = ? ORDER BY position DESC LIMIT 1",
        (deck_id,)
    )
    last_pos_row = cursor.fetchone()
    last_pos = last_pos_row[0] if last_pos_row else 0

    # Insert
    cursor.execute(
        "INSERT INTO cards (deckid, front, back, position) VALUES (?, ?, ?, ?)",
        (deck_id, default_front_text, default_back_text, last_pos + 1,)
    )
    db_connection.commit()

    return redirect(f"/editcard/{cursor.lastrowid}")

@app.route("/adddeck")
@login_required
def adddeck():
    db_connection = get_db()
    cursor = db_connection.cursor()

    try:
        cursor.execute(
            "INSERT INTO decks (ownerid, title) VALUES (?, ?)",
            (session["userid"], default_deck_title,)
        )
        db_connection.commit()
    except sqlite3.IntegrityError:
        flash(f"A deck with title: {default_deck_title} already exists!, please rename the existing one to a different name.")
        return redirect("/")
    
    return redirect(f"/viewdeck/{cursor.lastrowid}")

@app.route("/renamedeck", methods=["POST"])
@login_required
def renamedeck():
    deck_id = request.form.get("deck_id")
    title   = request.form.get("title")
    if not deck_id:
        flash("deck_id is empty, this is not possible in a normal scenario. report this to Pritam252 and try refreshing the page.")
        return '', 204
    if not title:
        flash("You must enter a title!")
        return '', 204
    
    db_connection = get_db()
    cursor = db_connection.cursor()

    # Verify if the owner even has access (owns) to this deck
    cursor.execute(
        "SELECT title FROM decks WHERE id = ? AND ownerid = ?",
        (deck_id, session["userid"],)
    )

    deck_row = cursor.fetchone()
    if not deck_row:
        flash("Item cannot be accessed!")
        return redirect("/")

    db_connection = get_db()
    cursor = db_connection.cursor()

    try:
        cursor.execute(
            "UPDATE decks SET title = ? WHERE id = ?",
            (title, deck_id,)
        )
        db_connection.commit()
    except sqlite3.IntegrityError:
        flash("Another deck with same title exists!")
        return '', 204
    
    return '', 204

@app.route("/deletedeck/<int:deck_id>")
@login_required
def deletedeck(deck_id):
    db_connection = get_db()
    cursor = db_connection.cursor()

    # Verify if the owner even has access (owns) to this deck
    cursor.execute(
        "SELECT title FROM decks WHERE id = ? AND ownerid = ?",
        (deck_id, session["userid"],)
    )

    deck_row = cursor.fetchone()
    if not deck_row:
        flash("Item cannot be accessed!")
        return redirect("/")
    
    cursor.execute(
        "DELETE FROM decks WHERE id = ?",
        (deck_id,)
    )
    db_connection.commit()

    return redirect("/")

@app.route("/importdecktsv", methods=["GET", "POST"])
@login_required
def importdecktsv():
    if request.method == "GET":
        return render_template("importdecktsv.html")
    elif request.method == "POST":
        if "file_upload" not in request.files:
            flash("No file selected")
            return redirect(request.url)
        
        file = request.files["file_upload"]

        if file.filename == '':
            flash("No selected file")
            return redirect(request.url)
        
        if not file:
            flash("File doesn't exist")
            return redirect(request.url)
        
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        reader = csv.reader(stream, delimiter='\t')

        db_connection = get_db()
        cursor = db_connection.cursor()

        deck_title_full = file.filename
        deck_title, _ext = os.path.splitext(deck_title_full)

        try:
            cursor.execute(
                "INSERT INTO decks (ownerid, title) VALUES (?, ?)",
                (session["userid"], deck_title,)
            )
            db_connection.commit()
        except sqlite3.IntegrityError:
            flash(f"A deck with title: {deck_title} already exists!, please rename the existing one to a different name.")
            return redirect(request.url)

        position = 0
        deck_id = cursor.lastrowid
        for row in reader:
            cursor.execute(
                "INSERT INTO cards (deckid, front, back, position) VALUES (?, ?, ?, ?)",
                (deck_id, row[0], row[1], position,)
            )
            position += 1

        db_connection.commit()
        return redirect(f"/viewdeck/{deck_id}")


@app.route("/processcards", methods=["POST"])
@login_required
def processcards():
    selected_ids = request.form.getlist("card_ids")
    if not selected_ids:
        return '', 204
    
    db_connection = get_db()
    cursor = db_connection.cursor()

    placeholders = ', '.join(['?'] * len(selected_ids))

    query = f"""
        SELECT COUNT(cards.id) 
        FROM cards
        JOIN decks ON cards.deckid = decks.id
        WHERE decks.ownerid = ? AND cards.id IN ({placeholders})"""

    params = [session["userid"]] + selected_ids
    cursor.execute(query, params)
    count = cursor.fetchone()[0]

    if count != len(selected_ids):
        flash("Item cannot be accessed!")
        return redirect("/")
    
    action = request.form.get("action")
    if action == "delete":
        cursor.execute(
            f"DELETE FROM cards WHERE id IN ({placeholders})",
            selected_ids
        )
        db_connection.commit()
        
    return redirect(request.referrer or "/")

@app.route("/importcards/<int:after_card_id>", methods=["GET", "POST"])
@login_required
def importcards(after_card_id):
    if request.method == "GET":
        return render_template("importcards.html", after_card_id=after_card_id)
    
    elif request.method == "POST":
        db_connection = get_db()
        cursor = db_connection.cursor()

        cursor.execute(
            """
            SELECT decks.ownerid, decks.id
            FROM cards
            JOIN decks ON cards.deckid = decks.id
            WHERE cards.id = ?
            """,
            (after_card_id,)
        )
        owner_row = cursor.fetchone()
        if not owner_row:
            flash("Card doesn't exist!")
            return redirect("/")
        if not owner_row[0] == session["userid"]:
            flash("Item cannot be accessed!")
            return redirect("/")
        deck_id = owner_row[1]

        if "file_upload" not in request.files:
            flash("No file selected")
            return redirect(request.url)
        
        file = request.files["file_upload"]

        if file.filename == '':
            flash("No selected file")
            return redirect(request.url)
        
        if not file:
            flash("File doesn't exist")
            return redirect(request.url)
        
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        reader = csv.reader(stream, delimiter='\t')

        # Find position of card before and after
        cursor.execute(
            "SELECT position FROM cards WHERE id = ?",
            (after_card_id,)
        )
        before_pos = cursor.fetchone()[0]
        cursor.execute(
            "SELECT position FROM cards WHERE position > ? ORDER BY position ASC LIMIT 1",
            (before_pos,)
        )

        # lazy fix for len(reader)
        reader_len = len(stream.getvalue().splitlines())

        after_pos_row = cursor.fetchone()
        after_pos = after_pos_row[0] if after_pos_row else before_pos + reader_len

        increment = (after_pos - before_pos) / reader_len
        curr_pos = before_pos + increment

        for row in reader:
            print(f"INSERT INTO cards (deckid, front, back, position) VALUES ({deck_id}, {row[0]}, {row[1]}, {curr_pos})")

            cursor.execute(
                "INSERT INTO cards (deckid, front, back, position) VALUES (?, ?, ?, ?)",
                (deck_id, row[0], row[1], curr_pos,)
            )
            curr_pos += increment

        db_connection.commit()
        return redirect(f"/viewdeck/{deck_id}")


@app.route("/importcardspost/<int:deck_id>", methods=["GET", "POST"])
@login_required
def importcardspost(deck_id):
    db_connection = get_db()
    cursor = db_connection.cursor()

    cursor.execute(
        "SELECT title FROM decks WHERE id = ? AND ownerid = ?",
        (deck_id, session["userid"],)
    )

    deck_row = cursor.fetchone()
    if not deck_row:
        flash("Item cannot be accessed!")
        return redirect("/")

    if request.method == "GET":
        return render_template("importcardspost.html", deck_id=deck_id, deck_title=deck_row[0])
    
    elif request.method == "POST":
        if "file_upload" not in request.files:
            flash("No file selected")
            return redirect(request.url)
        
        file = request.files["file_upload"]

        if file.filename == '':
            flash("No selected file")
            return redirect(request.url)
        
        if not file:
            flash("File doesn't exist")
            return redirect(request.url)
        
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        reader = csv.reader(stream, delimiter='\t')

        cursor.execute(
            "SELECT position FROM cards WHERE deckid = ? ORDER BY position DESC LIMIT 1",
            (deck_id,)
        )
        last_position_row = cursor.fetchone()
        curr_position = last_position_row[0] if last_position_row else 0

        for row in reader:
            cursor.execute(
                "INSERT INTO cards (deckid, front, back, position) VALUES (?, ?, ?, ?)",
                (deck_id, row[0], row[1], curr_position,)
            )
            curr_position += 1
        db_connection.commit()

        return redirect(f"/viewdeck/{deck_id}")

