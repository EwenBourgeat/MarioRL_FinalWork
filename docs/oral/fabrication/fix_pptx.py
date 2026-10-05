"""Nettoie le .pptx écrit par pptxgenjs : un seul <a:pPr> par paragraphe.

pptxgenjs écrit un <a:pPr> par morceau de texte : dans une puce qui commence
par du gras (« Gras : suite »), le 2e <a:pPr> (sans puce) annule la puce et
rend le XML non conforme.  On garde le premier, placé en tête du paragraphe.

    python docs/oral/fabrication/fix_pptx.py docs/oral/Oral_RL_Mario.pptx
"""

import re
import shutil
import sys
import zipfile

from lxml import etree

A = "http://schemas.openxmlformats.org/drawingml/2006/main"


def fix(path):
    tmp = path + ".tmp"
    removed = 0
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w") as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if re.match(r"ppt/slides/slide\d+\.xml$", item.filename):
                root = etree.fromstring(data)
                for p in root.iter(f"{{{A}}}p"):
                    pprs = p.findall(f"{{{A}}}pPr")
                    for extra in pprs[1:]:
                        p.remove(extra)
                        removed += 1
                    if pprs and p.index(pprs[0]) != 0:
                        p.remove(pprs[0])
                        p.insert(0, pprs[0])
                data = etree.tostring(root, xml_declaration=True,
                                      encoding="UTF-8", standalone=True)
            zout.writestr(item, data)
    shutil.move(tmp, path)
    print(f"{path} : {removed} <a:pPr> en trop supprimés")


if __name__ == "__main__":
    for f in sys.argv[1:]:
        fix(f)
