import json
from pathlib import Path

import pytest
import requests

from newstracker import config, db, llm
from newstracker.cli import main

SAMPLE = Path(__file__).parent.parent / "sample_data" / "real_amzn.json"


class FakeResponse:
    def __init__(self, status_code=200, body=None):
        self.status_code, self._body = status_code, body

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


def ok(text):
    return FakeResponse(200, {"choices": [{"message": {"content": text}}]})


@pytest.fixture
def conn(tmp_path):
    conn = db.connect(str(tmp_path / "test.db"))
    articles = json.loads(SAMPLE.read_text(encoding="utf-8"))["results"]
    db.save_articles(conn, articles)
    db.tag_articles(conn)
    yield conn
    conn.close()


@pytest.fixture(autouse=True)
def key(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "test-openai-key")


def test_sends_the_question_and_only_that_companys_stories(conn):
    sent = {}

    def post(url, headers, json, timeout):
        sent.update(url=url, headers=headers, body=json)
        return ok("  Amazon coverage is mostly deals.  ")

    result = llm.answer_with_llm(conn, "Did Amazon announce layoffs?", post=post)

    assert result == "Amazon coverage is mostly deals."
    assert sent["url"] == config.OPENAI_URL
    assert sent["headers"]["Authorization"] == "Bearer test-openai-key"
    assert sent["body"]["model"] == config.OPENAI_MODEL
    prompt = sent["body"]["messages"][1]["content"]
    assert "Did Amazon announce layoffs?" in prompt
    assert "Hanes" in prompt and "earbuds" in prompt
    assert "adidas" not in prompt  # stored, but never linked to Amazon


def test_a_question_naming_two_companies_includes_both(conn):
    prompts = []

    def post(url, headers, json, timeout):
        prompts.append(json["messages"][1]["content"])
        return ok("answer")

    llm.answer_with_llm(conn, "Compare Amazon and Walmart", post=post)

    assert "Articles about Amazon" in prompts[0]
    assert "Articles about Walmart" in prompts[0]


def test_no_request_when_there_is_nothing_to_send(conn):
    def post(*args, **kwargs):
        raise AssertionError("should not call the API")

    assert "No articles about Linde" in llm.answer_with_llm(conn, "News on Linde?", post=post)
    assert "couldn't tell which company" in llm.answer_with_llm(conn, "How is Tesla?", post=post)


def test_missing_key_raises_without_calling_the_api(conn, monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", None)

    def post(*args, **kwargs):
        raise AssertionError("should not call the API")

    with pytest.raises(llm.LLMError, match="OPENAI_API_KEY is not set"):
        llm.answer_with_llm(conn, "News on Amazon?", post=post)


def test_api_error_message_is_reported_without_the_key(conn):
    body = {"error": {"message": "You exceeded your current quota"}}

    with pytest.raises(llm.LLMError) as error:
        llm.answer_with_llm(conn, "News on Amazon?", post=lambda *a, **k: FakeResponse(429, body))

    assert "HTTP 429: You exceeded your current quota" in str(error.value)
    assert "test-openai-key" not in str(error.value)


def test_network_error_and_bad_responses_raise(conn):
    def unreachable(*args, **kwargs):
        raise requests.ConnectionError("boom with test-openai-key in it")

    with pytest.raises(llm.LLMError) as error:
        llm.answer_with_llm(conn, "News on Amazon?", post=unreachable)
    assert str(error.value) == "ConnectionError"

    for bad in (FakeResponse(200, {"unexpected": 1}), FakeResponse(200, None), ok("   ")):
        with pytest.raises(llm.LLMError):
            llm.answer_with_llm(conn, "News on Amazon?", post=lambda *a, **k: bad)


def test_cli_does_not_use_the_model_unless_asked(tmp_path, capsys, monkeypatch):
    path = str(tmp_path / "cli.db")
    conn = db.connect(path)
    db.save_articles(conn, json.loads(SAMPLE.read_text(encoding="utf-8"))["results"])
    db.tag_articles(conn)
    conn.close()
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: pytest.fail("API called"))

    main(["--db", path, "ask", "What has the news said about Amazon?"])

    assert "Amazon: 2 stories collected" in capsys.readouterr().out


def test_cli_falls_back_to_the_rule_based_summary(tmp_path, capsys, monkeypatch):
    path = str(tmp_path / "cli.db")
    conn = db.connect(path)
    db.save_articles(conn, json.loads(SAMPLE.read_text(encoding="utf-8"))["results"])
    db.tag_articles(conn)
    conn.close()
    monkeypatch.setattr(config, "OPENAI_API_KEY", None)

    main(["--db", path, "ask", "--llm", "What has the news said about AMZN?"])

    out = capsys.readouterr().out
    assert "Language model unavailable (OPENAI_API_KEY is not set)" in out
    assert "Amazon: 2 stories collected" in out


def test_cli_prints_the_model_answer(tmp_path, capsys, monkeypatch):
    path = str(tmp_path / "cli.db")
    conn = db.connect(path)
    db.save_articles(conn, json.loads(SAMPLE.read_text(encoding="utf-8"))["results"])
    db.tag_articles(conn)
    conn.close()
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: ok("Mostly Black Friday deals."))

    main(["--db", path, "ask", "--llm", "What has the news said about AMZN?"])

    assert capsys.readouterr().out.strip() == "Mostly Black Friday deals."
