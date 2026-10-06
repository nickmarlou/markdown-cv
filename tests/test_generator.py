from pathlib import Path
import subprocess
import sys

import pymupdf
import pytest

ROOT = Path(__file__).resolve().parents[1]


def run_cv(tmp_path, markdown, existing=None):
    source = tmp_path / "input with spaces.md"
    source.write_text(markdown)
    output = tmp_path / "result.pdf"
    if existing:
        output.write_bytes(existing)
    result = subprocess.run(
        [sys.executable, str(ROOT / "generate.py"), str(source), "-o", str(output)],
        cwd=tmp_path, capture_output=True, text=True,
    )
    return result, output


def test_routing_unicode_links_and_order(tmp_path):
    result, output = run_cv(tmp_path, """---
name: Test Person
headline: Engineer
location: Lisbon
email: person@example.com
linkedin: https://www.linkedin.com/in/test-person
---

## Projects

Project first.

## Languages

- Русский *(Native)*

## Summary

Summary second.

""")
    assert result.returncode == 0, result.stderr
    with pymupdf.open(output) as doc:
        assert len(doc) == 1
        page = doc[0]
        assert tuple(page.rect) == (0, 0, 612, 792)
        assert page.search_for("Русский")[0].x0 < 202
        assert page.search_for("Projects")[0].x0 > 220
        assert page.search_for("Projects")[0].y0 < page.search_for("Summary")[0].y0
        assert "Page 1 of 1" in page.get_text()
        assert any(link.get("uri") == "mailto:person@example.com" for link in page.get_links())
        assert any(link.get("uri") == "https://www.linkedin.com/in/test-person" for link in page.get_links())
        assert page.search_for("Engineer")[0].x0 > 220
        assert page.search_for("Lisbon")[0].x0 > 220
        assert page.search_for("person@example.com")[0].x0 < 202


def test_frontmatter_contact_merges_with_extra_details(tmp_path):
    result, output = run_cv(tmp_path, """---
name: Test Person
email: person@example.com
---
## Contact

Phone: 123456789
""")
    assert result.returncode == 0, result.stderr
    with pymupdf.open(output) as doc:
        text = doc[0].get_text()
        assert text.count("Contact") == 1
        assert text.count("person@example.com") == 1
        assert "123456789" in text


def test_optional_frontmatter_omitted(tmp_path):
    result, output = run_cv(tmp_path, "---\nname: Person\n---\n## Summary\nHello.")
    assert result.returncode == 0, result.stderr
    with pymupdf.open(output) as doc:
        assert "Person" in doc[0].get_text()
        assert "Contact" not in doc[0].get_text()


@pytest.mark.parametrize("markdown,message", [
    ('---\nname: ""\n---\n', 'frontmatter "name"'),
    ('---\nname: [One, Two]\n---\n', 'single text value'),
    ('---\nname: One\nemail: {address: test@example.com}\n---\n', 'single text value'),
    ('---\nname: One\nlinkedin: linkedin.com/in/one\n---\n', 'full http:// or https:// URL'),
    ("## Summary\nText", 'frontmatter "name"'),
    ('---\nname: One\n---\n# Two', "put your name"),
    ("---\nname: One\n---\n## Summary\nA\n## SUMMARY\nB", "duplicate section"),
    ("---\nname: One\n---\n\nHeadline\n: A\n\nHeadline\n: B", "put identity fields"),
    ("---\nname: One\n---\n## Experience\n#### Engineer", "level-3"),
    ("---\nname: One\n---\n## Experience\n### Company", "level-4 role"),
    ("---\nname: One\n---\n## Experience\n### Company\n##### Engineer", "level-4"),
    ("---\nname: One\n---\n## Education\n#### University", "level-3"),
    ("---\nname: One\n---\n\nUnknown\n: Value", "put identity fields"),
])
def test_invalid_input_preserves_output(tmp_path, markdown, message):
    result, output = run_cv(tmp_path, markdown, existing=b"previous output")
    assert result.returncode != 0
    assert message in result.stderr
    assert output.read_bytes() == b"previous output"
    assert not list(tmp_path.glob(".cv-*"))


def test_sidebar_overflow_preserves_output(tmp_path):
    result, output = run_cv(
        tmp_path, "---\nname: Person\n---\n\n## Top Skills\n\n" + "- A skill\n" * 100,
        existing=b"previous output",
    )
    assert result.returncode != 0
    assert "Sidebar exceeds" in result.stderr
    assert output.read_bytes() == b"previous output"


def test_long_bullet_flows_and_sidebar_does_not_repeat(tmp_path):
    markdown = "---\nname: Person\n---\n\n## Contact\n\nSIDEBARONLY\n\n## Projects\n\n- "
    markdown += "A lengthy achievement with important details. " * 300
    markdown += "ENDMARKER\n"
    result, output = run_cv(tmp_path, markdown)
    assert result.returncode == 0, result.stderr
    with pymupdf.open(output) as doc:
        assert len(doc) > 1
        text = "".join(page.get_text() for page in doc)
        assert text.count("SIDEBARONLY") == 1
        assert "ENDMARKER" in text
        for i, page in enumerate(doc):
            assert f"Page {i + 1} of {len(doc)}" in page.get_text()
            assert any(
                drawing["fill"] and drawing["rect"].x0 == 0
                and abs(drawing["rect"].x1 - 201.96) < 0.1
                for drawing in page.get_drawings()
            )


def test_reference_example_and_text_bounds(tmp_path):
    result, output = run_cv(tmp_path, (ROOT / "input/profile.md").read_text())
    assert result.returncode == 0, result.stderr
    with pymupdf.open(output) as doc:
        text = "".join(page.get_text() for page in doc)
        for phrase in ("PandaDoc", "Senior Software Engineer II", "aisa.agency", "Master's degree", "Bachelor's degree"):
            assert phrase in text
        assert len(doc) == 3
        for page in doc:
            for word in page.get_text("words"):
                x0, y0, x1, y1 = word[:4]
                assert 0 <= x0 < x1 <= 612
                assert 0 <= y0 < y1 <= 792


def test_long_url_wraps_in_sidebar(tmp_path):
    url = "https://example.com/" + "longpath" * 18
    result, output = run_cv(tmp_path, f"---\nname: Person\n---\n\n## Contact\n\n[{url}]({url})\n")
    assert result.returncode == 0, result.stderr
    with pymupdf.open(output) as doc:
        for word in doc[0].get_text("words"):
            if word[0] < 202:
                assert word[2] <= 181
