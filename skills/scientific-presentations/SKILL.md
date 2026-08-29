---
name: scientific-presentations
description: Design and deliver scientific talks and posters with one-idea-per-slide layouts, visual hierarchy, and large high-contrast figures. Use Quarto revealjs, Beamer, Marp markdown, and matplotlib for talk figures, plus A0 poster layouts. Covers conference timing, accessibility (alt text, captions), and recording/export. Triggers include "slides", "talk", "Quarto revealjs", "Beamer", "Marp", "poster A0", "conference talk", "matplotlib talk figure".
license: MIT
compatibility: Requires Python 3.10+ with matplotlib, jinja2, pandoc, Quarto CLI 1.5+, and a TeX distribution for Beamer/PDF export. For web export (revealjs, Marp) Chromium is needed for PDF snapshots.
metadata:
  version: "1.0.0"
  skill-author: Scientific Agent Skills Contributors
  category: Knowledge & Communication
---

# Scientific Presentations

## Overview

A scientific talk is a deliberately narrow argument for a deliberately
narrow audience, expressed in pictures more than words. A poster is the
same idea in static print, designed for walking readers who spend 30-90
seconds before deciding to stop. This skill covers the pipeline:

1. **Plan** the talk around a single takeaway sentence, then build a
   narrative arc (motivation -> question -> data -> result -> conclusion).
2. **Choose a stack**: Quarto `revealjs` for the web, Beamer for academic
   PDFs, Marp for fast markdown-to-PDF, plain HTML/CSS for fully custom.
3. **Make figures for the talk, not the paper**: bigger fonts, fewer
   panels, higher contrast, single-message plots.
4. **Design posters** on A0 with a multi-column layout and a "hero
   figure" up top.
5. **Rehearse timing**: 1 slide per 30-90 s for a talk, no more than
   1 slide per minute for unfamiliar audiences.
6. **Add accessibility** throughout: alt text on every figure, captions
   on videos, color-blind-safe palettes, contrast-checked colors.
7. **Export and record**: PDF for the venue, MP4 for sharing, subtitles
   for social and accessibility.

## When to use this skill

- You are preparing a **conference talk** (15/20/30 min + Q&A).
- You are preparing a **poster** for a session.
- You need a **lecture** deck for a course or workshop.
- You need a **keynote or plenary** talk.
- You need to **record** a talk for an online conference.
- You need to **make accessible slides** (alt text, captions, contrast).
- You need to **regenerate figures** for the talk that differ from the
  paper figures (larger fonts, fewer panels).

Do NOT use this skill for manuscripts (use `scientific-writing`) or
grant applications (use `grant-writing`).

## Prerequisites

- Python 3.10 or newer.
- Libraries:
  ```bash
  pip install matplotlib jinja2
  ```
- Quarto CLI 1.5+ (https://quarto.org/docs/download/) for `revealjs`.
- TeX distribution with `beamer` (in `texlive-full` or `texlive-latex-extra`).
- Pandoc 3+ for format conversion.
- (Optional) Marp CLI: `npm i -g @marp-team/marp-cli`.
- (Optional) Chromium for HTML-to-PDF export of revealjs/Marp.

## Core workflows

### 1. Quarto revealjs skeleton (web-talk)

```yaml
---
title: "Effect of X on Y"
author: "Ada Lovelace"
format:
  revealjs:
    theme: simple
    transition: slide
    slide-number: true
    width: 1280
    height: 720
    footer: "Lovelace et al. 2025"
    chalkboard: true
    preview-link: true
bibliography: refs.bib
execute: { echo: false, warning: false }
---
```

```markdown
# One takeaway sentence
## {{< frag >}}Add one sentence the audience repeats next week.{{</ frag >}}

# Why this matters
- Gap in the field
- Cost of the gap
- Who pays

# The question
![](figures/hero.png){.r-stretch}

# Data
```{python}
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(8, 5))
ax.bar(['Control', 'X'], [4.1, 6.2]); plt.savefig("figures/main.png")
```

# Result
One sentence. One figure.

# Conclusion
- What we know now
- What we still don't know
- What's next
```

Render: `quarto render talk.qmd --to revealjs` (HTML5) or
`quarto render talk.qmd --to pdf` (PDF via Chromium).

### 2. Beamer (academic PDF)

```python
from pylatex import Document, Section
doc = Document("talk", documentclass="beamer",
              document_options=["aspectratio=169","11pt"],
              preamble=r"\usetheme{metropolis}\usepackage{graphicx}")
with doc.create(Section("One takeaway")):
    doc.append("The audience should leave with this sentence.")
doc.generate_pdf("talk", clean=False)
```

### 3. Marp markdown to PDF

```markdown
---
marp: true
theme: default
size: 16:9
paginate: true
footer: "Lovelace 2025"
---
# One takeaway sentence
---
# Why this matters
- Gap
- Cost
- Who pays
---
# Result
![w:800](figures/main.png)
```

Render: `marp talk.md -o talk.pdf --pdf` (needs Chromium) or
`marp talk.md -o talk.pptx`.

### 4. matplotlib talk figure (large fonts, high contrast)

```python
import matplotlib.pyplot as plt
import matplotlib as mpl
mpl.rcParams.update({
    "font.size": 22, "axes.titlesize": 22, "axes.labelsize": 20,
    "xtick.labelsize": 18, "ytick.labelsize": 18,
    "figure.figsize": (10, 6), "figure.dpi": 150,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.prop_cycle": mpl.cycler(
        color=["#1b9e77", "#d95f02", "#7570b3"])  # ColorBrewer Set2
})
fig, ax = plt.subplots()
ax.bar(["Control", "Drug X"], [4.1, 6.2],
       yerr=[0.3, 0.4], capsize=8, color=["#7570b3", "#d95f02"])
ax.set_ylabel("Outcome (a.u.)")
ax.set_title("Drug X improves outcome")
fig.tight_layout()
fig.savefig("figures/main.png", dpi=200, bbox_inches="tight")
```

### 5. A0 poster layout (Python + HTML/CSS or LaTeX)

```python
from jinja2 import Template
tpl = Template("""<!doctype html><html><head><style>
@page { size: 841mm 1189mm; margin: 0; }
body { width: 841mm; height: 1189mm; margin: 0;
       font-family: 'Helvetica'; font-size: 36pt; }
header { background:#1b3a4b; color:#fff; padding:30mm 20mm; }
.grid { display:grid; grid-template-columns:1fr 1fr 1fr;
        gap:20mm; padding:20mm; }
img { width:100%; }
</style></head><body>
<header><h1>{{ title }}</h1>
<p>{{ authors }} - {{ affiliations }}</p></header>
<div class="grid">
  <section><h2>Background</h2><p>{{ bg }}</p>
          <img src="figures/hero.png" alt="Hero figure: ..."></section>
  <section><h2>Methods</h2><p>{{ methods }}</p></section>
  <section><h2>Results</h2><p>{{ results }}</p>
          <img src="figures/main.png" alt="Main result bar chart"></section>
</div>
</body></html>""")
open("poster.html","w").write(tpl.render(
    title="Effect of X on Y",
    authors="Lovelace A., Turing A., Curie M.",
    affiliations="Example University, MIT, Sorbonne",
    bg="...", methods="...", results="..."))
# Render to PDF: chromium --headless --disable-gpu \
#   --print-to-pdf=poster.pdf poster.html
```

## Best practices

- **One idea per slide.** If you find yourself writing "and also" on a
  slide, split it.
- **Takeaway sentence first.** Decide the single sentence your audience
  should repeat next week; build every slide to defend it.
- **Figures first, words second.** A talk is slides plus speech, not
  slides with speech.
- **Bigger fonts.** Title 36 pt+, body 24 pt+, axis labels 18 pt+. If
  it cannot be read from the back row, it does not exist.
- **Use a color-blind-safe palette** (e.g., ColorBrewer Set2, Okabe-Ito)
  and **check contrast** against the background (WCAG AA: 4.5:1 for body,
  3:1 for large text).
- **Alt text on every figure** ("Bar chart of outcome by treatment;
  Drug X mean 6.2, control 4.1"). It is required for accessibility and
  helps the speaker prepare.
- **Time yourself.** A 30 min slot has ~25 min of talk + 5 of Q&A;
  rehearse with a timer and cut 20%.
- **Slide count rule**: 1 slide per 1-1.5 min for unfamiliar audiences;
  up to 1 per 30 s for friendly ones.
- **Posters**: hero figure on top third, ~250-400 words total, QR code
  to a 1-page PDF for walk-up readers.
- **Record and post.** Record the talk with OBS or Zoom, burn
  subtitles with Whisper, post on the lab website and a CC-BY license.

## Common pitfalls

- Default matplotlibrc fonts that look fine in a paper render unreadable
  on a projector — bump font sizes to 18+ pt and DPI to 150+.
- Paper figures copy-pasted into slides: too many panels, axes
  illegible, no takeaway sentence.
- Animations that "fly in" every bullet: distracting and slow.
- "Don't read the slide" violated by slides that are paragraphs.
- Color choices like red/green that are unreadable for ~5% of men
  (deuteranopia).
- No alt text or no captions; inaccessible to screen readers and to
  the room's audio listeners.
- 60 slides for a 15 min talk; the speaker races through the last 20.
- No PDF export; a venue without HDMI for the live web app crashes the
  talk. Always export a PDF backup.
- Tiny QR codes that the audience cannot scan from the back row.
- Forgetting to test on the projector: colors render very differently
  than on a laptop screen.

## Worked example

A 20 min conference talk: "Microglial senescence in early Alzheimer's
disease." Built with Quarto revealjs, with one matplotlib talk figure
and one poster derived from the same data.

```python
# make_figure.py
import matplotlib as mpl, matplotlib.pyplot as plt
mpl.rcParams.update({"font.size": 22, "axes.spines.top": False,
                     "axes.spines.right": False})
fig, ax = plt.subplots(figsize=(10, 6))
ax.bar(["Ctrl", "TREM2-/-"], [4.1, 7.8], yerr=[0.4, 0.6], capsize=10,
       color=["#7570b3", "#d95f02"])
ax.set_ylabel("Senescent microglia (%)\n")
ax.set_title("TREM2 loss drives senescence")
fig.tight_layout()
fig.savefig("figures/main.png", dpi=200, bbox_inches="tight")
```

```markdown
---
title: "Microglial senescence in early Alzheimer's disease"
author: "Ada Lovelace"
format:
  revealjs:
    theme: simple
    transition: slide
    slide-number: true
    width: 1280
    height: 720
bibliography: refs.bib
---

# Takeaway
## Microglia enter a senescent state years before symptoms, and TREM2 is the switch.

# Why it matters
- AD is silent for decades
- Current drugs target the wrong window
- A 5-year-earlier biomarker could change trials

# The question
![](figures/hero.png){.r-stretch}
Are senescent microglia enriched in early-stage human brain?

# Data
```{python}
#| echo: false
import matplotlib.pyplot as plt
plt.bar(["Ctrl", "TREM2-/-"], [4.1, 7.8])
plt.title("TREM2 loss drives senescence")
plt.savefig("figures/main.png", dpi=150)
```

# Result
TREM2 loss doubles senescent microglia.

# Conclusion
- Senescence is an early-AD phenomenon
- TREM2 is a candidate mechanistic switch
- A CSF biomarker is the next step

# Thanks
- Lab, funders, brain banks
- (QR code to PDF + code)
```

Render: `quarto render talk.qmd --to revealjs` (HTML) and
`quarto render talk.qmd --to pdf` (PDF backup). Time the talk: 13 slides
at 20 min = ~1.5 min/slide — feasible.

For the poster, reuse the figure with smaller fonts via a second
matplotlib run, and render the HTML poster to PDF for printing.

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| Quarto (revealjs) | Markdown -> web slides | https://quarto.org |
| Beamer (LaTeX) | Academic PDF slides | `apt install texlive-latex-extra` |
| Marp CLI | Fast markdown -> PDF/PPTX | `npm i -g @marp-team/marp-cli` |
| matplotlib | Talk-grade figures | `pip install matplotlib` |
| pylatex | Generate Beamer from Python | `pip install pylatex` |
| jinja2 | HTML poster templating | `pip install jinja2` |
| Chromium | HTML/PDF export for revealjs and Marp | https://www.chromium.org |
| OBS Studio | Record talks with camera + slides | https://obsproject.com |
| Whisper (openai) | Auto-subtitle recordings | `pip install openai-whisper` |
| ColorBrewer / Okabe-Ito | Color-blind-safe palettes | matplotlib built-in |
| Inkscape | Edit SVG figures for slides | https://inkscape.org |
| a11y contrast checkers | WAVE, axe, Color Contrast Analyser | https://webaim.org/resources/contrastchecker |

## References

- Quarto presentations docs: https://quarto.org/docs/presentations/
- Beamer documentation: https://www.overleaf.com/learn/latex/Beamer
- Marp CLI docs: https://github.com/marp-team/marp-cli
- ColorBrewer 2.0 (color-blind palettes): https://colorbrewer2.org
- Okabe-Ito palette: https://jfly.uni-koeln.de/color/
- WCAG 2.2 contrast (success criterion 1.4.3): https://www.w3.org/TR/WCAG22/
- Reynolds & Edwards "Presentation Zen" / Duarte "Slide:ology" — design
  principles for one-idea-per-slide.
- Michael Alley "The Craft of Scientific Presentations" — talk design.

## Ethics & safety

- **Plagiarism / image theft.** Every figure that is not yours needs a
  citation and (usually) permission. Use CC-licensed images and credit
  the source on the slide.
- **Authorship and credit.** Co-authors must consent to be listed on the
  title slide and agree with the slides' claims; do not show unpublished
  collaborators' data without their approval.
- **Confidentiality.** If preliminary or patient data is shown, obtain
  IRB approval for the dissemination and anonymize per your protocol.
- **Data integrity.** Do not crop axes, splice gels, or filter outliers
  to make the slide cleaner; the slide's figure must match the
  manuscript's figure.
- **Accessibility.** Alt text on every figure, captions on every video,
  color-blind-safe palette, contrast-checked colors — required for any
  public talk and best practice for any talk.
- **Conflicts of interest.** Disclose funding sources and conflicts on
  the title or disclosure slide.
- **AI use disclosure.** If generative AI helped draft slides, figures,
  or speech, disclose per conference policy; AI cannot be a co-author or
  speaker.
- **Recording consent.** Obtain consent from the audience (and any
  identifiable people in figures) before recording or live-streaming.
