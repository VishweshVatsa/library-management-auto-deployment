import pytest
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    return app.test_client()


def add_book(client, title="Clean Code", copies="1"):
    return client.post("/books", data={"title": title, "author": "R. Martin", "copies": copies},
                       follow_redirects=True)


def add_member(client, name="Asha", email="asha@example.com"):
    return client.post("/members", data={"name": name, "email": email}, follow_redirects=True)


def test_health(client):
    assert client.get("/health").get_json() == {"status": "ok"}


def test_add_book_shows_in_list(client):
    r = add_book(client)
    assert b"Clean Code" in r.data


def test_invalid_book_rejected(client):
    r = client.post("/books", data={"title": "", "author": "x", "copies": "1"}, follow_redirects=True)
    assert b"Enter a title" in r.data


def test_duplicate_member_email_rejected(client):
    add_member(client)
    r = add_member(client, name="Other")
    assert b"already exists" in r.data


def test_issue_and_return_flow(client):
    add_book(client)
    add_member(client)
    r = client.post("/issues", data={"book_id": 1, "member_id": 1}, follow_redirects=True)
    assert b"Issued" in r.data
    # only 1 copy, so a second issue must fail
    r = client.post("/issues", data={"book_id": 1, "member_id": 1}, follow_redirects=True)
    assert b"No copies" in r.data or b"Choose a book" in r.data
    r = client.post("/issues/1/return", follow_redirects=True)
    assert b"Book returned" in r.data


def test_cannot_delete_issued_book(client):
    add_book(client)
    add_member(client)
    client.post("/issues", data={"book_id": 1, "member_id": 1})
    r = client.post("/books/1/delete", follow_redirects=True)
    assert b"Return all copies" in r.data
