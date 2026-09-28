"""Constantes du moteur : dimensions, tuiles, physique NES et palette.

Toutes les valeurs physiques reprennent les tables du Super Mario Bros.
original (NES, 1985) telles que documentées par la communauté (désassemblage
« SMBDIS » de doppelganger).  Unités NES :

* position horizontale : pixels + sous-pixels (1/256 de pixel) ;
* vitesse horizontale  : 1/16 de pixel par image (0x18 = 1,5 px/image) ;
* vitesse verticale    : pixels par image + fraction en 1/256 ;
* le jeu tourne à 60 images par seconde (NTSC).
"""

# ---------------------------------------------------------------------------
# Écran / niveau
# ---------------------------------------------------------------------------
TILE = 16                   # taille d'un « bloc » (métatuile) en pixels
SCREEN_W = 256              # largeur de l'écran NES
SCREEN_H = 240              # hauteur de l'écran NES
ROWS = 15                   # 15 rangées de 16 px (les 2 premières = HUD)
FPS = 60

LEVEL_COLS = 212            # 1-1 fait 212 colonnes (3392 px)
GROUND_ROW = 13             # le sol occupe les rangées 13 et 14

# ---------------------------------------------------------------------------
# Codes des tuiles (grille du niveau)
# ---------------------------------------------------------------------------
EMPTY = 0
GROUND = 1
BRICK = 2               # brique simple (cassable si Mario est grand)
BRICK_COIN = 3          # brique à pièces multiples (10 pièces environ)
BRICK_STAR = 4          # brique contenant l'étoile
BRICK_POWERUP = 5       # brique contenant un champignon/fleur (absent en 1-1)
QBLOCK_COIN = 6         # bloc ? contenant une pièce
QBLOCK_POWERUP = 7      # bloc ? contenant champignon / fleur de feu
USED = 8                # bloc vide (déjà frappé)
HIDDEN_1UP = 9          # bloc invisible contenant un champignon 1-UP
STAIR = 10              # bloc dur (escaliers, base du drapeau)
PIPE_TL = 11            # tuyau : haut gauche
PIPE_TR = 12            # tuyau : haut droit
PIPE_L = 13             # tuyau : corps gauche
PIPE_R = 14             # tuyau : corps droit
FLAGPOLE = 15           # mât du drapeau
FLAG_BALL = 16          # boule au sommet du mât
COIN = 17               # pièce libre (salle bonus)
UG_BRICK = 18           # brique souterraine (bleue)
UG_GROUND = 19          # sol souterrain
SPIPE_TOP_MOUTH = 20    # tuyau horizontal : embouchure haut
SPIPE_TOP_BODY = 21     # tuyau horizontal : corps haut
SPIPE_BOT_MOUTH = 22    # tuyau horizontal : embouchure bas
SPIPE_BOT_BODY = 23     # tuyau horizontal : corps bas
SPIPE_JOIN_TOP = 24     # jonction tuyau horizontal / vertical (haut)
SPIPE_JOIN_BOT = 25     # jonction tuyau horizontal / vertical (bas)
N_TILE_TYPES = 26

SOLID_TILES = frozenset({
    GROUND, BRICK, BRICK_COIN, BRICK_STAR, BRICK_POWERUP, QBLOCK_COIN,
    QBLOCK_POWERUP, USED, STAIR, PIPE_TL, PIPE_TR, PIPE_L, PIPE_R,
    UG_BRICK, UG_GROUND, SPIPE_TOP_MOUTH, SPIPE_TOP_BODY, SPIPE_BOT_MOUTH,
    SPIPE_BOT_BODY, SPIPE_JOIN_TOP, SPIPE_JOIN_BOT,
})
# Blocs qui réagissent quand Mario les frappe par dessous.
BUMPABLE_TILES = frozenset({
    BRICK, BRICK_COIN, BRICK_STAR, BRICK_POWERUP, QBLOCK_COIN,
    QBLOCK_POWERUP, HIDDEN_1UP, UG_BRICK,
})
BREAKABLE_TILES = frozenset({BRICK, UG_BRICK})
CLIMB_TILES = frozenset({FLAGPOLE, FLAG_BALL})

# Table de lookup rapide (index = code tuile) pour les tests de solidité.
SOLID_LUT = [t in SOLID_TILES for t in range(N_TILE_TYPES)]

# ---------------------------------------------------------------------------
# Physique du joueur (valeurs NES)
# ---------------------------------------------------------------------------
# Index 0..4 choisi selon la vitesse horizontale absolue au moment du saut.
JUMP_SPEED_THRESHOLDS = (0x09, 0x10, 0x19, 0x1C)
JUMP_MFORCE = (0x20, 0x20, 0x1E, 0x28, 0x28)     # gravité en montée (A tenu)
FALL_MFORCE = (0x70, 0x70, 0x60, 0x90, 0x90)     # gravité en chute
JUMP_Y_SPEED = (-4, -4, -4, -5, -5)              # vitesse verticale initiale
JUMP_INIT_MFORCE = (0x00, 0x00, 0x00, 0x00, 0x00)

MAX_RIGHT_SPEED = (0x28, 0x18, 0x10)             # course / marche / eau
MAX_LEFT_SPEED = (-0x28, -0x18, -0x10)
FRICTION = (0xE4, 0x98, 0xD0)                    # accélérations / frictions
PLAYER_MAX_FALL = 4                              # px / image
RUNNING_TIMER_RESET = 0x0A
SKID_TURN_SPEED = 0x0B                           # sous ce seuil : demi-tour
AIR_RUN_THRESHOLD = 0x19
FAST_FRICTION_THRESHOLD = 0x21
RUN_ANIM_THRESHOLD = 0x1C
WALK_ANIM_THRESHOLD = 0x0E
PLAYER_ANIM_TIMER = (0x02, 0x04, 0x07)

STOMP_BOUNCE_SPEED = -4                          # rebond après écrasement
BRICK_BREAK_Y_SPEED = -2                         # Mario continue après casse

# Points de collision décor (x, y) relatifs à la position du joueur
# (y = haut d'une boîte de 32 px ; le petit Mario occupe y+16..y+31).
# Ordre : tête, pied gauche, pied droit, côté gauche (haut, bas),
# côté droit (haut, bas).
COLL_BIG = ((8, 4), (3, 32), (12, 32), (2, 8), (2, 24), (13, 8), (13, 24))
COLL_SMALL = ((8, 18), (3, 32), (12, 32), (2, 24), (2, 24), (13, 24), (13, 24))

# Boîtes de collision avec les ennemis (x1, y1, x2, y2), relatives.
BBOX_BIG = (2, 8, 14, 32)
BBOX_SMALL = (3, 20, 13, 32)
BBOX_CROUCH = (2, 20, 14, 32)

# ---------------------------------------------------------------------------
# Ennemis et objets
# ---------------------------------------------------------------------------
ENEMY_SPEED = -0x08            # Goomba / Koopa : 0,5 px/image vers la gauche
ENEMY_GRAVITY = 0x3D
ENEMY_MAX_FALL = 3
SHELL_SPEED = 0x30             # carapace frappée : 3 px/image
REVIVED_SPEEDS = (0x08, -0x08)
POWERUP_SPEED = 0x10           # champignon / étoile : 1 px/image
ENEMY_SPAWN_MARGIN = 48        # apparition 48 px après le bord droit
ENEMY_DESPAWN_MARGIN = 72
FIREBALL_SPEED = 0x40
FIREBALL_GRAVITY = 0x50
FIREBALL_MAX_FALL = 3
FIREBALL_BOUNCE = -3

# Boîtes ennemis (relatives au coin haut-gauche d'une boîte 16x24 dont le
# bas coïncide avec les pieds, comme sur NES).
BBOX_GOOMBA = (3, 14, 13, 20)
BBOX_KOOPA = (2, 9, 14, 21)
BBOX_POWERUP = (2, 9, 14, 21)

# ---------------------------------------------------------------------------
# Minuteries (en images)
# ---------------------------------------------------------------------------
INTERVAL = 21                  # les « interval timers » NES : 1 tic / 21 img
GAME_TIMER_START = 400
GAME_TIMER_TICK = 24           # le chrono perd 1 toutes les 24 images
STAR_DURATION = 0x23 * INTERVAL
INJURY_DURATION = 0x08 * INTERVAL
KOOPA_REVIVE = 0x10 * INTERVAL
GOOMBA_FLAT_TIME = 2 * INTERVAL
BRICK_COIN_TIME = 0x0B * INTERVAL
GROW_FRAMES = 59
FIRE_FRAMES = 63
SHRINK_FRAMES = 55
BLOCK_BOUNCE_FRAMES = 0x10
PIPE_ENTRY_FRAMES = 0x30
DEATH_PAUSE = 15

# ---------------------------------------------------------------------------
# Scores
# ---------------------------------------------------------------------------
STOMP_CHAIN_POINTS = (100, 200, 400, 500, 800, 1000, 2000, 4000, 5000, 8000)
SHELL_CHAIN_POINTS = (500, 800, 1000, 2000, 4000, 5000, 8000)
FLAGPOLE_Y_DATA = (0x18, 0x22, 0x50, 0x68, 0x90)
FLAGPOLE_POINTS = (5000, 2000, 800, 400, 100)

# ---------------------------------------------------------------------------
# Manette (bits)
# ---------------------------------------------------------------------------
BTN_RIGHT = 0x01
BTN_LEFT = 0x02
BTN_DOWN = 0x04
BTN_UP = 0x08
BTN_START = 0x10
BTN_SELECT = 0x20
BTN_B = 0x40
BTN_A = 0x80

# ---------------------------------------------------------------------------
# Palette NES (valeurs RVB « classiques » utilisées par la plupart des
# émulateurs pour SMB : ciel 5C94FC, sol C84C0C, etc.)
# ---------------------------------------------------------------------------
NES_PALETTE = {
    0x00: (0x74, 0x74, 0x74), 0x01: (0x24, 0x18, 0x8C), 0x02: (0x00, 0x00, 0xA8),
    0x03: (0x44, 0x00, 0x9C), 0x04: (0x8C, 0x00, 0x74), 0x05: (0xA8, 0x00, 0x10),
    0x06: (0xA4, 0x00, 0x00), 0x07: (0x7C, 0x08, 0x00), 0x08: (0x40, 0x2C, 0x00),
    0x09: (0x00, 0x44, 0x00), 0x0A: (0x00, 0x50, 0x00), 0x0B: (0x00, 0x3C, 0x14),
    0x0C: (0x18, 0x3C, 0x5C), 0x0F: (0x00, 0x00, 0x00),
    0x10: (0xBC, 0xBC, 0xBC), 0x11: (0x00, 0x70, 0xEC), 0x12: (0x20, 0x38, 0xEC),
    0x13: (0x80, 0x00, 0xF0), 0x14: (0xBC, 0x00, 0xBC), 0x15: (0xE4, 0x00, 0x58),
    0x16: (0xD8, 0x28, 0x00), 0x17: (0xC8, 0x4C, 0x0C), 0x18: (0x88, 0x70, 0x00),
    0x19: (0x00, 0x94, 0x00), 0x1A: (0x00, 0xA8, 0x00), 0x1B: (0x00, 0x90, 0x38),
    0x1C: (0x00, 0x80, 0x88),
    0x20: (0xFC, 0xFC, 0xFC), 0x21: (0x3C, 0xBC, 0xFC), 0x22: (0x5C, 0x94, 0xFC),
    0x23: (0xCC, 0x88, 0xFC), 0x24: (0xF4, 0x78, 0xFC), 0x25: (0xFC, 0x74, 0xB4),
    0x26: (0xFC, 0x74, 0x60), 0x27: (0xFC, 0x98, 0x38), 0x28: (0xF0, 0xBC, 0x3C),
    0x29: (0x80, 0xD0, 0x10), 0x2A: (0x4C, 0xDC, 0x48), 0x2B: (0x58, 0xF8, 0x98),
    0x2C: (0x00, 0xE8, 0xD8), 0x2D: (0x78, 0x78, 0x78),
    0x30: (0xFC, 0xFC, 0xFC), 0x31: (0xA8, 0xE4, 0xFC), 0x32: (0xC4, 0xD4, 0xFC),
    0x33: (0xD4, 0xC8, 0xFC), 0x34: (0xFC, 0xC4, 0xFC), 0x35: (0xFC, 0xC4, 0xD8),
    0x36: (0xFC, 0xBC, 0xB0), 0x37: (0xFC, 0xD8, 0xA8), 0x38: (0xFC, 0xE4, 0xA0),
    0x39: (0xE0, 0xFC, 0xA0), 0x3A: (0xA8, 0xF0, 0xBC), 0x3B: (0xB0, 0xFC, 0xCC),
    0x3C: (0x9C, 0xFC, 0xF0), 0x3D: (0xC4, 0xC4, 0xC4),
}
SKY_COLOR = 0x22

# ---------------------------------------------------------------------------
# Codes des observations
# ---------------------------------------------------------------------------
# Observation « tiles » (grille sémantique de l'écran, moteur NES)
OBS_EMPTY = 0
OBS_SOLID = 1        # sol, escaliers, tuyaux, blocs vides
OBS_BRICK = 2
OBS_QBLOCK = 3
OBS_COIN = 4
OBS_ENEMY = 5        # Goomba / Koopa qui marche
OBS_SHELL = 6        # carapace (immobile ou lancée)
OBS_ITEM = 7         # champignon, fleur, étoile, 1-UP
OBS_MARIO = 8
OBS_FLAG = 9         # mât du drapeau
OBS_FIREBALL = 10
N_OBS_CODES = 11

# Codes de la « viewport » de l'article (Ponnock & Ho, section 2.1.2)
P_EMPTY = 0
P_GROUND = 1
P_STEP = 2
P_PIPE = 3
P_BRICK = 4
P_QBLOCK = 5
P_USED = 6
P_GOOMBA = 7
P_FLAG = 8
N_PAPER_CODES = 9
