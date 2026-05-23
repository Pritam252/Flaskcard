# Flaskcard App

A simple flashcard app written using Python and Flask (and also Bootstrap for styling).

It is my CS50x final project.




## How to run in debug:

- Make sure Python is installed (as far as I know, it at least has to support f-strings and Flask.)

- Run `python -m pip install -r requirements.txt` to install dependencies.

- Run `python -m flask run` to run in debug.

You can directly run `pip` and `flask` directly if you have it set up directly.




## Features:

- Import from TSV format

- Separated user account isolation

- Password changing




## TODO (Soon):

- Implement export to TSV

- Changing the order of cards

- Random shuffling of cards during revision

- "To review" page (tracks when the user should revise again)




## Used frameworks / libraries:

- Python

- Flask (and Werkzeug for the Security module)

- Flask-Session

- Sqlite3

- Client-side HTML, CSS, and JavaScript




## Internals:

There's an SQLite3 database (`data.db`).

The database stores 3 tables: `users`, `products`, and `orders`.




The `users` table stores each user's data:

- `id`: Their unique integer ID.

- `username`: Their unique username.

- `passhash`: Their password's hash (calculated using `Werkzeug Security`'s `generate_password_hash`)

The users system uses Flask-Session to store user login.




The `decks` table stores metadata of each deck. (Though not the actual card data.):

- `id`: The deck's unique integer ID.

- `ownerid`: The ID of the owner.

- `title`: The title of the deck.




And most importantly, the `cards` table, which stores the actual cards.

- `id`: The card's unique integer ID.

- `deckid`: The ID of the deck that the card is part of.

- `front`: The front text of the card.

- `back`: The back text of the card.

- `position`: The position of the card in the deck.

Because I wanted to be able to insert cards between other cards dynamically,

(and in the future expand it to a full drag-and-drop feature), a REAL type was chosen

for `position`.

To insert `n` cards between card `a` and card `b` (where `a.position` < `b.position`),

We just have to add a card every `(b.position - a.position) / n` starting after `a`.




The schema of the database is in `data.db`, or you can use the `.schema` command to view it as well.




### Source files & Explaination:

- `helpers.py`: Has the `@login_required` annotation from CS50 finance assignment.

- `app.py`: The main app, contains all the app's routes.

- `create.sql`: SQL Commands for creating the `data.db` file.

- `data.db`: SQLite3 database for storing all the flashcards.

- `templates/card.html`: The card view. (for reviewing)

- `templates/deck.html`: The deck view. (summary of all cards in the deck)

- `templates/editcard.html`: The card editing view.

- `templates/importcards.html`: The page for importing cards to be inserted into the deck after a certain card.

- `templates/importcardspost.html`: The page for importing cards to be appended to the end of the deck.

- `templates/importdecktsv.html`: The page for importing cards into a new deck.

- `templates/index.html`: The home page.

- `templates/layout.html`: The layout template.

- `templates/login.html`: The login page.

- `templates/passchange.html`: The password change page.

- `templates/register.html`: The registration page.

- `static/styles.css`: The app's stylesheet.




## Credits:

Thanks to the user login code and the `layout.html` code from the finance app from CS50x,

Gemini for overall styling (CSS), and the idea behind using REAL datatype for `position`.