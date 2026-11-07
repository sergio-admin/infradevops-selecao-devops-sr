from fastapi.testclient import TestClient

import main


class FakeCursor:
    lastrowid = 1

    def __init__(self, rows=None):
        self.rows = rows or []
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchall(self):
        return self.rows

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


client = TestClient(main.app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_comment(monkeypatch):
    cursor = FakeCursor()
    monkeypatch.setattr(main, "get_connection", lambda: FakeConnection(cursor))
    payload = {"email": "a@b.com", "comment": "teste", "content_id": 1}
    response = client.post("/api/comment/new", json=payload)
    assert response.status_code == 201
    assert response.json()["id"] == 1
    assert cursor.executed[0][1] == ("a@b.com", "teste", 1)


def test_create_comment_invalid_email():
    payload = {"email": "invalido", "comment": "teste", "content_id": 1}
    response = client.post("/api/comment/new", json=payload)
    assert response.status_code == 422


def test_list_comments(monkeypatch):
    rows = [{"id": 1, "email": "a@b.com", "comment": "x", "content_id": 7}]
    cursor = FakeCursor(rows)
    monkeypatch.setattr(main, "get_connection", lambda: FakeConnection(cursor))
    response = client.get("/api/comment/list/7")
    assert response.status_code == 200
    assert response.json() == rows
    assert cursor.executed[0][1] == (7,)


def test_ready_without_database(monkeypatch):
    def fail():
        raise Exception("sem banco")

    monkeypatch.setattr(main, "get_connection", fail)
    response = client.get("/ready")
    assert response.status_code == 503


def test_metrics():
    client.get("/health")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
