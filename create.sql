CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    username TEXT NOT NULL,
    passhash TEXT NOT NULL
);

CREATE UNIQUE INDEX username ON users (username);

CREATE TABLE decks (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    ownerid INTEGER NOT NULL,
    title TEXT NOT NULL,
    FOREIGN KEY (ownerid) REFERENCES users (id) ON DELETE CASCADE
);

-- Useful for searching (we search using title)
CREATE INDEX idx_title ON decks(title);

-- Makes sure that the whole thing is sorted by ownerid then title
-- and 2 decks cannot have the same owner and same title
CREATE UNIQUE INDEX ownerid_title_unique ON decks (ownerid, title);

CREATE TABLE cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    deckid INTEGER NOT NULL,
    front TEXT NOT NULL,
    back TEXT NOT NULL,
    position REAL NOT NULL,
    -- I used real because then i can shift cards around and then renumber everything upon saving instead
    FOREIGN KEY (deckid) REFERENCES decks (id) ON DELETE CASCADE
);

-- Many cards can have the same deckid
CREATE INDEX idx_cards_deckid ON cards(deckid);