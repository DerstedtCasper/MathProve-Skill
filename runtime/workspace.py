"""Ephemeral workspace for Lean project execution."""
import argparse
import os
import shutil
import tempfile
from dataclasses import dataclass


@dataclass
class EphemeralWorkspace:
    source_dir: str
    temp_dir: str | None = None
    project_dir: str | None = None

    def __enter__(self) -> str:
        self.temp_dir = tempfile.mkdtemp(prefix="mathprove_")
        self.project_dir = os.path.join(self.temp_dir, "proj")
        shutil.copytree(
            self.source_dir,
            self.project_dir,
            ignore=shutil.ignore_patterns(
                "build",
                "lake-packages",
                "__pycache__",
                "*.olean",
                "*.class",
                ".git*",
            ),
        )
        return self.project_dir

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.temp_dir and os.path.isdir(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create ephemeral workspace")
    parser.add_argument("source_dir", help="Lean project directory")
    args = parser.parse_args()
    with EphemeralWorkspace(args.source_dir) as workdir:
        print(workdir)


if __name__ == "__main__":
    main()
