"""Graphismes du jeu, redessinés pixel par pixel (palette NES).

Chaque image est décrite par des chaînes de caractères ; chaque caractère
correspond à une couleur de la palette associée ('.' = transparent).
Les images sont converties en tableaux numpy (RVB + masque) à la demande
et mises en cache.
"""

from functools import lru_cache

import numpy as np

from .constants import NES_PALETTE

# ---------------------------------------------------------------------------
# Palettes (caractère -> index de couleur NES)
# ---------------------------------------------------------------------------
PAL = {
    "mario": {"R": 0x16, "S": 0x27, "B": 0x18},
    "fire": {"R": 0x37, "S": 0x27, "B": 0x16},
    "star1": {"R": 0x29, "S": 0x27, "B": 0x0F},
    "star2": {"R": 0x16, "S": 0x37, "B": 0x0F},
    "star3": {"R": 0x0F, "S": 0x27, "B": 0x16},
    "ground": {"M": 0x36, "A": 0x17, "K": 0x0F},
    "underground": {"M": 0x3C, "A": 0x1C, "K": 0x0F},
    "qblock": {"O": 0x27, "B": 0x17, "K": 0x0F},
    "qblock2": {"O": 0x17, "B": 0x17, "K": 0x0F},
    "qblock3": {"O": 0x07, "B": 0x17, "K": 0x0F},
    "used": {"B": 0x17, "K": 0x0F},
    "pipe": {"L": 0x29, "G": 0x1A, "K": 0x0F},
    "cloud": {"W": 0x30, "C": 0x21, "K": 0x0F},
    "bush": {"W": 0x29, "C": 0x1A, "K": 0x0F},
    "hill": {"G": 0x1A, "K": 0x0F},
    "goomba": {"B": 0x17, "W": 0x36, "K": 0x0F},
    "goomba_ug": {"B": 0x1C, "W": 0x3C, "K": 0x0F},
    "koopa": {"G": 0x1A, "W": 0x30, "O": 0x27},
    "mushroom": {"R": 0x16, "O": 0x27, "W": 0x30, "K": 0x0F},
    "1up": {"R": 0x1A, "O": 0x27, "W": 0x30, "K": 0x0F},
    "flower1": {"R": 0x16, "O": 0x27, "W": 0x30, "G": 0x1A},
    "flower2": {"R": 0x27, "O": 0x30, "W": 0x16, "G": 0x1A},
    "flower3": {"R": 0x30, "O": 0x16, "W": 0x27, "G": 0x1A},
    "flower4": {"R": 0x1A, "O": 0x27, "W": 0x30, "G": 0x1A},
    "star_a": {"O": 0x27, "K": 0x0F},
    "star_b": {"O": 0x30, "K": 0x0F},
    "star_c": {"O": 0x29, "K": 0x0F},
    "star_d": {"O": 0x16, "K": 0x0F},
    "coin": {"O": 0x27, "B": 0x17, "K": 0x0F, "W": 0x37},
    "coin2": {"O": 0x17, "B": 0x07, "K": 0x0F, "W": 0x27},
    "coin3": {"O": 0x07, "B": 0x17, "K": 0x0F, "W": 0x17},
    "fireball": {"R": 0x16, "O": 0x27, "Y": 0x38},
    "flag": {"W": 0x30, "G": 0x1A},
    "castle_flag": {"W": 0x30, "R": 0x16, "G": 0x1A},
    "pole": {"L": 0x29, "G": 0x1A, "K": 0x0F},
    "white": {"X": 0x30},
    "peach": {"X": 0x36},
    "black": {"X": 0x0F},
    "cursor": {"R": 0x16, "W": 0x36, "K": 0x0F},
    "firework": {"R": 0x16, "O": 0x27, "W": 0x30},
}

# ---------------------------------------------------------------------------
# Petit Mario (16 x 16), tourné vers la droite
# ---------------------------------------------------------------------------
_HEAD = [
    ".....RRRRR......",
    "....RRRRRRRRR...",
    "....BBBSSBS.....",
    "...BSBSSSBSSS...",
    "...BSBBSSSBSSS..",
    "...BBSSSSBBBB...",
    ".....SSSSSSS....",
]

SMALL = {
    "stand": _HEAD + [
        "....BBRBBB......",
        "...BBBRBBRBBB...",
        "..BBBBRRRRBBBB..",
        "..SSBRSRRSRBSS..",
        "..SSSRRRRRRSSS..",
        "..SSRRRRRRRRSS..",
        "....RRR..RRR....",
        "...BBB....BBB...",
        "..BBBB....BBBB..",
    ],
    "walk1": _HEAD + [
        "..BBBBBRRB.SS...",
        "SSBBBBBBRRRSSS..",
        "SSS.BBBRSRRRSS..",
        "SS..RRRRRRRR.B..",
        "...RRRRRRRRRBB..",
        "..RRRRRRRRRRBB..",
        ".BBRRR...RRRBB..",
        ".BBB............",
        "..BBB...........",
    ],
    "walk2": _HEAD + [
        "....BBRRBB......",
        "...BBBBRRBB.....",
        "...BBBRRSRR.....",
        "...BBBBRRRR.....",
        "...RBBSSSRR.....",
        "....RRSSRRR.....",
        ".....RRRBBB.....",
        ".....BBBBBB.....",
        ".....BBBB.......",
    ],
    "walk3": _HEAD + [
        "....BBRBBB......",
        "...BBBBRRBB.....",
        "...BBBRRSRRR....",
        "...BBRRRRRRR....",
        "...RRSSSRRRR....",
        "...RRSSRRRR.....",
        "....RRRRBBB.....",
        "....BBBBBB......",
        ".....BBBB.......",
    ],
    "jump": [
        ".............SSS",
        "......RRRRR..SSS",
        ".....RRRRRRRRRSS",
        ".....BBBSSBS.BBB",
        "....BSBSSSBSSBBB",
        "....BSBBSSSBSSSB",
        "....BBSSSSBBBBB.",
        "......SSSSSSSB..",
        "..BBBBBRBBBRB...",
        ".BBBBBBBRBBBR..B",
        "SSBBBBBBRRRRR..B",
        "SSS.RRBRRSRRSRBB",
        ".S.BRRRRRRRRRRBB",
        "..BBBRRRRRRRRRBB",
        ".BBBRRRRRRR.....",
        ".B..RRRR........",
    ],
    "skid": [
        ".....RRRRR......",
        "...RRRRRRRRR....",
        "..BBBBSSSBB.....",
        ".BSSSBBSSSBS....",
        ".BSSSBBSSBSB....",
        "..BBSSSSSBBB....",
        "...SSSSSSSS.....",
        "..BBBBRRRBSSS...",
        ".SSBBBBRRRBSS...",
        ".SSSRBBBRRRRR...",
        ".SS.RRRRRRRRR...",
        "....RRRRRRRRRB..",
        "...RRRRRRR.BBB..",
        "..BRRRR....BBB..",
        "..BBBB.....BB...",
        "...BBB..........",
    ],
    "death": [
        "......RRRR......",
        "..S.RRRRRRRR.S..",
        ".SSSBSBSSBSBSSS.",
        ".SSBBSBSSBSBBSS.",
        "..BBSSSSSSSSBB..",
        "...BBSBBBBSBB...",
        "....SSBSSBSS....",
        "...BBRSSSSRBB...",
        "..BBBRRRRRRBBB..",
        ".BBBBRSRRSRBBBB.",
        ".BBBRRRRRRRRBBB.",
        "..BBRRRRRRRRBB..",
        "....RRRRRRRR....",
        "....RRR..RRR....",
        "...BBB....BBB...",
        "..BBBB....BBBB..",
    ],
    "climb": _HEAD + [
        "...BBBRBBSS.....",
        "..BBBBRRBSS.....",
        "..BBBRRRRR......",
        "..SSRRRSRR......",
        "..SSRRRRRR......",
        "...RRRRRRR......",
        "...RRR.RRRR.....",
        "..BBB...BBBB....",
        "..BBB....BBB....",
    ],
}

# ---------------------------------------------------------------------------
# Grand Mario (16 x 32), tourné vers la droite
# ---------------------------------------------------------------------------
_BIG_HEAD = [
    "......RRRRR.....",
    "....RRRRRRRRR...",
    "...RRRRRRRRRRRR.",
    "...BBBSSSBSS....",
    "..BSSBSSSSBSSS..",
    "..BSSBBSSSSBSSS.",
    "..BBSSSSSBBBBBB.",
    "...BSSSSSSBBBB..",
    "....SSSSSSSSS...",
    ".....SSSSSSS....",
]
_BIG_TORSO = [
    "....BBBRRBB.....",
    "...BBBBRRBBBB...",
    "..BBBBBRRRBBBB..",
    ".BBBBBBRRRRBBBB.",
    ".BBBBBBRRRRBBBB.",
    "BBBBBBRRSRRBBBBB",
    "SSSBBRRRRRRRBSSS",
    "SSSSRRRRRRRRSSSS",
    "SSSRRRRRRRRRRSSS",
    "..RRRRRRRRRRRR..",
]

BIG = {
    "stand": _BIG_HEAD + _BIG_TORSO + [
        "..RRRRRRRRRRRR..",
        "..RRRRRR.RRRRR..",
        "..RRRRR...RRRR..",
        "..RRRRR...RRRR..",
        "...RRRR...RRR...",
        "...BBBB...BBB...",
        "..BBBBB...BBBB..",
        ".BBBBBB...BBBBB.",
        ".BBBBBB...BBBBB.",
        "................",
        "................",
        "................",
    ][:12],
    "walk1": _BIG_HEAD + [
        "....BBBRRBB.....",
        "...BBBBRRBBBB...",
        "..BBBBBRRRBBBBSS",
        ".BBBBBBRRRRBBSSS",
        "SSBBBBBRRRRBBSS.",
        "SSSBBBRRSRRRBB..",
        "SSS.RRRRRRRRR...",
        "....RRRRRRRRRR..",
        "...RRRRRRRRRRRR.",
        "..RRRRRRRRRRRRR.",
        "..RRRRRR..RRRRR.",
        ".RRRRRR....RRRR.",
        ".RRRRR......RRRB",
        "BBRRR.......BBBB",
        "BBBB........BBBB",
        "BBB.........BBB.",
        ".BBB............",
        "..BBB...........",
        "................",
        "................",
        "................",
        "................",
    ],
    "walk2": _BIG_HEAD + [
        "....BBBRRBB.....",
        "...BBBBRRBBB....",
        "...BBBBRRRBB....",
        "...BBBBRRRRB....",
        "...BBBRRSRRR....",
        "...SSSRRRRRR....",
        "...SSSRRRRRR....",
        "....SRRRRRRR....",
        "....RRRRRRRR....",
        "....RRRRRRRR....",
        "....RRRRRRRR....",
        "....RRRRRRR.....",
        ".....RRRRRR.....",
        ".....RRRRBB.....",
        ".....BBBBBB.....",
        ".....BBBBBBB....",
        ".....BBBBBBB....",
        "................",
        "................",
        "................",
        "................",
        "................",
    ],
    "walk3": _BIG_HEAD + [
        "....BBBRRBB.....",
        "...BBBBRRBBB....",
        "..BBBBBRRRBBB...",
        "..BBBBBRRRRBB...",
        "..SSBBRRSRRRBSS.",
        "..SSSRRRRRRRSSS.",
        "..SSRRRRRRRRRS..",
        "...RRRRRRRRRR...",
        "...RRRRRRRRRR...",
        "...RRRRRRRRRR...",
        "...RRRRR.RRRR...",
        "...RRRR...RRRR..",
        "..BBBRR...RRRR..",
        "..BBBB....BBBB..",
        ".BBBBB.....BBBB.",
        ".BBBB......BBBB.",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
    ],
    "jump": [
        "..............SS",
        ".......RRRRR..SS",
        ".....RRRRRRRRRSS",
        "....RRRRRRRRRRSS",
        "....BBBSSSBSS.BB",
        "...BSSBSSSSBSSBB",
        "...BSSBBSSSSBSSB",
        "...BBSSSSSBBBBB.",
        "....BSSSSSSBBBB.",
        ".....SSSSSSSSB..",
        "...BBBBBRRBBBB..",
        "..BBBBBBRRBBBB..",
        ".BBBBBBBRRRBBB..",
        "SSBBBBBBRRRRBB..",
        "SSSBBBBRRSRRR...",
        "SSS.RRRRRRRRRB..",
        "...RRRRRRRRRRBB.",
        "..RRRRRRRRRRRBBB",
        "..RRRRRRRRRRRBBB",
        ".RRRRRRRR.RRRBB.",
        ".RRRRRRR..RRRR..",
        "BBRRRRR...RRRR..",
        "BBBRR.....RRR...",
        "BBBB............",
        "BBB.............",
        ".BBB............",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
    ],
    "skid": [
        ".....RRRRRR.....",
        "...RRRRRRRRRR...",
        "..RRRRRRRRRRRR..",
        "...BBSSSBBBB....",
        "..BSSSBBSSSSB...",
        "..BSSSBBSSSBSB..",
        "..BBBSSSSSBBBB..",
        "...BBSSSSSSSB...",
        "....SSSSSSSS....",
        "....SSSSSSS.....",
        "...BBBRRBBBSSS..",
        "..BBBBRRBBBSSS..",
        ".BBBBBRRRBBSSS..",
        ".SSBBBRRRRBBB...",
        "SSSSBRRSRRRRR...",
        "SSS.RRRRRRRRR...",
        "....RRRRRRRRRR..",
        "...RRRRRRRRRRR..",
        "...RRRRRRRRRRRB.",
        "..RRRRRRR.RRBBB.",
        "..RRRRRR..RBBBB.",
        "..RRRRR....BBBB.",
        "...RRRR....BBB..",
        "..BBBBB.........",
        ".BBBBBB.........",
        ".BBBBB..........",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
    ],
    "crouch": [
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "......RRRRR.....",
        "....RRRRRRRRR...",
        "...RRRRRRRRRRRR.",
        "...BBBSSSBSS....",
        "..BSSBSSSSBSSS..",
        "..BSSBBSSSSBSSS.",
        "..BBSSSSSBBBBBB.",
        "....SSSSSSSSS...",
        "..BBBBRRRRBBB...",
        ".BBBBRRRRRRBBBB.",
        "SSSBRRSRRSRRBSSS",
        "SSSRRRRRRRRRRSSS",
        "SSRRRRRRRRRRRRSS",
        "..RRRRRRRRRRRR..",
        ".RRRRRRRRRRRRRR.",
        ".RRRRRR..RRRRRR.",
        ".BBBBB....BBBBB.",
        "BBBBBB....BBBBBB",
        "................",
        "................",
    ][:32],
    "climb": _BIG_HEAD + [
        "....BBBRRBBSS...",
        "...BBBBRRBBSS...",
        "..BBBBBRRRBSS...",
        "..BBBBBRRRR.....",
        "..SSBBRRSRR.....",
        "..SSSRRRRRR.....",
        "..SSRRRRRRR.....",
        "...RRRRRRRR.....",
        "...RRRRRRRRR....",
        "...RRRRRRRRR....",
        "...RRRR.RRRR....",
        "...RRRR..RRRR...",
        "..BBBB...BBBB...",
        "..BBBB...BBBB...",
        ".BBBBB...BBBBB..",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
    ],
}
BIG["throw"] = _BIG_HEAD + [
    "....BBBRRBB.....",
    "...BBBBRRBBB....",
    "..BBBBBRRRBBSSS.",
    ".BBBBBBRRRRBSSS.",
    ".BBBBBBRRRRBSSS.",
    "BBBBBBRRSRRR....",
    "SSSBBRRRRRRR....",
    "SSSSRRRRRRRR....",
    "SSSRRRRRRRRRR...",
    "..RRRRRRRRRRRR..",
] + BIG["stand"][20:]

# ---------------------------------------------------------------------------
# Ennemis
# ---------------------------------------------------------------------------
GOOMBA = [
    "......BBBB......",
    ".....BBBBBB.....",
    "....BBBBBBBB....",
    "...BBBBBBBBBB...",
    "..BKKBBBBBBKKB..",
    ".BBBWKBBBBKWBBB.",
    ".BBBWKKKKKKWBBB.",
    "BBBBWKWBBWKWBBBB",
    "BBBBWWWBBWWWBBBB",
    "BBBBBBBBBBBBBBBB",
    ".BBBBWWWWWWBBBB.",
    "....WWWWWWWW....",
    "...WWWWWWWWWKK..",
    "..KKWWWWWWWKKKK.",
    "..KKKKWWWWKKKKK.",
    "...KKKK..KKKK...",
]
GOOMBA_FLAT = [
    "......BBBB......",
    "...BBBBBBBBBB...",
    ".BBKKWWBBWWKKBB.",
    "BBBBBBBBBBBBBBBB",
    "..WWWWWWWWWWWW..",
    ".KKKKWWWWWWKKKK.",
    "KKKKKK....KKKKKK",
    "................",
]

KOOPA_1 = [
    "....OO..........",
    "...OOOO.........",
    "..OOOOOO........",
    "..OWWOOO........",
    "..OWGOOO........",
    "..OOOOOO........",
    ".OOOOOOO........",
    "OOO.OOOO........",
    "OO..OOOO........",
    ".....OOO........",
    ".....OOO.GGGG...",
    "....OOOGGWGGWG..",
    "....OOGGWGGWGGG.",
    "....OGGWWWWWWGGG",
    "....OGWGGWGGWGGG",
    "....WWWGGWGGWGGG",
    "...WWWWWWWWWWWG.",
    "...OOOWWWWWWWW..",
    "...OOOOWWWWWWO..",
    "....OOOOOOOOOO..",
    ".....OOO..OOOO..",
    "....OOOO..OOOO..",
    "...OOOOO...OOOO.",
    "................",
]
KOOPA_2 = KOOPA_1[:18] + [
    "...OOOOWWWWWWO..",
    "....OOOOOOOOO...",
    ".....OOOOOOO....",
    "......OOOOO.....",
    ".....OOOOOO.....",
    "................",
]
SHELL = [
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    ".....GGGGGG.....",
    "...GGWGGGGWGG...",
    "..GGWGGWWGGWGG..",
    ".GGGWGWGGWGWGGG.",
    ".GGWWWWWWWWWWGG.",
    "GGGWGGWGGWGGWGGG",
    "GGWGGGWGGWGGGWGG",
    "GWWWWWWWWWWWWWWG",
    "WWWWWWWWWWWWWWWW",
    ".WWWWWWWWWWWWWW.",
    "..OOOOOOOOOOOO..",
    "...OOOOOOOOOO...",
    "................",
    "................",
    "................",
    "................",
]
SHELL_LEGS = SHELL[:18] + [
    ".OOOOOOOOOOOOOO.",
    "OOO.OOOOOOOO.OOO",
    "OO............OO",
    "................",
    "................",
    "................",
]

# ---------------------------------------------------------------------------
# Objets
# ---------------------------------------------------------------------------
MUSHROOM = [
    "......RRRR......",
    "....RRROOORR....",
    "...RRRROOOORR...",
    "..RRRRRROOORRR..",
    ".ROORRRRRRRRRRR.",
    ".OOOORRRRRRROOR.",
    "ROOOORRRRRROOOOR",
    "ROOOORRRRRROOOOR",
    "RROORRRRRRRROORR",
    "RRRRRWWWWWWRRRRR",
    ".RRWWWWWWWWWWRR.",
    "...WWWKWWKWWW...",
    "...WWWKWWKWWW...",
    "...WWWWWWWWWW...",
    "....WWWWWWWW....",
    ".....WWWWWW.....",
]
FLOWER = [
    "................",
    "...RRRRRRRRRR...",
    ".RROOOOOOOOOORR.",
    "RROOWWWWWWWWOORR",
    "RROOWWWWWWWWOORR",
    ".RROOOOOOOOOORR.",
    "...RRRRRRRRRR...",
    ".......GG.......",
    ".GGG...GG...GGG.",
    "GGGGG..GG..GGGGG",
    ".GGGGG.GG.GGGGG.",
    "..GGGGGGGGGGGG..",
    "...GGGGGGGGGG...",
    ".....GGGGGG.....",
    ".......GG.......",
    ".......GG.......",
]
STAR = [
    ".......OO.......",
    ".......OO.......",
    "......OOOO......",
    "......OOOO......",
    "OOOOOOOOOOOOOOOO",
    ".OOOOOOOOOOOOOO.",
    "..OOOOKOOKOOOO..",
    "...OOOKOOKOOO...",
    "....OOKOOKOO....",
    "....OOOOOOOO....",
    "...OOOOOOOOOO...",
    "...OOOOOOOOOO...",
    "..OOOOO..OOOOO..",
    "..OOOO....OOOO..",
    ".OOO........OOO.",
    ".O............O.",
]
COIN_TILE = [
    "................",
    "......KKKK......",
    ".....KOOOOK.....",
    "....KOOWWOOK....",
    "....KOWOOBOK....",
    "....KOWOOBOK....",
    "....KOWOOBOK....",
    "....KOWOOBOK....",
    "....KOWOOBOK....",
    "....KOWOOBOK....",
    "....KOWOOBOK....",
    "....KOOBBOOK....",
    ".....KOOOOK.....",
    "......KKKK......",
    "................",
    "................",
]
COIN_SPIN = [
    COIN_TILE,
    COIN_TILE,
    [
        "................",
        ".......KK.......",
        "......KOOK......",
        "......KWBK......",
        "......KWBK......",
        "......KWBK......",
        "......KWBK......",
        "......KWBK......",
        "......KWBK......",
        "......KWBK......",
        "......KWBK......",
        "......KWBK......",
        "......KOOK......",
        ".......KK.......",
        "................",
        "................",
    ],
    [
        "................",
        ".......KK.......",
        ".......KK.......",
        ".......KK.......",
        ".......KK.......",
        ".......KK.......",
        ".......KK.......",
        ".......KK.......",
        ".......KK.......",
        ".......KK.......",
        ".......KK.......",
        ".......KK.......",
        ".......KK.......",
        ".......KK.......",
        "................",
        "................",
    ],
]
COIN_SPIN[1] = [
    "................",
    "......KKK.......",
    ".....KOOOK......",
    ".....KWOBK......",
    ".....KWOBK......",
    ".....KWOBK......",
    ".....KWOBK......",
    ".....KWOBK......",
    ".....KWOBK......",
    ".....KWOBK......",
    ".....KWOBK......",
    ".....KWOBK......",
    ".....KOOOK......",
    "......KKK.......",
    "................",
    "................",
]
HUD_COIN = [
    "..KKK...",
    ".KOOOK..",
    ".KOWBK..",
    ".KOWBK..",
    ".KOWBK..",
    ".KOWBK..",
    ".KOOOK..",
    "..KKK...",
]
FIREBALL = [
    "..RRR...",
    ".ROOOR..",
    "ROYYOR..",
    "ROYYYOR.",
    ".ROYYOR.",
    "..ROOR.R",
    "...RR...",
    "........",
]
EXPLOSION = [
    [
        "................",
        "................",
        "................",
        "................",
        "......R..R......",
        ".......RR.......",
        ".....ROOOOR.....",
        "....RROYYORR....",
        "....RROYYORR....",
        ".....ROOOOR.....",
        ".......RR.......",
        "......R..R......",
        "................",
        "................",
        "................",
        "................",
    ],
    [
        "................",
        "................",
        "...R........R...",
        "....R..RR..R....",
        ".....ROOOOR.....",
        "....ROYYYYOR....",
        "...ROYY..YYOR...",
        "..RROY....YORR..",
        "..RROY....YORR..",
        "...ROYY..YYOR...",
        "....ROYYYYOR....",
        ".....ROOOOR.....",
        "....R..RR..R....",
        "...R........R...",
        "................",
        "................",
    ],
    [
        "R..............R",
        ".R....R..R....R.",
        "..R..........R..",
        "................",
        "....O......O....",
        "................",
        "R.O..........O.R",
        "................",
        "................",
        "R.O..........O.R",
        "................",
        "....O......O....",
        "................",
        "..R..........R..",
        ".R....R..R....R.",
        "R..............R",
    ],
]
DEBRIS = [
    "..AAAA..",
    ".AMMAAA.",
    "AMAAAKAA",
    "AAAAKAAA",
    "AAAKAAAA",
    ".AKAAAK.",
    "..AAAA..",
    "........",
]
FLAG = [
    "WWWWWWWWWWWWWWWW",
    ".WWWWWWWWWWWWWWW",
    "..WWWWWGGGGWWWWW",
    "...WWWGGGGGGWWWW",
    "....WWGWGGWGWWWW",
    ".....WGGGGGGWWWW",
    "......WGWWGWWWWW",
    ".......WGGWWWWWW",
    "........WWWWWWWW",
    ".........WWWWWWW",
    "..........WWWWWW",
    "...........WWWWW",
    "............WWWW",
    ".............WWW",
    "..............WW",
    "...............W",
]
CASTLE_FLAG = [
    "WWWWWWWWWWWW....",
    "WWWWWRWWWWWW....",
    "WWWWRRRWWWWW....",
    "WWRRRRRRRWWW....",
    "WWWRRRRRWWWW....",
    "WWWWRRRRWWWW....",
    "WWWRRWWRRWWW....",
    "WWWWWWWWWWWW....",
    "WWWWWWWWWWWW....",
    "............GG..",
    "............GG..",
    "............GG..",
    "............GG..",
    "............GG..",
    "............GG..",
    "............GG..",
]

# ---------------------------------------------------------------------------
# Tuiles de décor (16 x 16)
# ---------------------------------------------------------------------------
GROUND_T = [
    "AMMMMMMMMKAMMMMA",
    "MAAAAAAAAKMAAAAK",
    "MAAAAAAAAKMAAAAK",
    "MAAAAAAAAKMAAAAK",
    "MAAAAAAAAKMKAAAK",
    "MAAAAAAAAKAKKKKA",
    "MAAAAAAAAKMMMMMK",
    "MAAAAAAAAKMAAAAK",
    "MAAAAAAAAKMAAAAK",
    "MAAAAAAAAKMAAAAK",
    "KKAAAAAAKMAAAAAK",
    "MMKKAAAAKMAAAAAK",
    "MAMMKKKKMAAAAAAK",
    "MAAAMMMKMAAAAAAK",
    "MAAAAAAKMAAAAAKK",
    "AKKKKKKAKKKKKKKA",
]
BRICK_T = [
    "MMMMMMMMMMMMMMMM",
    "AAAAAAAKAAAAAAAK",
    "AAAAAAAKAAAAAAAK",
    "KKKKKKKKKKKKKKKK",
    "AAAKAAAAAAAKAAAA",
    "AAAKAAAAAAAKAAAA",
    "AAAKAAAAAAAKAAAA",
    "KKKKKKKKKKKKKKKK",
    "AAAAAAAKAAAAAAAK",
    "AAAAAAAKAAAAAAAK",
    "AAAAAAAKAAAAAAAK",
    "KKKKKKKKKKKKKKKK",
    "AAAKAAAAAAAKAAAA",
    "AAAKAAAAAAAKAAAA",
    "AAAKAAAAAAAKAAAA",
    "KKKKKKKKKKKKKKKK",
]
STAIR_T = [
    "AMMMMMMMMMMMMMMK",
    "MAMMMMMMMMMMMMKK",
    "MMAMMMMMMMMMMKKK",
    "MMMAAAAAAAAAKKKK",
    "MMMAAAAAAAAAKKKK",
    "MMMAAAAAAAAAKKKK",
    "MMMAAAAAAAAAKKKK",
    "MMMAAAAAAAAAKKKK",
    "MMMAAAAAAAAAKKKK",
    "MMMAAAAAAAAAKKKK",
    "MMMAAAAAAAAAKKKK",
    "MMMAAAAAAAAAKKKK",
    "MMMAAAAAAAAAKKKK",
    "MMKKKKKKKKKKKAKK",
    "MKKKKKKKKKKKKKAK",
    "KKKKKKKKKKKKKKKA",
]
QBLOCK_T = [
    ".BBBBBBBBBBBBBB.",
    "BOOOOOOOOOOOOOOK",
    "BOKOOOOOOOOOOKOK",
    "BOOOOBBBBBOOOOOK",
    "BOOOBBKKKBBOOOOK",
    "BOOOBBKOOBBKOOOK",
    "BOOOBBKOOBBKOOOK",
    "BOOOOKKOBBBKOOOK",
    "BOOOOOOBBKKKOOOK",
    "BOOOOOOBBKOOOOOK",
    "BOOOOOOOKKOOOOOK",
    "BOOOOOOBBOOOOOOK",
    "BOOOOOOBBKOOOOOK",
    "BOKOOOOOKKOOOKOK",
    "BOOOOOOOOOOOOOOK",
    "KKKKKKKKKKKKKKKK",
]
USED_T = [
    ".KKKKKKKKKKKKKK.",
    "KBBBBBBBBBBBBBBK",
    "KBKBBBBBBBBBBKBK",
    "KBBBBBBBBBBBBBBK",
    "KBBBBBBBBBBBBBBK",
    "KBBBBBBBBBBBBBBK",
    "KBBBBBBBBBBBBBBK",
    "KBBBBBBBBBBBBBBK",
    "KBBBBBBBBBBBBBBK",
    "KBBBBBBBBBBBBBBK",
    "KBBBBBBBBBBBBBBK",
    "KBBBBBBBBBBBBBBK",
    "KBBBBBBBBBBBBBBK",
    "KBKBBBBBBBBBBKBK",
    "KBBBBBBBBBBBBBBK",
    ".KKKKKKKKKKKKKK.",
]

_PIPE_TOP_IN = "G" + "L" * 2 + "G" + "L" * 9 + "G" + "L" + "G" * 2 + "L" + "G" * 12
_PIPE_BODY_IN = "G" + "L" * 2 + "G" + "L" * 7 + "G" + "L" + "G" * 2 + "L" + "G" * 10
PIPE_TOP = ["K" * 32] + ["K" + _PIPE_TOP_IN + "K"] * 14 + ["K" * 32]
PIPE_BODY = [".." + "K" + _PIPE_BODY_IN + "K" + ".."] * 16

POLE_T = ["......." + "LG" + "......."] * 16
BALL_T = [
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "......KKKK......",
    ".....KGGGGK.....",
    "....KGLLGGGK....",
    "....KGLGGGGK....",
    "....KGGGGGGK....",
    "....KGGGGGGK....",
    ".....KGGGGK.....",
    "......KKKK......",
]

# Château (palette « ground »)
CASTLE = {
    "brick": BRICK_T,
    "top": ["....KAAAAAAK...."] * 1 + ["....AAAAAAAA...."] * 7 + BRICK_T[8:],
    "top_fill": ["KKKKKAAAAAAKKKKK"] * 1 + ["KKKKAAAAAAAAKKKK"] * 7 + BRICK_T[8:],
    "win_l": [("KKKKKK" + r[6:]) for r in BRICK_T],
    "win_r": [(r[:10] + "KKKKKK") for r in BRICK_T],
    "door_top": [
        "KKKKKKKKKKKKKKKK",
        "AAAAAAAKAAAAAAAK",
        "AAAAAAAKAAAAAAAK",
        "KKKKKKKKKKKKKKKK",
        "AAAKAKKKKKKAAAAA",
        "AAAKKKKKKKKKAAAA",
        "AAAKKKKKKKKKKAAA",
        "KKKKKKKKKKKKKKKK",
        "AAKKKKKKKKKKKKAK",
        "AAKKKKKKKKKKKKAK",
        "AAKKKKKKKKKKKKAK",
        "KKKKKKKKKKKKKKKK",
        "AAKKKKKKKKKKKKAA",
        "AAKKKKKKKKKKKKAA",
        "AAKKKKKKKKKKKKAA",
        "KKKKKKKKKKKKKKKK",
    ],
    "door": ["AAKKKKKKKKKKKKAA"] * 16,
}

# ---------------------------------------------------------------------------
# Police du HUD (8 x 8)
# ---------------------------------------------------------------------------
FONT = {
    "0": ["..XXX...", ".X..XX..", "XX...XX.", "XX...XX.", "XX...XX.", ".XX..X..", "..XXX...", "........"],
    "1": ["...XX...", "..XXX...", "...XX...", "...XX...", "...XX...", "...XX...", ".XXXXXX.", "........"],
    "2": [".XXXXX..", "XX...XX.", "....XXX.", "..XXXX..", ".XXXX...", "XXX.....", "XXXXXXX.", "........"],
    "3": [".XXXXXX.", "....XX..", "...XX...", "..XXXX..", ".....XX.", "XX...XX.", ".XXXXX..", "........"],
    "4": ["...XXX..", "..XXXX..", ".XX.XX..", "XX..XX..", "XXXXXXX.", "....XX..", "....XX..", "........"],
    "5": ["XXXXXX..", "XX......", "XXXXXX..", ".....XX.", ".....XX.", "XX...XX.", ".XXXXX..", "........"],
    "6": ["..XXXX..", ".XX.....", "XX......", "XXXXXX..", "XX...XX.", "XX...XX.", ".XXXXX..", "........"],
    "7": ["XXXXXXX.", "XX...XX.", "....XX..", "...XX...", "..XX....", "..XX....", "..XX....", "........"],
    "8": [".XXXX...", "XX...X..", "XXX..X..", ".XXXX...", "X..XXXX.", "X....XX.", ".XXXXX..", "........"],
    "9": [".XXXXX..", "XX...XX.", "XX...XX.", ".XXXXXX.", ".....XX.", "....XX..", ".XXXX...", "........"],
    "A": ["..XXX...", ".XX.XX..", "XX...XX.", "XX...XX.", "XXXXXXX.", "XX...XX.", "XX...XX.", "........"],
    "B": ["XXXXXX..", "XX...XX.", "XX...XX.", "XXXXXX..", "XX...XX.", "XX...XX.", "XXXXXX..", "........"],
    "C": ["..XXXX..", ".XX..XX.", "XX......", "XX......", "XX......", ".XX..XX.", "..XXXX..", "........"],
    "D": ["XXXXX...", "XX..XX..", "XX...XX.", "XX...XX.", "XX...XX.", "XX..XX..", "XXXXX...", "........"],
    "E": ["XXXXXXX.", "XX......", "XX......", "XXXXXX..", "XX......", "XX......", "XXXXXXX.", "........"],
    "F": ["XXXXXXX.", "XX......", "XX......", "XXXXXX..", "XX......", "XX......", "XX......", "........"],
    "G": ["..XXXXX.", ".XX.....", "XX......", "XX..XXX.", "XX...XX.", ".XX..XX.", "..XXXXX.", "........"],
    "H": ["XX...XX.", "XX...XX.", "XX...XX.", "XXXXXXX.", "XX...XX.", "XX...XX.", "XX...XX.", "........"],
    "I": [".XXXXXX.", "...XX...", "...XX...", "...XX...", "...XX...", "...XX...", ".XXXXXX.", "........"],
    "K": ["XX...XX.", "XX..XX..", "XX.XX...", "XXXX....", "XXXXX...", "XX.XXX..", "XX..XXX.", "........"],
    "L": [".XX.....", ".XX.....", ".XX.....", ".XX.....", ".XX.....", ".XX.....", ".XXXXXX.", "........"],
    "M": ["XX...XX.", "XXX.XXX.", "XXXXXXX.", "XXXXXXX.", "XX.X.XX.", "XX...XX.", "XX...XX.", "........"],
    "N": ["XX...XX.", "XXX..XX.", "XXXX.XX.", "XXXXXXX.", "XX.XXXX.", "XX..XXX.", "XX...XX.", "........"],
    "O": [".XXXXX..", "XX...XX.", "XX...XX.", "XX...XX.", "XX...XX.", "XX...XX.", ".XXXXX..", "........"],
    "P": ["XXXXXX..", "XX...XX.", "XX...XX.", "XX...XX.", "XXXXXX..", "XX......", "XX......", "........"],
    "R": ["XXXXXX..", "XX...XX.", "XX...XX.", "XX..XXX.", "XXXXX...", "XX.XXX..", "XX..XXX.", "........"],
    "S": [".XXXX...", "XX..XX..", "XX......", ".XXXXX..", ".....XX.", "XX...XX.", ".XXXXX..", "........"],
    "T": [".XXXXXX.", "...XX...", "...XX...", "...XX...", "...XX...", "...XX...", "...XX...", "........"],
    "U": ["XX...XX.", "XX...XX.", "XX...XX.", "XX...XX.", "XX...XX.", "XX...XX.", ".XXXXX..", "........"],
    "V": ["XX...XX.", "XX...XX.", "XX...XX.", "XXX.XXX.", ".XXXXX..", "..XXX...", "...X....", "........"],
    "W": ["XX...XX.", "XX...XX.", "XX.X.XX.", "XXXXXXX.", "XXXXXXX.", "XXX.XXX.", "XX...XX.", "........"],
    "Y": [".XX..XX.", ".XX..XX.", ".XX..XX.", "..XXXX..", "...XX...", "...XX...", "...XX...", "........"],
    "-": ["........", "........", "........", ".XXXXXX.", "........", "........", "........", "........"],
    "x": ["........", "XX...XX.", ".XX.XX..", "..XXX...", ".XX.XX..", "XX...XX.", "........", "........"],
    "!": ["...XX...", "..XXXX..", "..XXXX..", "...XX...", "...XX...", "........", "...XX...", "........"],
    ".": ["........", "........", "........", "........", "........", "...XX...", "...XX...", "........"],
    " ": ["........"] * 8,
    "Q": [".XXXXX..", "XX...XX.", "XX...XX.", "XX...XX.", "XX.XXXX.", "XX..XX..", ".XXXX.X.", "........"],
    "J": ["....XXX.", ".....XX.", ".....XX.", ".....XX.", "XX...XX.", "XX...XX.", ".XXXXX..", "........"],
    "X": ["XX...XX.", "XX...XX.", ".XX.XX..", "..XXX...", ".XX.XX..", "XX...XX.", "XX...XX.", "........"],
    "Z": ["XXXXXXX.", "....XXX.", "...XXX..", "..XXX...", ".XXX....", "XXX.....", "XXXXXXX.", "........"],
    "©": ["..XXXX..", ".X....X.", "X..XX..X", "X.X....X", "X.X....X", "X..XX..X", ".X....X.", "..XXXX.."],
}

# Curseur du menu (petit champignon 8 x 8 de l'écran titre)
CURSOR = [
    "..RRRR..",
    ".RWRRWR.",
    "RWWRRWWR",
    "RRRRRRRR",
    "KRWWWWRK",
    "..WKKW..",
    "..WWWW..",
    "........",
]
MINI = {
    "0": [".XX.", "X..X", "X..X", "X..X", ".XX."],
    "1": [".X..", "XX..", ".X..", ".X..", "XXX."],
    "2": ["XXX.", "...X", ".XX.", "X...", "XXXX"],
    "4": ["X.X.", "X.X.", "XXXX", "..X.", "..X."],
    "5": ["XXXX", "X...", "XXX.", "...X", "XXX."],
    "8": [".XX.", "X..X", ".XX.", "X..X", ".XX."],
    "U": ["X..X", "X..X", "X..X", "X..X", ".XX."],
    "P": ["XXX.", "X..X", "XXX.", "X...", "X..."],
}


# ---------------------------------------------------------------------------
# Génération procédurale : nuages, buissons, collines
# ---------------------------------------------------------------------------
def _outline(shape):
    """Contour noir d'un masque booléen (pixels du bord)."""
    h, w = shape.shape
    pad = np.pad(shape, 1)
    inner = pad[1:-1, 1:-1] & pad[:-2, 1:-1] & pad[2:, 1:-1] \
        & pad[1:-1, :-2] & pad[1:-1, 2:]
    return shape & ~inner


def cloud_image(n_mid, bush=False):
    """Nuage (ou buisson) de ``n_mid`` segments centraux, largeur (n+2)*16."""
    w = (n_mid + 2) * 16
    h = 16 if bush else 32
    yy, xx = np.mgrid[0:h, 0:w]
    shape = np.zeros((h, w), dtype=bool)
    tops = [8 + 16 * i + 8 for i in range(n_mid)]
    # bosses supérieures
    for i, cx in enumerate(tops):
        shape |= ((xx - cx) / 8.5) ** 2 + ((yy - 11) / 8.0) ** 2 <= 1.0
    shape |= ((xx - 12) / 6.5) ** 2 + ((yy - 14) / 6.0) ** 2 <= 1.0
    shape |= ((xx - (w - 12)) / 6.5) ** 2 + ((yy - 14) / 6.0) ** 2 <= 1.0
    if bush:
        shape |= (yy >= 12) & (xx >= 6) & (xx < w - 6)
    else:
        shape |= (yy >= 12) & (yy <= 22) & (xx >= 7) & (xx < w - 7)
        for cx in range(14, w - 12, 12):
            shape |= ((xx - cx) / 7.0) ** 2 + ((yy - 22) / 4.5) ** 2 <= 1.0
    edge = _outline(shape)
    img = np.full((h, w), ".", dtype="<U1")
    img[shape] = "W"
    if not bush:
        shade = shape & (yy >= 20)
        shade &= ~(((xx % 12) - 6) ** 2 + (yy - 20) ** 2 * 3 < 30)
        img[shade] = "C"
        # petites rides bleues sous les bosses
        for cx in tops:
            m = shape & (np.abs(xx - cx + 3) <= 2) & (yy == 17)
            img[m] = "C"
    else:
        for cx in tops:
            m = shape & (((xx - cx - 3) ** 2 + (yy - 9) ** 2) <= 4)
            img[m] = "C"
    img[edge] = "K"
    return ["".join(r) for r in img]


def hill_image(big):
    """Colline (grande : 80x48, petite : 48x32) : pentes à 45°, sommet rond."""
    w, h = (80, 48) if big else (48, 32)
    r = 10.0 if big else 8.0
    yy, xx = np.mgrid[0:h, 0:w]
    cx = (w - 1) / 2.0
    cy = (h - 1) - cx + np.sqrt(2.0) * r
    slope = (yy >= (h - 1) - np.minimum(xx, w - 1 - xx))
    near = np.abs(xx - cx) <= r / np.sqrt(2.0)
    dome = ((xx - cx) ** 2 + (yy - cy) ** 2 <= r * r) | (near & (yy >= cy))
    shape = np.where(near, dome, slope)
    edge = _outline(shape)
    edge[h - 1, :] = False
    img = np.full((h, w), ".", dtype="<U1")
    img[shape] = "G"
    img[edge] = "K"
    if big:
        spots = [(cx - 9, cy + 9), (cx + 7, cy + 12), (cx - 3, cy + 22),
                 (cx + 13, cy + 25)]
    else:
        spots = [(cx + 2, cy + 8)]
    for sx, sy in spots:
        m = (((xx - sx) / 1.6) ** 2 + ((yy - sy) / 3.6) ** 2 <= 1.0) & shape
        img[m] = "K"
        m2 = (((xx - sx - 4) / 1.6) ** 2 + ((yy - sy + 1) / 3.2) ** 2 <= 1.0)
        img[m2 & shape] = "K"
    return ["".join(r) for r in img]


# ---------------------------------------------------------------------------
# Conversion en tableaux numpy
# ---------------------------------------------------------------------------
_ART = {}


def register(name, art):
    _ART[name] = art


def _register_all():
    for k, v in SMALL.items():
        register("small_" + k, v)
    for k, v in BIG.items():
        register("big_" + k, v)
    register("goomba", GOOMBA)
    register("goomba_flat", GOOMBA_FLAT)
    register("koopa1", KOOPA_1)
    register("koopa2", KOOPA_2)
    register("shell", SHELL)
    register("shell_legs", SHELL_LEGS)
    register("mushroom", MUSHROOM)
    register("flower", FLOWER)
    register("star", STAR)
    register("coin_tile", COIN_TILE)
    for i, a in enumerate(COIN_SPIN):
        register(f"coin_spin{i}", a)
    register("hud_coin", HUD_COIN)
    register("cursor", CURSOR)
    for k in range(4):
        register(f"fireball{k}", ["".join(r) for r in np.rot90(
            np.array([list(r) for r in FIREBALL]), -k)])
    for i, a in enumerate(EXPLOSION):
        register(f"explosion{i}", a)
    register("debris", DEBRIS)
    register("flag", FLAG)
    register("castle_flag", CASTLE_FLAG)
    register("ground", GROUND_T)
    register("brick", BRICK_T)
    register("stair", STAIR_T)
    register("qblock", QBLOCK_T)
    register("used", USED_T)
    register("pipe_top", PIPE_TOP)
    register("pipe_body", PIPE_BODY)
    top = np.array([list(r) for r in PIPE_TOP])
    body = np.array([list(r) for r in PIPE_BODY])
    register("spipe_mouth", ["".join(r) for r in top.T])     # 32 x 16
    register("spipe_body", ["".join(r) for r in body.T])
    register("pole", POLE_T)
    register("ball", BALL_T)
    for k, v in CASTLE.items():
        register("castle_" + k, v)
    for n in (1, 2, 3):
        register(f"cloud{n}", cloud_image(n))
        register(f"bush{n}", cloud_image(n, bush=True))
    register("hill_big", hill_image(True))
    register("hill_small", hill_image(False))
    for ch, g in FONT.items():
        register("font_" + ch, g)
    for ch, g in MINI.items():
        register("mini_" + ch, g)


_register_all()


@lru_cache(maxsize=None)
def get(name, palette, flip=False, vflip=False):
    """Renvoie (image RVB uint8 [h,w,3], masque bool [h,w])."""
    art = _ART[name]
    pal = PAL[palette]
    h = len(art)
    w = max(len(r) for r in art)
    img = np.zeros((h, w, 3), dtype=np.uint8)
    mask = np.zeros((h, w), dtype=bool)
    for y, row in enumerate(art):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            code = pal.get(ch)
            if code is None:
                continue
            img[y, x] = NES_PALETTE[code]
            mask[y, x] = True
    if flip:
        img = img[:, ::-1].copy()
        mask = mask[:, ::-1].copy()
    if vflip:
        img = img[::-1].copy()
        mask = mask[::-1].copy()
    return img, mask


def names():
    return sorted(_ART)
