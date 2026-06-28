from lewisham_server.startup_banner import CROWN, PANEL_WIDTH, print_startup_banner


def test_text_logging_prints_crown_panel_and_server_identity(capsys) -> None:
    print_startup_banner("text", app_version="1.2.3")

    captured = capsys.readouterr()

    assert captured.err == ""
    assert "Lewisham Council Scraper" in captured.out
    assert "API Server · v1.2.3" in captured.out
    assert "╭" in captured.out
    assert "╯" in captured.out
    assert all(line in captured.out for line in CROWN.splitlines())
    assert len(CROWN.splitlines()) == 34
    assert max(len(line) for line in CROWN.splitlines()) == 94
    assert max(len(line) for line in captured.out.splitlines()) == PANEL_WIDTH


def test_json_logging_does_not_print_crown(capsys) -> None:
    print_startup_banner("json", app_version="1.2.3")

    captured = capsys.readouterr()

    assert captured.out == ""
    assert captured.err == ""
