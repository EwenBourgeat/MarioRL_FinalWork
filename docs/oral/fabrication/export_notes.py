"""Écrit docs/oral/Notes_oral.md : le texte à dire, diapo par diapo, lu dans
les notes de l'orateur du .pptx (copie de secours si Canva ne les importe pas).

    python docs/oral/fabrication/export_notes.py
"""

import re
from pathlib import Path

from pptx import Presentation

ORAL = Path(__file__).resolve().parents[1]


def main():
    prs = Presentation(ORAL / "Oral_RL_Mario.pptx")
    out = ["# Oral final : notes de l'orateur", "",
           "Texte à dire pour chaque diapo de `Oral_RL_Mario.pptx`, avec la durée visée entre crochets "
           "(environ 19 minutes pour les diapos 1 à 21). Les mêmes notes sont dans le PowerPoint.", ""]
    total = 0
    for i, slide in enumerate(prs.slides, 1):
        title = None
        for shape in slide.shapes:
            if shape.has_text_frame and shape.name in ("titre", "grand_titre") and shape.text_frame.text.strip():
                title = " ".join(shape.text_frame.text.split())
                break
        notes = slide.notes_slide.notes_text_frame.text.strip() if slide.has_notes_slide else ""
        for m, s in re.findall(r"\[(\d+):(\d\d)\]", notes):
            total += int(m) * 60 + int(s)
        out += [f"## Diapo {i} : {title or '-'}", "", notes or "-", ""]
    out.insert(4, f"Durée totale des diapos minutées : {total // 60} min {total % 60:02d} s.")
    out.insert(5, "")
    (ORAL / "Notes_oral.md").write_text("\n".join(out), encoding="utf-8")
    print("Notes_oral.md écrit,", len(prs.slides), "diapos, durée", total // 60, "min", total % 60, "s")


if __name__ == "__main__":
    main()
