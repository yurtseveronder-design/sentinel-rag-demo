import pytest

from rag_demo import cli


def test_missing_documents_fail_loudly(tmp_path, capsys):
    assert cli.main(["hello", "--unprotected", "--docs", str(tmp_path)]) == 2
    assert "no documents found" in capsys.readouterr().err


def test_unprotected_run_answers_from_the_documents(capsys):
    assert cli.main(["--unprotected"]) == 0
    assert "1.2 million" in capsys.readouterr().out
