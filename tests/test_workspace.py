import pathlib

from runtime.workspace import EphemeralWorkspace


def test_ephemeral_workspace_copies_and_cleans(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "demo.txt").write_text("ok", encoding="utf-8")

    ws = EphemeralWorkspace(str(src))
    with ws as workdir:
        assert pathlib.Path(workdir).joinpath("demo.txt").exists()
        temp_dir = pathlib.Path(ws.temp_dir)

    assert not temp_dir.exists()
