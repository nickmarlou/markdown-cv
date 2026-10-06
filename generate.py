"""Generate professional, two-column CV PDFs from Markdown with Pandoc and WeasyPrint."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent


def generate(source: Path, output: Path) -> None:
    source, output = source.resolve(), output.resolve()
    if not source.is_file():
        raise ValueError(f"Input file does not exist: {source}")
    if source == output:
        raise ValueError("Input and output must be different files")
    if output.suffix.lower() != ".pdf":
        raise ValueError("Output must have a .pdf extension")
    pandoc = shutil.which("pandoc")
    engine = Path(sys.executable).parent / "weasyprint"
    if not pandoc:
        raise ValueError("Pandoc is missing. Install it and ensure it is on PATH.")
    if not engine.is_file():
        raise ValueError("WeasyPrint is missing. Run uv sync, then use uv run python generate.py.")
    # Fontconfig needs a writable cache, including in sandboxed environments.
    os.environ.setdefault("XDG_CACHE_HOME", str(ROOT / ".cache"))
    if sys.platform == "darwin" and "DYLD_FALLBACK_LIBRARY_PATH" not in os.environ:
        # uv's Python does not automatically search Homebrew's native libraries.
        os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = ":".join(
            str(path) for path in (Path("/opt/homebrew/lib"), Path("/usr/local/lib"))
            if path.is_dir()
        )
    from weasyprint import HTML

    common = [
        pandoc, str(source), "--from=markdown-raw_html-raw_tex-smart-blank_before_header", "--to=html5",
        "--standalone", f"--lua-filter={ROOT / 'filters/cv.lua'}",
        f"--template={ROOT / 'templates/linkedin.html'}",
        f"--css={(ROOT / 'styles/linkedin.css').as_uri()}",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".cv-", dir=output.parent) as scratch:
        html_path = Path(scratch) / "cv.html"
        pdf_path = Path(scratch) / "cv.pdf"
        subprocess.run(common + ["--output", str(html_path)], check=True, cwd=source.parent)
        document = HTML(filename=str(html_path), base_url=str(source.parent)).render()
        anchors = [
            (i, page.anchors["cv-sidebar-end"])
            for i, page in enumerate(document.pages)
            if "cv-sidebar-end" in page.anchors
        ]
        # WeasyPrint anchor coordinates are CSS pixels, measured from the page top.
        limit = (792 - 36) * 96 / 72
        if len(anchors) != 1 or anchors[0][0] != 0 or anchors[0][1][1] > limit:
            raise ValueError("Sidebar exceeds the first-page area. Shorten Contact, Top Skills, Languages, or Certifications.")
        subprocess.run(
            common + [f"--pdf-engine={engine}", "--output", str(pdf_path)],
            check=True, cwd=source.parent,
        )
        os.replace(pdf_path, output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Structured Markdown CV")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Destination PDF")
    args = parser.parse_args()
    try:
        generate(args.input, args.output)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Created {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
