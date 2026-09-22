#!/usr/bin/env python3
"""Mechanical Markdown-to-LaTeX conversion for the frozen PVLDB baseline."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs/paper-full-draft-v6-evaluation-hierarchy.md"
OUTPUT = Path(__file__).resolve().parent / "main.tex"

FIGURE_HEIGHTS = {"F1": "2.20in", "F2": "2.05in", "F3": "2.05in", "F4": "2.15in"}


def inline(text: str) -> str:
    text = text.replace("&", r"\&").replace("%", r"\%").replace("#", r"\#").replace("_", r"\_")
    text = re.sub(r"\[@([^\]]+)\]", lambda m: "~\\cite{" + ",".join(
        part.strip().lstrip("@") for part in m.group(1).split(";")
    ) + "}", text)
    text = re.sub(r"Figure F([1-4])", lambda m: r"Figure~\ref{fig:f" + m.group(1) + "}", text)
    text = re.sub(r"Table T([1-5])", lambda m: r"Table~\ref{tab:t" + m.group(1) + "}", text)
    text = re.sub(r"`([^`]+)`", lambda m: "\\texttt{" + latex_escape(m.group(1)) + "}", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\\textbf{\1}", text)
    text = re.sub(r"\*([^*]+)\*", r"\\emph{\1}", text)
    text = text.replace("→", r"$\rightarrow$").replace("≤", r"$\leq$")
    text = text.replace("×", r"$\times$").replace("—", "---").replace("–", "--")
    return text


def latex_escape(text: str) -> str:
    for old, new in [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"),
                     ("#", r"\#"), ("_", r"\_"), ("{", r"\{"), ("}", r"\}")]:
        text = text.replace(old, new)
    return text


def table_latex(caption: str, rows: list[list[str]], label: str) -> str:
    cols = len(rows[0])
    xcol = r">{\raggedright\arraybackslash}X"
    specs = xcol * cols
    out = [r"\begin{table*}[t]", r"\centering", r"\small", f"\\caption{{{inline(caption)}}}",
           f"\\label{{tab:{label.lower()}}}", f"\\begin{{tabularx}}{{\\textwidth}}{{@{{}}{specs}@{{}}}}", r"\toprule"]
    for idx, row in enumerate(rows):
        out.append(" & ".join(inline(cell) for cell in row) + r" \\")
        if idx == 0:
            out.append(r"\midrule")
    out.extend([r"\bottomrule", r"\end{tabularx}", r"\end{table*}"])
    return "\n".join(out)


def figure_latex(line: str) -> str:
    match = re.match(r"> \*\*Figure (F\d): ([^*]+)\*\* (.*)", line)
    if not match:
        raise ValueError(f"Unrecognized figure caption: {line}")
    fid, title, body = match.groups()
    title = title.rstrip(".")
    body = re.sub(r"\s*\*\(Production note:.*?\)\*\s*$", "", body)
    height = FIGURE_HEIGHTS[fid]
    asset = {
        "F1": "figures/f1-ce-replay-architecture.pdf",
        "F2": "figures/f2-cross-workload-nonmonotonicity.pdf",
        "F3": "figures/f3-analyze-maintenance-cost.pdf",
        "F4": "figures/f4-mcv-fd-composition.pdf",
    }[fid]
    return "\n".join([
        r"\begin{figure*}[t]", r"\centering",
        f"\\includegraphics[width=\\textwidth,height={height},keepaspectratio]{{{asset}}}",
        f"\\caption{{\\textbf{{{inline(title)}.}} {inline(body)}}}",
        f"\\Description{{Final vector figure {fid}; its visual content is described by the caption and repository figure plan.}}",
        f"\\label{{fig:{fid.lower()}}}", r"\end{figure*}"])


def convert() -> str:
    lines = SOURCE.read_text().splitlines()
    out: list[str] = []
    in_math = False
    in_list = None
    pending_table_caption = None
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("# "):
            i += 1; continue
        if line == "## Abstract":
            out.append(r"\begin{abstract}"); i += 1
            while i < len(lines) and not lines[i].startswith("## "):
                if lines[i].strip(): out.append(inline(lines[i]))
                i += 1
            out.append(r"\end{abstract}")
            continue
        if line.startswith("## Artifact and Reproducibility Statement"):
            out.append(r"\section*{Artifact and Reproducibility Statement}\label{sec:artifact}"); i += 1; continue
        if line.startswith("## "):
            section_number = re.match(r"^## (\d+)\.", line).group(1)
            title = re.sub(r"^## \d+\. ", "", line)
            out.append(f"\\section{{{inline(title)}}}\\label{{sec:{section_number}}}"); i += 1; continue
        if line.startswith("### "):
            title = re.sub(r"^### \d+\.\d+ ", "", line)
            out.append(f"\\subsection{{{inline(title)}}}"); i += 1; continue
        if line == "$$":
            out.append(r"\[" if not in_math else r"\]"); in_math = not in_math; i += 1; continue
        if line.startswith("```"):
            block = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(lines[i].replace("←", "<-").replace("↓", "v")); i += 1
            wide = max((len(x) for x in block), default=0) > 50
            if wide:
                out.extend([r"\begin{table*}[t]", r"\centering", r"\begin{minipage}{0.94\textwidth}"])
            out.append(r"\begin{verbatim}")
            out.extend(block)
            out.append(r"\end{verbatim}")
            if wide:
                out.extend([r"\end{minipage}", r"\end{table*}"])
            i += 1; continue
        if in_math:
            out.append(line); i += 1; continue
        if line.startswith("> **Figure "):
            out.append(figure_latex(line)); i += 1; continue
        table_cap = re.match(r"\*\*Table (T\d): ([^*]+)\*\*", line)
        if table_cap:
            tid, title = table_cap.groups()
            rest = line[table_cap.end():].strip()
            pending_table_caption = (tid, title + (" " + rest if rest else ""))
            i += 1; continue
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[-:| ]+\|$", lines[i + 1]):
            rows = [[cell.strip() for cell in line.strip("|").split("|")]]
            i += 2
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([cell.strip() for cell in lines[i].strip("|").split("|")]); i += 1
            if not pending_table_caption: raise ValueError("Table without caption")
            tid, caption = pending_table_caption
            out.append(table_latex(caption, rows, tid)); pending_table_caption = None
            continue
        list_match = re.match(r"^(\d+\.|-) (.*)", line)
        if list_match:
            kind = "enumerate" if list_match.group(1) != "-" else "itemize"
            if in_list != kind:
                if in_list: out.append(f"\\end{{{in_list}}}")
                out.append(f"\\begin{{{kind}}}"); in_list = kind
            out.append("\\item " + inline(list_match.group(2))); i += 1; continue
        if in_list and line.strip() == "":
            out.append(f"\\end{{{in_list}}}"); in_list = None; i += 1; continue
        if line.strip(): out.append(inline(line))
        else: out.append("")
        i += 1
    if in_list: out.append(f"\\end{{{in_list}}}")
    return "\n".join(out)


PREAMBLE = r"""% Generated mechanically from docs/paper-full-draft-v6-evaluation-hierarchy.md.
% Scientific content remains synchronized with that evaluation-hierarchy Markdown manuscript.
\documentclass[sigconf,nonacm]{acmart}

%%% do not modify the following VLDB block %%
%%% VLDB block start %%%
\usepackage{pvldb}
%%% VLDB block end %%%

\usepackage{array}
\usepackage{tabularx}
\renewcommand\vldbdoi{XX.XX/XXX.XX}
\renewcommand\vldbpages{XXX-XXX}
\renewcommand\vldbavailabilityurl{https://github.com/1951123/ce-replay}

\begin{document}
\title{CE-Replay: Executable Cardinality-Estimation Semantics for Statistics Physical Design}

% AUTHOR METADATA PENDING: replace these explicit placeholders before submission.
\author{AUTHOR METADATA PENDING}
\affiliation{%
  \institution{AFFILIATION METADATA PENDING}
  \city{CITY METADATA PENDING}
  \country{COUNTRY METADATA PENDING}
}
\email{EMAIL-METADATA-PENDING@example.invalid}
"""

POST_ABSTRACT = r"""
\maketitle

%%% do not modify the following VLDB block %%
%%% VLDB block start %%%
\vldbtopmatter
%%% VLDB block end %%%
"""

POSTAMBLE = r"""
\phantomsection
\label{references-start}
\bibliographystyle{ACM-Reference-Format}
\bibliography{paper}
\end{document}
"""

body = convert()
abstract_end = body.index(r"\end{abstract}") + len(r"\end{abstract}")
OUTPUT.write_text(PREAMBLE + body[:abstract_end] + POST_ABSTRACT + body[abstract_end:] + POSTAMBLE)
