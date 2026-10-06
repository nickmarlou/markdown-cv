# markdown-cv

Generate professional, two-column CV PDFs from Markdown using **Pandoc +
WeasyPrint**. The layout uses US Letter paper, a dark sidebar,
grouped employment history, and page-number footers. The sidebar appears only on
page one; its background continues on every page.

## Quickstart

### Install dependencies

```sh
brew install uv pandoc pango
uv sync
```

### Generate

Copy `input/template.md` to start a CV. `input/profile.md` transcribes the supplied
reference, retaining its authored wording and durations. Run the same command with
your own input and output paths. Paths containing spaces are supported, and the
generator can be invoked from another directory using its absolute path.

```sh
uv run python generate.py input/profile.md -o output/profile.pdf
```

## Markdown contract

Start with YAML frontmatter. `name` is required; the other fields are optional.
Use lowercase keys and a full URL for `linkedin`:

```markdown
---
name: Your Name
headline: Senior Software Engineer
location: City, Country
email: you@example.com
linkedin: https://www.linkedin.com/in/yourname
---
```

Name, headline, and location appear at the top of the main column. Email and
LinkedIn become clickable links in the sidebar's Contact section. If you include
`## Contact` for a phone number or other details, the generated links follow that
content. Otherwise, Contact is inserted at the top of the sidebar. No empty Contact
section is generated when both links are omitted. Quote YAML values containing
special syntax, such as `headline: "Engineer: Platform"`.

The body starts with `##` sections; the former name heading and identity definition
lists are no longer accepted. Definition lists remain supported for employment and
education fields.

Level-two headings select the layout area, regardless of where they occur in the
source. Matching is case-insensitive; headings keep their original display text.

| Heading | Layout and contents |
| --- | --- |
| `## Contact` | Sidebar; optional additional contact details, followed by frontmatter links |
| `## Skills` or `## Top Skills` | Sidebar; a list displayed without bullets |
| `## Languages` | Sidebar; a list; italic text renders as muted proficiency labels |
| `## Certifications` | Sidebar; a list displayed without bullets |
| `## Summary` | Main column; larger introductory body text |
| `## Experience` | Main column; employers and roles as shown below |
| `## Education` | Main column; institutions and qualifications as shown below |
| Any other `## Heading` | Main column; ordinary Markdown, including subheadings |

Sections retain their source order **within each column**. All sections are optional,
but section names must be unique. Omitted sections leave no placeholder. Use Markdown
links for clickable email addresses, telephone numbers, and web addresses. Two
trailing spaces create a hard line break. Raw HTML and raw TeX are disabled.

Experience uses level-three employer headings and one or more level-four role
headings. Employer `Duration` is optional. Role `Dates`, `Duration`, and `Location`
are optional; write achievements as paragraphs or bullet lists after the fields.

```markdown
## Experience

### Company

Duration
: 5 years

#### Senior Software Engineer

Dates
: January 2023 - Present

Duration
: 3 years

Location
: Lisbon, Portugal

- Delivered a measurable improvement.

#### Software Engineer

Dates
: January 2021 - December 2022

- Built and maintained a service.
```

Education uses level-three institution headings with optional `Degree`, `Dates`, and
`Location` fields. Repeat the institution heading for another qualification.

```markdown
## Education

### University

Degree
: Bachelor's degree, Computer Science

Dates
: September 2015 - June 2019
```

Employment and education field labels are case-insensitive. Each field takes one definition; duplicate or
unknown fields in structured entries are errors. Identity fields are plain display
text. Dates and durations remain exactly as authored; the generator does not infer
them or update `Present` durations.

## Layout and errors

- `templates/linkedin.html` defines the document's layout slots.
- `styles/linkedin.css` controls page dimensions, columns, typography, colors,
  spacing, pagination, and footers.
- `filters/cv.lua` maps the Markdown syntax to semantic HTML and template fields.
- `generate.py` runs Pandoc, checks the first-page sidebar using a WeasyPrint
  preflight render, and invokes Pandoc with WeasyPrint as its PDF engine.

The sidebar must fit above the footer on page one. Overflow produces an error asking
you to shorten it; content is never silently clipped or reduced to a smaller font.
The main column flows across pages and can split long descriptions. Headings stay
with following content where possible.

Missing dependencies, invalid Markdown structure, and rendering failures return a
nonzero exit status. A failed generation leaves an existing destination PDF intact.
Temporary generation files are cleaned up automatically. PDFs, local caches, and
the virtual environment are ignored by Git. Native library locations under standard
Homebrew prefixes are detected automatically on macOS.

## Verify

```sh
uv sync
uv run pytest -q
```

Tests cover section routing, grouping, invalid input, Unicode, links, pagination,
sidebar overflow, long URLs, and preserving existing output on failure. The reference
example is also visually reviewed page by page for layout fidelity. PyMuPDF and
pytest are development dependencies; runtime-only installs can use `uv sync --no-dev`.
