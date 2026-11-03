import os
import sqlite3
from datetime import date

from flask import Flask, flash, g, redirect, render_template, request, url_for

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    copies INTEGER NOT NULL DEFAULT 1,
    available INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL REFERENCES books(id),
    member_id INTEGER NOT NULL REFERENCES members(id),
    issue_date TEXT NOT NULL,
    return_date TEXT
);
"""


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-only-change-me")
    app.config["DATABASE"] = db_path or os.getenv("DATABASE", "library.db")

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        get_db().executescript(SCHEMA)

    @app.route("/health")
    def health():
        return {"status": "ok"}

    @app.route("/")
    def dashboard():
        db = get_db()
        stats = {
            "books": db.execute("SELECT COUNT(*) FROM books").fetchone()[0],
            "members": db.execute("SELECT COUNT(*) FROM members").fetchone()[0],
            "issued": db.execute(
                "SELECT COUNT(*) FROM issues WHERE return_date IS NULL"
            ).fetchone()[0],
        }
        return render_template("dashboard.html", stats=stats)

    @app.route("/books", methods=["GET", "POST"])
    def books():
        db = get_db()
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            author = request.form.get("author", "").strip()
            copies = request.form.get("copies", "1")
            if not title or not author or not copies.isdigit() or int(copies) < 1:
                flash("Enter a title, an author and at least 1 copy.", "error")
            else:
                db.execute(
                    "INSERT INTO books (title, author, copies, available) VALUES (?,?,?,?)",
                    (title, author, int(copies), int(copies)),
                )
                db.commit()
                flash(f"Added '{title}'.", "ok")
            return redirect(url_for("books"))
        rows = db.execute("SELECT * FROM books ORDER BY title").fetchall()
        return render_template("books.html", books=rows)

    @app.post("/books/<int:book_id>/delete")
    def delete_book(book_id):
        db = get_db()
        out = db.execute(
            "SELECT COUNT(*) FROM issues WHERE book_id=? AND return_date IS NULL",
            (book_id,),
        ).fetchone()[0]
        if out:
            flash("Return all copies before deleting this book.", "error")
        else:
            db.execute("DELETE FROM issues WHERE book_id=?", (book_id,))
            db.execute("DELETE FROM books WHERE id=?", (book_id,))
            db.commit()
            flash("Book deleted.", "ok")
        return redirect(url_for("books"))

    @app.route("/members", methods=["GET", "POST"])
    def members():
        db = get_db()
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            if not name or "@" not in email:
                flash("Enter a name and a valid email.", "error")
            else:
                try:
                    db.execute(
                        "INSERT INTO members (name, email) VALUES (?,?)", (name, email)
                    )
                    db.commit()
                    flash(f"Added member {name}.", "ok")
                except sqlite3.IntegrityError:
                    flash("A member with this email already exists.", "error")
            return redirect(url_for("members"))
        rows = db.execute("SELECT * FROM members ORDER BY name").fetchall()
        return render_template("members.html", members=rows)

    @app.route("/issues", methods=["GET", "POST"])
    def issues():
        db = get_db()
        if request.method == "POST":
            book_id = request.form.get("book_id", type=int)
            member_id = request.form.get("member_id", type=int)
            book = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
            if not book or not member_id:
                flash("Choose a book and a member.", "error")
            elif book["available"] < 1:
                flash(f"No copies of '{book['title']}' are available.", "error")
            else:
                db.execute(
                    "INSERT INTO issues (book_id, member_id, issue_date) VALUES (?,?,?)",
                    (book_id, member_id, date.today().isoformat()),
                )
                db.execute(
                    "UPDATE books SET available = available - 1 WHERE id=?", (book_id,)
                )
                db.commit()
                flash(f"Issued '{book['title']}'.", "ok")
            return redirect(url_for("issues"))
        rows = db.execute(
            """SELECT i.id, i.issue_date, i.return_date, b.title, m.name
               FROM issues i JOIN books b ON b.id=i.book_id
               JOIN members m ON m.id=i.member_id
               ORDER BY i.return_date IS NOT NULL, i.issue_date DESC"""
        ).fetchall()
        available = db.execute(
            "SELECT * FROM books WHERE available > 0 ORDER BY title"
        ).fetchall()
        people = db.execute("SELECT * FROM members ORDER BY name").fetchall()
        return render_template("issues.html", issues=rows, books=available, members=people)

    @app.post("/issues/<int:issue_id>/return")
    def return_book(issue_id):
        db = get_db()
        row = db.execute(
            "SELECT * FROM issues WHERE id=? AND return_date IS NULL", (issue_id,)
        ).fetchone()
        if row:
            db.execute(
                "UPDATE issues SET return_date=? WHERE id=?",
                (date.today().isoformat(), issue_id),
            )
            db.execute(
                "UPDATE books SET available = available + 1 WHERE id=?",
                (row["book_id"],),
            )
            db.commit()
            flash("Book returned.", "ok")
        return redirect(url_for("issues"))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
