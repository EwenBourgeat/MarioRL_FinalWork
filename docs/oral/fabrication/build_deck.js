// Génère le diaporama de l'oral final (PowerPoint, importable dans Canva).
//
//   NODE_PATH=<dossier node_modules avec pptxgenjs> node docs/oral/fabrication/build_deck.js
//
// Choix pour l'import Canva : Canva n'importe pas les tableaux PowerPoint,
// donc tableaux et graphiques sont faits de formes et de zones de texte
// (tout reste modifiable). Pas de masque ni d'espace réservé : chaque
// élément est posé directement sur sa diapo.

const fs = require('fs');
const path = require('path');
const pptxgen = require('pptxgenjs');
const { NOTES, PERF, PERF_BEST, COST } = require('./content');

const BUILD = __dirname;
const ORAL = path.resolve(BUILD, '..');
const ASSETS = path.join(BUILD, 'assets');
const VIDEOS = path.join(ORAL, 'videos');
const OUT = process.env.DECK_OUT || path.join(ORAL, 'Oral_RL_Mario.pptx');
const NO_VIDEO = !!process.env.NO_VIDEO;   // aperçu LibreOffice sans les vidéos

// --- charte (reprise du diaporama modèle) ----------------------------------
const W = 13.333, H = 7.5;
const FT = 'Arcade Gamer';      // titres (police du modèle Canva)
const FS = 'Disket Mono';       // sous-titre de la page de titre (modèle)
const FB = 'Montserrat';        // texte courant, lisible, accents français
const SKY = '5A99ED', NAVY = '14183D', PURPLE = '2E1B5B', YEL = 'FFC703';
const WHITE = 'FFFFFF', BLACK = '000000', GREY = '4A5070', ZEBRA = 'EAF1FE';
const G_LIGHT = '6FC72E', G_DARK = '1AA703';
const RED = 'D62839', ORANGE = 'E8790C', GREEN = '15911F';
const ALGO = { ql: '2F6FE4', sarsa: '15911F', mc: 'E8790C', dqn: 'D62839', ours: '7B3FE4', ppo: 'C2338A' };
const LIGHT = { ql: 'DCE7FC', sarsa: 'D9F0DA', mc: 'FDE8D2', dqn: 'F9D9DC', ours: 'E8DEFB', ppo: 'F6DCEB' };

const SP = JSON.parse(fs.readFileSync(path.join(ASSETS, 'sprites', 'sprites.json'), 'utf8'));
const asset = (f) => path.join(ASSETS, f);
const b64 = (f) => 'data:image/png;base64,' + fs.readFileSync(f).toString('base64');

const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE';
pres.author = 'Chris, Ewen, Chloé';
pres.company = 'HPDA 2026';
pres.title = 'Reinforcement Learning in Super Mario Bros - oral final';
pres.subject = 'Veille scientifique : Ponnock et Ho (2026)';
pres.theme = { headFontFace: FT, bodyFontFace: FB };

// ombre « pixel » : décalée, sans flou (comme les titres du modèle)
const sh = (off = 3, color = PURPLE) => ({ type: 'outer', blur: 0, offset: off, angle: 45, color, opacity: 1 });
const NOLINE = { type: 'none' };
// marges d'une zone de texte : pptxgenjs attend [gauche, droite, bas, haut]
const mg = (top, right, bottom, left) => [left, right, bottom, top];
// typographie française : espaces insécables (avant : ; ? ! % », après «,
// milliers « 10 000 », unités « 16 s »)
const NB = '\u00A0';
function fr(t) {
  if (Array.isArray(t)) return t.map((r) => Object.assign({}, r, { text: fr(r.text) }));
  if (typeof t !== 'string') return t;
  return t.replace(/ ([:;?!%»])/g, NB + '$1').replace(/« /g, '«' + NB)
          .replace(/(\d) (\d{3})(?!\d)/g, '$1' + NB + '$2')
          .replace(/(\d) (Wh|kWh|g|s|min|M)(?![\wÀ-ÿ])/g, '$1' + NB + '$2');
}
let slideNo = 0;

function newSlide(section) {
  const s = pres.addSlide({ sectionTitle: section });
  s.background = { color: SKY };
  slideNo += 1;
  return s;
}

// --- éléments communs ---------------------------------------------------------
function sprite(s, name, o = {}) {
  const m = SP[name];
  const k = o.scale || 1;
  const w = m.w * k, h = m.h * k;
  const x = o.x !== undefined ? o.x : m.x;
  let y = o.y !== undefined ? o.y : m.y;
  if (o.bottom !== undefined) y = o.bottom - h;
  s.addImage({ path: path.join(ASSETS, 'sprites', name + '.png'), x, y, w, h, objectName: name,
               flipH: !!o.flipH });
}

function bricks(s) {               // sol en briques du modèle (diapos « Mario »)
  sprite(s, 'ground', { x: 0, y: 6.537, scale: 1 });
}

function greenGround(s) {          // diapos de contenu : simple sol vert
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 7.2, w: W, h: 0.07, fill: { color: G_LIGHT }, line: NOLINE, objectName: 'sol_haut' });
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 7.27, w: W, h: 0.23, fill: { color: G_DARK }, line: NOLINE, objectName: 'sol' });
}

function pageNo(s) {
  s.addText(String(slideNo), { x: W - 1.0, y: 7.27, w: 0.62, h: 0.23, fontFace: FB, fontSize: 10, bold: true,
                               color: WHITE, align: 'right', valign: 'middle', margin: 0, isTextBox: true });
}

function header(s, world, title, msg) {
  s.addText(world, { x: 0.6, y: 0.3, w: 9, h: 0.3, fontFace: FT, fontSize: 12, color: YEL, margin: 0,
                     valign: 'middle', isTextBox: true, shadow: sh(1.5), objectName: 'monde' });
  s.addText(fr(title), { x: 0.6, y: 0.62, w: 12.13, h: 0.6, fontFace: FT, fontSize: 28, color: WHITE, margin: 0,
                     valign: 'middle', isTextBox: true, shadow: sh(2.5), objectName: 'titre' });
  if (msg) {
    s.addText(fr(msg), { x: 0.6, y: 1.27, w: 12.13, h: 0.42, fontFace: FB, fontSize: 16, bold: true, color: NAVY,
                     margin: 0, valign: 'middle', isTextBox: true, objectName: 'message' });
  }
}

function content(section, world, title, msg) {
  const s = newSlide(section);
  greenGround(s);
  header(s, world, title, msg);
  pageNo(s);
  return s;
}

function card(s, x, y, w, h, fill = WHITE, name = 'carte') {
  s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: fill }, line: { color: BLACK, width: 1.5 },
                                      shadow: sh(3.5), objectName: name });
}

function tag(s, text, x, y, w, fill = NAVY, color = WHITE, size = 12) {
  w = Math.max(w, text.length * size * 0.0088 + 0.32);      // assez large pour tenir sur une ligne
  s.addText(fr(text), { x, y, w, h: 0.36, fontFace: FB, fontSize: size, bold: true, color, fill: { color: fill },
                    margin: mg(0, 8, 0, 8), valign: 'middle', isTextBox: true, charSpacing: 0.5, objectName: 'etiquette' });
}

function txt(s, text, x, y, w, h, o = {}) {
  s.addText(fr(text), Object.assign({ x, y, w, h, fontFace: FB, fontSize: 14, color: NAVY, margin: 0,
                                  valign: 'top', isTextBox: true }, o));
}

// liste à puces : items = chaînes ou [gras, suite]
function bullets(s, items, x, y, w, h, o = {}) {
  const size = o.fontSize || 14;
  const runs = [];
  items.forEach((it, i) => {
    const last = i === items.length - 1;
    const base = { bullet: { indent: 14 }, paraSpaceAfter: o.space || 7, breakLine: false };
    if (Array.isArray(it)) {
      runs.push({ text: fr(it[0]), options: Object.assign({}, base, { bold: true }) });
      runs.push({ text: fr(it[1]), options: { breakLine: !last } });   // même paragraphe (voir fix_pptx.py)
    } else {
      runs.push({ text: fr(it), options: Object.assign({}, base, { breakLine: !last }) });
    }
  });
  s.addText(runs, Object.assign({ x, y, w, h, fontFace: FB, fontSize: size, color: NAVY, margin: 0, valign: 'top',
                                  isTextBox: true, lineSpacingMultiple: 1.05 }, o.box || {}));
}

// petit carré de couleur (algorithme)
function chip(s, x, y, key, size = 0.2) {
  s.addShape(pres.shapes.RECTANGLE, { x, y, w: size, h: size, fill: { color: ALGO[key] }, line: { color: BLACK, width: 0.75 } });
}

// tableau en formes (Canva n'importe pas les tableaux PowerPoint)
function table(s, { x, y, colW, headH, rowH, head, rows, keys, best = [], size = 13, headSize = 11.5, firstBold = true, leftCols = [] }) {
  const totW = colW.reduce((a, b) => a + b, 0);
  const totH = headH + rowH * rows.length;
  s.addShape(pres.shapes.RECTANGLE, { x: x - 0.02, y: y - 0.02, w: totW + 0.04, h: totH + 0.04, fill: { color: NAVY },
                                      line: { color: BLACK, width: 1.5 }, shadow: sh(3.5), objectName: 'tableau_fond' });
  let cx = x;
  head.forEach((hd, j) => {
    const left = j === 0 || leftCols.includes(j);
    s.addText(fr(hd), { x: cx, y, w: colW[j], h: headH, fontFace: FB, fontSize: headSize, bold: true, color: WHITE,
                    fill: { color: NAVY }, align: left ? 'left' : 'center', valign: 'middle',
                    margin: mg(2, 6, 2, left ? 10 : 6), isTextBox: true, objectName: 'entete' });
    cx += colW[j];
  });
  rows.forEach((row, i) => {
    let cxx = x;
    const ry = y + headH + i * rowH;
    row.forEach((cell, j) => {
      const isBest = best.some(([bi, bj]) => bi === i && bj === j - 1);
      const fill = isBest ? 'FFE27A' : (i % 2 ? ZEBRA : WHITE);
      if (j === 0) {
        s.addText(fr(cell), { x: cxx, y: ry, w: colW[j], h: rowH, fontFace: FB, fontSize: size, bold: firstBold,
                          color: NAVY, fill: { color: fill }, valign: 'middle', margin: mg(0, 4, 0, keys ? 30 : 10),
                          isTextBox: true, objectName: 'cellule' });
        if (keys) chip(s, cxx + 0.12, ry + rowH / 2 - 0.1, keys[i]);
      } else {
        const left = leftCols.includes(j);
        s.addText(fr(cell), { x: cxx, y: ry, w: colW[j], h: rowH, fontFace: FB, fontSize: size, bold: isBest,
                          color: NAVY, fill: { color: fill }, align: left ? 'left' : 'center', valign: 'middle',
                          margin: left ? mg(2, 6, 2, 10) : 2, isTextBox: true, objectName: 'cellule' });
      }
      cxx += colW[j];
    });
  });
  return y + totH;
}

// barres horizontales : items = {label, value (0-100), text, color, bold}
function hbars(s, { x, y, labelW, barW, rowH, items, size = 13, max = 100 }) {
  items.forEach((it, i) => {
    const ry = y + i * rowH;
    const bh = rowH * 0.56;
    txt(s, it.label, x, ry, labelW - 0.12, rowH, { fontSize: size, bold: true, valign: 'middle' });
    s.addShape(pres.shapes.RECTANGLE, { x: x + labelW, y: ry + (rowH - bh) / 2, w: barW, h: bh,
                                        fill: { color: 'D9E3F5' }, line: NOLINE });
    const bw = Math.max(0.05, barW * it.value / max);
    s.addShape(pres.shapes.RECTANGLE, { x: x + labelW, y: ry + (rowH - bh) / 2, w: bw, h: bh,
                                        fill: { color: it.color }, line: { color: BLACK, width: 1 } });
    const inside = it.value / max > 0.78;
    txt(s, it.text, inside ? x + labelW + bw - 1.25 : x + labelW + bw + 0.08, ry, 1.17, rowH,
        { fontSize: size, bold: true, valign: 'middle', align: inside ? 'right' : 'left',
          color: inside ? WHITE : NAVY });
  });
}

// vidéo : image de remplacement (nom du fichier) + vidéo par-dessus
function video(s, name, x, y, w, h) {
  const base = name.replace('.mp4', '');
  s.addImage({ path: asset('fallback_' + base + '.png'), x, y, w, h, objectName: 'remplacement_' + base });
  if (!NO_VIDEO) {
    s.addMedia({ type: 'video', path: path.join(VIDEOS, name), x, y, w, h, cover: b64(asset('poster_' + base + '.png')),
                 objectName: 'video_' + base });
  }
  s.addShape(pres.shapes.RECTANGLE, { x: x - 0.03, y: y - 0.03, w: w + 0.06, h: h + 0.06, fill: { type: 'none' },
                                      line: { color: BLACK, width: 2 }, objectName: 'cadre_video' });
}

function kpi(s, x, y, w, h, value, label, o = {}) {
  card(s, x, y, w, h, o.fill || WHITE, 'kpi');
  txt(s, value, x + 0.15, y + 0.08, w - 0.3, h * 0.55, { fontSize: o.size || 26, bold: true, color: o.color || NAVY,
                                                        valign: 'middle', fontFace: FB });
  txt(s, label, x + 0.15, y + h * 0.58, w - 0.3, h * 0.38, { fontSize: o.labelSize || 11.5, color: GREY, valign: 'top' });
}

// grand titre des diapos « Mario » (blanc, ombre violette)
function bigTitle(s, text, x, y, w, h, size, color = WHITE, align = 'center') {
  s.addText(fr(text), { x, y, w, h, fontFace: FT, fontSize: size, color, align, valign: 'middle', margin: 0,
                    isTextBox: true, shadow: sh(Math.max(2, size * 0.05)), lineSpacingMultiple: 1.0, objectName: 'grand_titre' });
}

// =============================================================================
// DIAPOS
// =============================================================================

// 1. Titre ---------------------------------------------------------------------
{
  pres.addSection({ title: 'Introduction' });
  const s = newSlide('Introduction');
  ['hearts', 'coin_pipe', 'pipe_short', 'goomba', 'mario', 'tree', 'castle_peach', 'pill'].forEach((n) => sprite(s, n));
  bricks(s);
  bigTitle(s, 'REINFORCEMENT\nLEARNING', 0.5, 0.9, W - 1.0, 1.9, 54);
  s.addText('IN SUPER MARIO BROS : CURRICULUM, PEDAGOGY, AND OPTIMAL\nLEVEL DESIGN IN WORLD 1-1', {
    x: 1.0, y: 2.95, w: W - 2.0, h: 0.62, fontFace: FS, fontSize: 15.8, color: WHITE, align: 'center', valign: 'middle',
    margin: 0, isTextBox: true, shadow: sh(1.2), objectName: 'sous_titre' });
  s.addText('Veille scientifique · Ponnock & Ho (2026)', { x: 3.5, y: 3.62, w: W - 7.0, h: 0.34, fontFace: FB, fontSize: 13,
    bold: true, color: NAVY, align: 'center', valign: 'middle', margin: 0, isTextBox: true });
  const p = SP.pill;
  s.addText('CHRIS, EWEN, CHLOÉ', { x: p.x, y: p.y, w: p.w, h: p.h, fontFace: FT, fontSize: 12.5, color: BLACK,
    align: 'center', valign: 'middle', margin: 0, isTextBox: true, objectName: 'noms' });
  s.addText('HPDA 2026', { x: 5.2, y: 7.07, w: 2.93, h: 0.32, fontFace: FT, fontSize: 13.5, color: WHITE, align: 'center',
    valign: 'middle', margin: 0, isTextBox: true });
  s.addNotes(NOTES.title);
}

// 2. Le parcours (sommaire) -------------------------------------------------------
{
  const s = newSlide('Introduction');
  ['star_brick', 'coin_pipe2', 'pipe_tall'].forEach((n) => sprite(s, n));
  bricks(s);
  bigTitle(s, 'LE PARCOURS', 2.0, 1.85, W - 4.0, 0.78, 46);
  s.addText('4 MONDES  -  20 MINUTES', { x: 2.5, y: 2.72, w: W - 5.0, h: 0.42, fontFace: FT, fontSize: 17, color: WHITE,
    align: 'center', valign: 'middle', margin: 0, isTextBox: true, shadow: sh(1.5) });
  const worlds = [['1-1', 'LA VEILLE'], ['1-2', 'LE DUEL\nSUR V3'], ['1-3', 'LE VRAI\nJEU NES'], ['1-4', 'LE RECUL']];
  const bw = 2.0, bh = 1.088, gap = 0.22;
  const x0 = (W - (4 * bw + 3 * gap)) / 2;
  worlds.forEach(([n, label], i) => {
    const bx = x0 + i * (bw + gap), by = 3.95;
    s.addImage({ path: path.join(ASSETS, 'sprites', 'yellow_box.png'), x: bx, y: by, w: bw, h: bh, objectName: 'bloc_jaune' });
    s.addText([{ text: 'WORLD ' + n, options: { fontSize: 13, breakLine: true } },
               { text: label, options: { fontSize: 13 } }],
      { x: bx + 0.08, y: by + 0.06, w: bw - 0.16, h: bh - 0.14, fontFace: FT, color: BLACK, align: 'center',
        valign: 'middle', margin: 0, isTextBox: true, lineSpacingMultiple: 1.1 });
  });
  s.addNotes(NOTES.agenda);
}

// séparateurs de parties (style Mario) ----------------------------------------------
function divider(section, world, label, sub, decorate, note) {
  pres.addSection({ title: section });
  const s = newSlide(section);
  decorate(s);
  bricks(s);
  bigTitle(s, 'WORLD ' + world, 2.2, 1.35, W - 4.4, 0.95, 54);
  bigTitle(s, label, 2.2, 2.32, W - 4.4, 0.7, 32, YEL);
  s.addText(sub, { x: 3.0, y: 3.12, w: W - 6.0, h: 0.42, fontFace: FB, fontSize: 16, bold: true, color: NAVY,
                   align: 'center', valign: 'middle', margin: 0, isTextBox: true });
  s.addNotes(note);
  return s;
}

// =============================================================================
// WORLD 1-1 : LA VEILLE
// =============================================================================
divider('1-1 La veille', '1-1', 'LA VEILLE', "L'article, ses résultats, notre regard critique", (s) => {
  ['piranha', 'pipe_short2', 'pipe_tall2'].forEach((n) => sprite(s, n));
  sprite(s, 'star_brick', { x: 11.625, y: 2.125 });
  // les 4 pièces du modèle (page « Are you ready? »)
  [4.847, 5.759, 6.676, 7.588].forEach((x) => sprite(s, 'coin', { x, y: 4.824 }));
}, NOTES.d1);

{
  const s = content('1-1 La veille', 'WORLD 1-1 - LA VEILLE', "L'ARTICLE", 'Le niveau 1-1 est-il vraiment une leçon de game design ? Les auteurs le testent avec des IA.');
  card(s, 0.6, 1.9, 6.0, 3.05);
  tag(s, "L'ARTICLE ÉTUDIÉ", 0.6, 1.9, 2.25, NAVY);
  txt(s, 'Reinforcement Learning in Super Mario Bros: Curriculum, Pedagogy, and Optimal Level Design in World 1-1',
      0.85, 2.42, 5.5, 0.85, { fontSize: 15, bold: true, italic: true });
  txt(s, 'Jesse Ponnock & Lucas Ho · Johns Hopkins University', 0.85, 3.3, 5.5, 0.3, { fontSize: 13 });
  txt(s, 'arXiv:2606.29511 · 28 juin 2026 · prépublication, pas encore relue par des pairs', 0.85, 3.6, 5.5, 0.5,
      { fontSize: 12, color: GREY });
  [['4', 'algorithmes'], ['3', 'niveaux (v1 à v3)'], ['120', 'entraînements']].forEach(([n, l], i) => {
    const cx = 0.85 + i * 1.86;
    s.addText([{ text: n + ' ', options: { bold: true, fontSize: 17 } }, { text: l, options: { fontSize: 11.5 } }],
      { x: cx, y: 4.25, w: 1.74, h: 0.5, fontFace: FB, color: WHITE, fill: { color: NAVY }, align: 'center',
        valign: 'middle', margin: 2, isTextBox: true });
  });
  // les deux questions de recherche
  [['Q1', 'Quel algorithme apprend le mieux le niveau, et cela dépend-il de sa difficulté ?'],
   ['Q2', "L'ordre d'origine des 6 morceaux du niveau accélère-t-il l'apprentissage ?"]].forEach(([q, t], i) => {
    const y = 1.9 + i * 1.58;
    card(s, 6.95, y, 5.78, 1.42, YEL);
    s.addText(q, { x: 7.12, y: y + 0.2, w: 0.9, h: 1.0, fontFace: FT, fontSize: 26, color: NAVY, valign: 'middle',
                   margin: 0, isTextBox: true });
    txt(s, t, 8.0, y + 0.16, 4.55, 1.1, { fontSize: 15, bold: true, valign: 'middle' });
  });
  // frise de veille
  s.addText("VEILLE : D'OÙ VIENT L'ARTICLE", { x: 0.6, y: 5.18, w: 6, h: 0.3, fontFace: FB, fontSize: 12, bold: true,
    color: YEL, margin: 0, isTextBox: true, shadow: sh(1.2), charSpacing: 1 });
  s.addShape(pres.shapes.RECTANGLE, { x: 1.2, y: 5.93, w: 10.95, h: 0.06, fill: { color: WHITE }, line: NOLINE });
  const tl = [['1992', 'Q-Learning\nWatkins & Dayan'], ['1994', 'SARSA\nRummery & Niranjan'], ['2009', 'Curriculum learning\nBengio et al.'],
              ['2015', 'DQN\nMnih et al., Nature'], ['2017', 'PPO\nSchulman et al.'], ['2018', 'gym-super-mario-bros\nKautenja'],
              ['2026', "L'article\nPonnock & Ho"]];
  tl.forEach(([yr, lab], i) => {
    const cx = 1.45 + i * (10.45 / 6);
    const last = i === tl.length - 1;
    s.addShape(pres.shapes.RECTANGLE, { x: cx - 0.09, y: 5.87, w: 0.18, h: 0.18, fill: { color: last ? YEL : WHITE },
                                        line: { color: BLACK, width: 1 } });
    s.addText(yr, { x: cx - 0.8, y: 5.5, w: 1.6, h: 0.32, fontFace: FT, fontSize: 12, color: last ? YEL : WHITE,
                    align: 'center', valign: 'middle', margin: 0, isTextBox: true, shadow: sh(1.2) });
    txt(s, lab, cx - 0.87, 6.12, 1.74, 0.62, { fontSize: 10.5, bold: true, align: 'center', lineSpacingMultiple: 0.95 });
  });
  s.addNotes(NOTES.article);
}

{
  const s = content('1-1 La veille', 'WORLD 1-1 - LA VEILLE', 'LE TERRAIN ET LES JOUEURS',
    'Une grille de 212 × 14 cases, 3 boutons, et 4 algorithmes en compétition.');
  const lw = 12.13, lh = lw * 176 / 3392;
  s.addImage({ path: asset('level_v3.png'), x: 0.6, y: 1.92, w: lw, h: lh, objectName: 'niveau_v3' });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.58, y: 1.9, w: lw + 0.04, h: lh + 0.04, fill: { type: 'none' }, line: { color: BLACK, width: 1.5 } });
  txt(s, 'Le niveau v3 en entier : terrain (v1) + briques et blocs ? (v2) + 17 ennemis (v3)', 0.6, 2.62, 12.13, 0.28,
      { fontSize: 12, bold: true, color: NAVY });
  // règles
  card(s, 0.6, 3.05, 4.6, 3.85);
  tag(s, 'LES RÈGLES', 0.6, 3.05, 1.55);
  txt(s, '3 boutons', 0.8, 3.55, 2, 0.3, { fontSize: 13, bold: true });
  ['RIEN', 'DROITE', 'SAUT'].forEach((b, i) => {
    s.addText(b, { x: 0.8 + i * 1.38, y: 3.88, w: 1.25, h: 0.38, fontFace: FT, fontSize: 11, color: WHITE,
                   fill: { color: NAVY }, align: 'center', valign: 'middle', margin: 0, isTextBox: true });
  });
  txt(s, 'Récompenses', 0.8, 4.42, 2, 0.3, { fontSize: 13, bold: true });
  const rew = [['+100', 'drapeau'], ['-50', 'mort'], ['+0,5', 'pas à droite'], ['-0,1', 'sur place'],
               ['+5', 'Goomba'], ['+3', 'bloc ?'], ['+1', 'brique']];
  rew.forEach(([v, l], i) => {
    const col = i < 4 ? 0 : 1, row = i < 4 ? i : i - 4;
    const cx = 0.8 + col * 2.2, cy = 4.75 + row * 0.38;
    s.addText([{ text: v + '  ', options: { bold: true, color: v.startsWith('-') ? RED : GREEN } },
               { text: l, options: { color: NAVY } }],
      { x: cx, y: cy, w: 2.15, h: 0.34, fontFace: FB, fontSize: 13, valign: 'middle', margin: 0, isTextBox: true });
  });
  txt(s, "L'IA de l'article voit sa case et 4 lignes autour d'elle (115 nombres).", 0.8, 6.3, 4.25, 0.5, { fontSize: 11.5, color: GREY });
  // 4 algorithmes
  const algos = [['Q-LEARNING', 'ql', 'Corrige sa note à chaque pas, en visant le meilleur coup suivant.', 'à chaque pas'],
                 ['SARSA', 'sarsa', 'Corrige à chaque pas avec le coup vraiment joué, hasard compris : plus prudent.', 'à chaque pas'],
                 ['MONTE CARLO', 'mc', 'Attend la fin de la partie, puis crédite tous les coups avec le score final.', 'en fin de partie'],
                 ['DQN', 'dqn', 'Un réseau de neurones remplace le tableau, avec une mémoire de 50 000 coups.', 'par paquets de souvenirs']];
  algos.forEach(([n, k, d, f], i) => {
    const cx = 5.5 + (i % 2) * 3.68, cy = 3.05 + Math.floor(i / 2) * 1.98;
    card(s, cx, cy, 3.55, 1.82);
    tag(s, n, cx, cy, 2.0, ALGO[k]);
    txt(s, d, cx + 0.18, cy + 0.48, 3.2, 0.9, { fontSize: 13.5, valign: 'top' });
    txt(s, [{ text: 'Apprend : ', options: { bold: true } }, { text: f }], cx + 0.18, cy + 1.4, 3.25, 0.3,
        { fontSize: 11.5, color: ALGO[k], valign: 'middle' });
  });
  s.addNotes(NOTES.terrain);
}

{
  const s = content('1-1 La veille', 'WORLD 1-1 - LA VEILLE', "CE QUE TROUVE L'ARTICLE",
    "Monte Carlo gagne sur v3, et l'ordre d'origine du niveau accélère son apprentissage.");
  card(s, 0.6, 1.9, 6.0, 4.98);
  tag(s, 'Q1 · QUI APPREND LE MIEUX ?', 0.6, 1.9, 3.2);
  txt(s, 'Victoires sur la v3 (moyenne de 5 graines, 10 000 épisodes)', 0.85, 2.42, 5.6, 0.3, { fontSize: 12, color: GREY });
  hbars(s, { x: 0.85, y: 2.8, labelW: 1.75, barW: 3.65, rowH: 0.52, items: [
    { label: 'Monte Carlo', value: 94.9, text: '94,9 %', color: ALGO.mc },
    { label: 'Q-Learning', value: 86.5, text: '86,5 %', color: ALGO.ql },
    { label: 'SARSA', value: 84.4, text: '84,4 %', color: ALGO.sarsa },
    { label: 'DQN', value: 76.4, text: '76,4 %', color: ALGO.dqn }] });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.85, y: 5.07, w: 5.5, h: 1.6, fill: { color: 'FFF4C2' }, line: { color: BLACK, width: 1 } });
  txt(s, [{ text: 'DQN : 10,6 % en v1, 93,4 % en v2. ', options: { bold: true } },
          { text: 'Sans blocs à frapper, il ne reçoit presque que des morts : il lui faut des récompenses fréquentes (« densité de récompense »).' }],
      1.0, 5.15, 5.2, 1.45, { fontSize: 13, valign: 'middle' });
  card(s, 6.95, 1.9, 5.78, 4.98);
  tag(s, "Q2 · L'ORDRE DU NIVEAU COMPTE-T-IL ?", 6.95, 1.9, 4.05);
  txt(s, 'Monte Carlo, v3 découpée en 6 morceaux (A à F)', 7.2, 2.42, 5.3, 0.3, { fontSize: 12, color: GREY });
  [["Ordre d'origine", 'A B C D E F', '94,7 %', '0 échec sur 10', GREEN],
   ['10 ordres au hasard', 'mélangés', '89,0 %', '1 échec sur 50', ORANGE],
   ['Ordre inversé', 'F E D C B A', '48,5 %', '4 échecs sur 10', RED]].forEach(([a, b, v, f, c], i) => {
    const cy = 2.85 + i * 0.78;
    s.addShape(pres.shapes.RECTANGLE, { x: 7.2, y: cy, w: 5.28, h: 0.66, fill: { color: i % 2 ? ZEBRA : WHITE }, line: { color: 'C8D3EA', width: 0.75 } });
    txt(s, [{ text: a, options: { bold: true, breakLine: true } }, { text: b, options: { fontSize: 11, color: GREY } }],
        7.35, cy + 0.04, 2.3, 0.6, { fontSize: 13.5, valign: 'middle' });
    txt(s, v, 9.6, cy, 1.35, 0.66, { fontSize: 22, bold: true, color: c, valign: 'middle', align: 'center' });
    txt(s, f, 10.95, cy, 1.45, 0.66, { fontSize: 12, valign: 'middle', align: 'center' });
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 7.2, y: 5.25, w: 5.28, h: 1.42, fill: { color: 'FFF4C2' }, line: { color: BLACK, width: 1 } });
  txt(s, [{ text: "DQN : ~76 % quel que soit l'ordre. ", options: { bold: true } },
          { text: "Sa mémoire tire ses souvenirs au hasard parmi toutes les parties : l'ordre est effacé. Conclusion des auteurs : le 1-1 a une vraie structure pédagogique." }],
      7.35, 5.32, 5.0, 1.3, { fontSize: 13, valign: 'middle' });
  s.addNotes(NOTES.findings);
}

{
  const s = content('1-1 La veille', 'WORLD 1-1 - LA VEILLE', 'NOTRE LECTURE CRITIQUE',
    'Une question originale, mais des erreurs et un protocole fragile.');
  const cols = [
    ['FORCES', GREEN, ["Question originale : mesurer la « pédagogie » d'un niveau avec des IA",
      'Environnement codé de zéro, en 3 niveaux de difficulté',
      'Expérience de contrôle avec DQN, qui isole le rôle de la mémoire',
      'La densité de récompense proposée comme critère de choix']],
    ['ERREURS', RED, ['Ordre inversé : 94,7 % dans le texte, 48,5 % dans leur tableau',
      'Traverser le niveau : ~198 pas × 0,5, pas 99 × 0,5',
      '« Seul ordre sans échec » : faux, 9 ordres au hasard sur 10 aussi',
      'Monte Carlo v3 : 94,9 % (tableau) ou 94,7 % (conclusion) ?',
      'Mort dite « aléatoire » dans un jeu déterministe']],
    ['FAIBLESSES', ORANGE, ['10 ordres testés sur 720 possibles',
      'Effectifs inégaux (10 graines contre 5) ; d = 7,04 avec 5 graines',
      'Seul le DQN réglé à la main',
      'Physique « fidèle à la NES » : saut fixe, ni gauche ni course',
      'Pas de code publié',
      "Une IA qui apprend vite ne prouve pas qu'un humain apprend mieux"]]];
  cols.forEach(([t, c, items], i) => {
    const cx = 0.6 + i * 4.14;
    card(s, cx, 1.9, 3.85, 4.98);
    tag(s, t, cx, 1.9, 1.75, c);
    bullets(s, items, cx + 0.2, 2.5, 3.48, 4.3, { fontSize: 14.5, space: 12 });
  });
  s.addNotes(NOTES.critique);
}

// =============================================================================
// WORLD 1-2 : LE DUEL SUR V3
// =============================================================================
divider('1-2 Le duel sur v3', '1-2', 'LE DUEL SUR V3', 'Q-Learning, SARSA, Monte Carlo et DQN, à égalité', (s) => {
  ['coin_brick', 'brick', 'qblock_bricks'].forEach((n) => sprite(s, n));
  sprite(s, 'mario', { x: 5.15, bottom: 6.565 });
  sprite(s, 'goomba', { x: 7.45, bottom: 6.565 });
}, NOTES.d2);

{
  const s = content('1-2 Le duel sur v3', 'WORLD 1-2 - LE DUEL SUR V3', 'NOTRE MARIO, NOTRE PROTOCOLE',
    'On a recréé le niveau 1-1, puis on a mis tous les algorithmes dans les mêmes conditions.');
  card(s, 0.6, 1.9, 7.4, 4.98);
  tag(s, 'ON A RECRÉÉ LE NIVEAU 1-1', 0.6, 1.9, 3.0);
  s.addImage({ path: asset('ecran_titre.png'), x: 0.85, y: 2.5, w: 3.3, h: 3.094, objectName: 'ecran_titre' });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.83, y: 2.48, w: 3.34, h: 3.134, fill: { type: 'none' }, line: { color: BLACK, width: 1.25 } });
  txt(s, "Notre écran titre : version NES, version de l'article, menu MODELES", 0.85, 5.7, 3.3, 0.9, { fontSize: 11, color: GREY });
  bullets(s, [['Physique NES ', 'au sous-pixel près, en Python'],
              ['Carte et ennemis ', 'vérifiés case par case contre les données du jeu d\'origine'],
              ['2 environnements : ', "MarioGrid (la grille de l'article) et MarioNES (le vrai jeu)"],
              ['Menu MODELES ', 'pour regarder jouer nos IA'],
              ['103 tests ', 'automatiques']], 4.45, 2.55, 3.38, 4.2, { fontSize: 13.5, space: 10 });
  card(s, 8.3, 1.9, 4.43, 4.98, YEL);
  s.addText('MÊME PROTOCOLE POUR TOUS', { x: 8.3, y: 1.9, w: 4.43, h: 0.42, fontFace: FB, fontSize: 13, bold: true, color: WHITE,
    fill: { color: NAVY }, align: 'center', valign: 'middle', margin: 0, isTextBox: true });
  [['Niveau', 'v3 (17 ennemis)'], ['Durée', '6000 épisodes'], ['Graines', '5 (42 à 46)'], ['Machine', 'MacBook Air M4'],
   ['Énergie', 'mesurée par CodeCarbon']].forEach(([k, v], i) => {
    const cy = 2.48 + i * 0.44;
    txt(s, k, 8.5, cy, 1.25, 0.4, { fontSize: 13.5, bold: true, valign: 'middle' });
    txt(s, v, 9.75, cy, 2.85, 0.4, { fontSize: 13.5, valign: 'middle' });
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 8.5, y: 4.78, w: 4.03, h: 1.9, fill: { color: WHITE }, line: { color: BLACK, width: 1 } });
  txt(s, [{ text: '+ 2 tests ajoutés', options: { bold: true, breakLine: true } },
          { text: 'Test glouton : ', options: { bold: true } }, { text: '1 partie sans aucun hasard', options: { breakLine: true } },
          { text: 'Test de robustesse : ', options: { bold: true } },
          { text: '50 parties avec 2 % de boutons au hasard, le même pour tous' }],
      8.65, 4.86, 3.75, 1.75, { fontSize: 13, valign: 'middle', paraSpaceAfter: 4 });
  s.addNotes(NOTES.protocole);
}

{
  const s = content('1-2 Le duel sur v3', 'WORLD 1-2 - LE DUEL SUR V3', 'LES TABLEAUX APPRENNENT VITE',
    'Q-Learning, SARSA et Monte Carlo gagnent 94 à 96 % des parties en 6000 épisodes.');
  const vw = 9.0, vh = vw * 666 / 1920;
  video(s, '01_qlearning_progression.mp4', 0.6, 1.92, vw, vh);
  txt(s, 'Vidéo : la même IA (Q-Learning, graine 42) à 4 moments de son entraînement', 0.6, 1.92 + vh + 0.08, vw, 0.3,
      { fontSize: 12, bold: true });
  [['94,5 %', 'Q-Learning', 'ql'], ['96,2 %', 'SARSA', 'sarsa'], ['96,2 %', 'Monte Carlo', 'mc']].forEach(([v, n, k], i) => {
    const cy = 1.92 + i * 1.06;
    card(s, 9.9, cy, 2.83, 0.92);
    txt(s, v, 10.1, cy + 0.04, 2.45, 0.5, { fontSize: 24, bold: true, valign: 'middle' });
    chip(s, 10.12, cy + 0.6, k, 0.16);
    txt(s, n + ' · victoires', 10.36, cy + 0.52, 2.3, 0.32, { fontSize: 11.5, color: GREY, valign: 'middle' });
  });
  txt(s, '5 parties sans hasard gagnées sur 5, pour les 3', 9.9, 5.08, 2.83, 0.42, { fontSize: 11.5, bold: true, align: 'center' });
  card(s, 0.6, 5.6, 12.13, 1.28, 'FFF4C2');
  txt(s, [{ text: 'Monte Carlo attend les Goombas : ', options: { bold: true } },
          { text: "503 pas par partie et 12 ennemis écrasés, contre ~267 pas et 6 à 7 ennemis pour les deux autres. C'est sa logique : dans une partie gagnée, il récompense tous les coups, même les attentes. Et c'est sûr : il meurt peu (3,7 %)." }],
      0.85, 5.65, 11.7, 1.18, { fontSize: 14, valign: 'middle' });
  s.addNotes(NOTES.tableaux);
}

{
  const s = content('1-2 Le duel sur v3', 'WORLD 1-2 - LE DUEL SUR V3', 'DQN : DE 40 % À 94 %',
    "Le DQN de l'article échoue chez nous. En lui montrant tout l'écran, il devient le plus robuste.");
  const vw = 12.13, vh = vw * 338 / 1920;
  video(s, '02_dqn_article_vs_notre.mp4', 0.6, 1.92, vw, vh);
  txt(s, "Vidéo, même graine (44) : le DQN de l'article meurt colonne 154, le nôtre atteint le drapeau en 244 pas",
      0.6, 1.92 + vh + 0.08, vw, 0.3, { fontSize: 12, bold: true });
  const y0 = 4.55;
  card(s, 0.6, y0, 7.25, 2.33);
  tag(s, 'ÉTAPE PAR ÉTAPE · victoires, graines 42-43', 0.6, y0, 4.45);
  hbars(s, { x: 0.8, y: y0 + 0.45, labelW: 3.05, barW: 2.75, rowH: 0.36, size: 12, items: [
    { label: "0 · DQN de l'article", value: 44.2, text: '44 %', color: ALGO.dqn },
    { label: '1 · + vue complète', value: 81.8, text: '82 %', color: ALGO.ours },
    { label: '2 · 1 + Double DQN, 3 pas…', value: 78.2, text: '78 %', color: 'A99AD6' },
    { label: '3 · 1 + réseau convolutif', value: 76.6, text: '77 %', color: 'A99AD6' },
    { label: '4 · 1 + réglages fins', value: 94.5, text: '94,5 %', color: ALGO.ours }] });
  card(s, 8.15, y0, 4.58, 2.33, YEL);
  bullets(s, [["Il ne voyait que 4 lignes ", 'et son numéro de colonne : il apprenait le niveau par cœur.'],
              ['Vue complète : ', '14 × 28 cases en 6 calques (sol, briques, blocs, ennemis et leur sens).'],
              ['Optimisé avec Claude ', '(assistant IA), vérifié étape par étape.']],
          8.33, y0 + 0.15, 4.25, 2.1, { fontSize: 12.5, space: 6 });
  s.addNotes(NOTES.dqn);
}

{
  const s = content('1-2 Le duel sur v3', 'WORLD 1-2 - LE DUEL SUR V3', 'LE TABLEAU FINAL',
    'À hasard égal, notre DQN est le plus robuste ; les tableaux font presque aussi bien.');
  const head = ['Algorithme', 'Victoires¹', 'Robustesse²', 'Partie sans\nhasard gagnée', 'Retour\nmoyen', 'Parties pour\n80 % de victoires', 'Morts'];
  const end = table(s, { x: 0.6, y: 1.92, colW: [2.55, 1.75, 1.85, 1.6, 1.4, 1.75, 1.23], headH: 0.66, rowH: 0.55,
    head, rows: PERF.map((r) => [r[0], ...r.slice(2)]), keys: PERF.map((r) => r[1]), best: PERF_BEST, size: 13.5 });
  txt(s, "¹ 500 dernières parties d'entraînement, avec une part de hasard différente (1 % tableaux, 2 % notre DQN, 5 % DQN de l'article).   ² 50 parties avec 2 % de boutons au hasard : le même test pour tous, c'est la colonne à comparer.",
      0.6, end + 0.06, 12.13, 0.42, { fontSize: 11, color: NAVY });
  card(s, 0.6, 5.85, 12.13, 1.03, 'FFF4C2');
  txt(s, [{ text: 'Face à l\'article (victoires v3 : Q-Learning 86,5 % · SARSA 84,4 % · Monte Carlo 94,9 % · DQN 76,4 %) : ', options: { bold: true } },
          { text: 'tendances confirmées, chiffres plus hauts chez nous. Les règles des ennemis ne sont pas précisées : nos agents en écrasent 2 à 4 fois plus.' }],
      0.85, 5.88, 11.7, 0.97, { fontSize: 13.5, valign: 'middle' });
  s.addNotes(NOTES.tableau_final);
}

// =============================================================================
// WORLD 1-3 : LE VRAI JEU NES
// =============================================================================
divider('1-3 Le vrai jeu NES', '1-3', 'LE VRAI JEU NES', 'PPO sur la vraie physique, puis la Route A', (s) => {
  ['coin_pipe', 'pipe_short', 'goomba', 'mario', 'tree'].forEach((n) => sprite(s, n));
}, NOTES.d3);

{
  const s = content('1-3 Le vrai jeu NES', 'WORLD 1-3 - LE VRAI JEU NES', 'PASSER AU VRAI JEU',
    "Sur la vraie physique NES, une Q-table plafonne vers 35 % : il faut une IA qui généralise.");
  card(s, 0.6, 1.9, 6.75, 4.98);
  tag(s, "GRILLE DE L'ARTICLE OU VRAI JEU ?", 0.6, 1.9, 3.55);
  table(s, { x: 0.8, y: 2.45, colW: [1.55, 2.0, 2.8], headH: 0.42, rowH: 0.62, size: 12.5, headSize: 11.5,
    head: ['', "Grille de l'article", 'Vrai jeu NES'], leftCols: [1, 2],
    rows: [['Mouvement', '1 case par pas', 'élan, accélération, course'],
           ['Saut', 'toujours le même arc', '5 sauts selon la vitesse'],
           ["Ce que voit l'IA", 'sa case + 4 lignes', '62 nombres : position, vitesses, 5 ennemis, relief'],
           ['Boutons', '3', '5 (dont courir)']] });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.8, y: 5.9, w: 6.35, h: 0.8, fill: { color: 'FFF4C2' }, line: { color: BLACK, width: 1 } });
  txt(s, [{ text: "Q-Learning de l'article sur le vrai jeu : ~35 % ", options: { bold: true } },
          { text: 'de victoires, de façon instable (1 graine, 30 000 parties).' }], 0.95, 5.93, 6.1, 0.74, { fontSize: 13, valign: 'middle' });
  card(s, 7.65, 1.9, 5.08, 4.98);
  tag(s, 'PPO · OPENAI, 2017', 7.65, 1.9, 2.3, ALGO.ppo);
  // petit schéma acteur / critique
  s.addText('62 nombres\n(ce que voit Mario)', { x: 7.9, y: 2.55, w: 1.6, h: 1.15, fontFace: FB, fontSize: 11.5, bold: true,
    color: WHITE, fill: { color: NAVY }, align: 'center', valign: 'middle', margin: 2, isTextBox: true });
  [['ACTEUR', 'quel bouton ? (probabilités)', 2.42], ['CRITIQUE', 'la situation est-elle bonne ?', 3.22]].forEach(([n, d, cy]) => {
    const yc = cy + 0.31, up = yc < 3.125;
    s.addShape(pres.shapes.LINE, { x: 9.52, y: up ? yc : 3.125, w: 0.55, h: Math.abs(yc - 3.125), flipV: up,
                                   line: { color: NAVY, width: 1.5, endArrowType: 'triangle' } });
    s.addText([{ text: n, options: { bold: true, breakLine: true, fontSize: 12 } }, { text: d, options: { fontSize: 11 } }],
      { x: 10.1, y: cy, w: 2.45, h: 0.62, fontFace: FB, color: NAVY, fill: { color: LIGHT.ppo }, valign: 'middle',
        margin: mg(2, 4, 2, 8), isTextBox: true, line: { color: ALGO.ppo, width: 1 } });
  });
  bullets(s, [['Il apprend la façon de jouer ', 'directement, sans tableau de notes'],
              ['Par petits pas ', '(« proximal ») : chaque mise à jour reste proche de la précédente'],
              ['2 petits réseaux, ', '~17 000 poids (notre DQN : 319 000)'],
              ['Réglages optimisés avec Claude ', '(assistant IA)']], 7.9, 4.12, 4.65, 2.65, { fontSize: 13, space: 7 });
  s.addNotes(NOTES.vrai_jeu);
}

{
  const s = content('1-3 Le vrai jeu NES', 'WORLD 1-3 - LE VRAI JEU NES', 'PPO SUR LE VRAI NIVEAU',
    'PPO gagne 81 % des parties et réussit la partie sans hasard avec les 5 graines.');
  const vw = 4.55, vh = vw * 720 / 768;
  video(s, '03_ppo_nes_v3.mp4', 0.6, 1.92, vw, vh);
  txt(s, 'Vidéo : graine 42, sans hasard, vitesse réelle : drapeau en 336 pas', 0.6, 1.92 + vh + 0.08, vw, 0.5, { fontSize: 12, bold: true });
  const kp = [['81,4 %', 'victoires (± 5,6), 500 dernières parties'], ['5 / 5', 'parties sans hasard gagnées'],
              ['59,6 %', 'robustesse (46 à 82 % selon la graine)'], ['10,7 min', 'par graine : 3 M de pas, ~9 500 parties']];
  kp.forEach(([v, l], i) => kpi(s, 5.5 + (i % 2) * 3.67, 1.92 + Math.floor(i / 2) * 1.32, 3.56, 1.18, v, l, { size: 25 }));
  card(s, 5.5, 4.65, 7.23, 2.23);
  tag(s, 'PROGRESSION · moyenne des 5 graines', 5.5, 4.65, 3.9);
  const prog = [['0,5 M', 36], ['1 M', 69], ['1,5 M', 77], ['2 M', 80], ['2,5 M', 81], ['3 M', 79]];
  const bx = 5.8, by = 5.12, bh = 1.25, bwid = 0.62, step = 1.12;
  prog.forEach(([lab, v], i) => {
    const x = bx + i * step, h = bh * v / 100;
    s.addShape(pres.shapes.RECTANGLE, { x, y: by + bh - h, w: bwid, h, fill: { color: ALGO.ppo }, line: { color: BLACK, width: 1 } });
    txt(s, v + ' %', x - 0.2, by + bh - h - 0.28, bwid + 0.4, 0.26, { fontSize: 11.5, bold: true, align: 'center' });
    txt(s, lab, x - 0.2, by + bh + 0.04, bwid + 0.4, 0.26, { fontSize: 11, align: 'center', color: GREY });
  });
  s.addNotes(NOTES.ppo);
}

{
  const s = content('1-3 Le vrai jeu NES', 'WORLD 1-3 - LE VRAI JEU NES', 'ROUTE A : JOUER COMME UN HUMAIN',
    'Champignon, fleur, tuyau secret et salle bonus : PPO réussit tout, et gagne 91 % des parties.');
  const vw = 4.55, vh = vw * 720 / 768;
  video(s, '04_ppo_route_a.mp4', 0.6, 1.92, vw, vh);
  txt(s, 'Vidéo : graine 43, sans hasard : champignon, fleur, salle bonus, 21 pièces, drapeau', 0.6, 1.92 + vh + 0.08, vw, 0.5,
      { fontSize: 12, bold: true });
  const kp = [['91 %', 'victoires'], ['94 %', 'salle bonus'], ['97 %', 'champignon'], ['93 %', 'fleur'], ['80 %', 'robustesse']];
  kp.forEach(([v, l], i) => kpi(s, 5.5 + i * 1.46, 1.92, 1.35, 1.08, v, l, { size: 21, labelSize: 11 }));
  card(s, 5.5, 3.25, 7.23, 3.63);
  tag(s, "L'IA FAIT CE QU'ON RÉCOMPENSE, PAS CE QU'ON VEUT", 5.5, 3.25, 7.23, RED);
  const fixes = [['Restait dans la salle bonus jusqu\'à la fin du temps', 'pénalité de temps'],
                 ['866 appuis sur « bas » devant la sortie', 'entrée et sortie séparées dans sa vue'],
                 ['Collée à un tuyau en tenant droite + saut', 'règle du blocage : 150 pas sans rien de neuf = perdu'],
                 ['Fleur jamais trouvée', 'bouton gauche ajouté']];
  txt(s, 'Ce qu\'elle faisait', 5.72, 3.72, 3.35, 0.3, { fontSize: 11.5, bold: true, color: GREY });
  txt(s, 'Ce qu\'on a corrigé', 9.25, 3.72, 3.3, 0.3, { fontSize: 11.5, bold: true, color: GREY });
  fixes.forEach(([a, b], i) => {
    const cy = 4.05 + i * 0.6;
    s.addShape(pres.shapes.RECTANGLE, { x: 5.7, y: cy, w: 6.83, h: 0.54, fill: { color: i % 2 ? ZEBRA : WHITE }, line: NOLINE });
    txt(s, a, 5.8, cy, 3.3, 0.54, { fontSize: 12.5, valign: 'middle' });
    txt(s, b, 9.25, cy, 3.25, 0.54, { fontSize: 12.5, bold: true, valign: 'middle', color: GREEN });
  });
  txt(s, 'Une dizaine de variantes · 2 blocs ajoutés au début du niveau · 5 graines × 3 M de pas',
      5.7, 6.45, 6.85, 0.36, { fontSize: 11.5, color: GREY, valign: 'middle' });
  s.addNotes(NOTES.route_a);
}

// =============================================================================
// WORLD 1-4 : LE RECUL
// =============================================================================
divider('1-4 Le recul', '1-4', 'LE RECUL', 'Énergie, auto-critique et ce qu\'on retient', (s) => {
  ['star_brick', 'coin_pipe2', 'pipe_tall'].forEach((n) => sprite(s, n));
}, NOTES.d4);

{
  const s = content('1-4 Le recul', 'WORLD 1-4 - LE RECUL', "L'ÉNERGIE CONSOMMÉE",
    "Tous nos entraînements finaux : 113 Wh, l'énergie pour faire bouillir 1 litre d'eau.");
  const end = table(s, { x: 0.6, y: 1.92, colW: [2.35, 1.35, 1.45, 1.3, 1.15], headH: 0.62, rowH: 0.5,
    head: ['Modèle (par graine)', 'Durée', 'Énergie', 'CO2', 'vs\nQ-Learning'],
    rows: COST.map((r) => [r[0], ...r.slice(2)]), keys: COST.map((r) => r[1]), best: [[1, 1], [1, 2]], size: 13 });
  txt(s, 'CodeCarbon sur MacBook Air M4 (estimation d\'après la charge du processeur), électricité française ~56 g de CO2 par kWh.',
      0.6, end + 0.1, 7.6, 0.55, { fontSize: 11, color: NAVY });
  card(s, 8.55, 1.92, 4.18, 1.62, YEL);
  txt(s, '113 Wh', 8.75, 2.0, 3.8, 0.7, { fontSize: 32, bold: true, valign: 'middle' });
  txt(s, "pour tous nos entraînements finaux : ~1 L d'eau bouillie, ~7 charges de smartphone, 6 g de CO2",
      8.75, 2.68, 3.8, 0.8, { fontSize: 12.5, valign: 'top' });
  card(s, 8.55, 3.72, 4.18, 1.5);
  txt(s, '75 %', 8.75, 3.8, 3.8, 0.62, { fontSize: 28, bold: true, color: RED, valign: 'middle' });
  txt(s, 'du total pour le seul réseau convolutif (carte graphique)… pour un moins bon résultat', 8.75, 4.4, 3.8, 0.78, { fontSize: 12.5 });
  card(s, 8.55, 5.4, 4.18, 1.48);
  txt(s, '×88', 8.75, 5.48, 3.8, 0.62, { fontSize: 28, bold: true, color: ALGO.ours, valign: 'middle' });
  txt(s, "pour notre DQN face à Q-Learning, pour 5 points de robustesse en plus", 8.75, 6.08, 3.8, 0.75, { fontSize: 12.5 });
  s.addNotes(NOTES.energie);
}

{
  const s = content('1-4 Le recul', 'WORLD 1-4 - LE RECUL', 'NOTRE AUTO-CRITIQUE',
    'Ce que nos résultats ne disent pas, et ce que nous ferions avec plus de temps.');
  card(s, 0.6, 1.9, 6.75, 4.98);
  tag(s, 'NOS LIMITES', 0.6, 1.9, 1.75, RED);
  bullets(s, [['6000 épisodes ', 'au lieu de 10 000, pour tout faire tourner sur un portable'],
              ["L'expérience sur l'ordre du niveau ", "n'a pas été refaite"],
              ['Règles des ennemis devinées : ', 'nos Goombas sont plus faciles, nos scores plus hauts'],
              ['Notre DQN réglé sur les graines 42 et 43, ', 'puis évalué avec elles ; garder sa meilleure version l\'avantage au test de robustesse'],
              ['Énergie estimée, ', 'pas mesurée par un capteur, et pour toute la machine'],
              ['Route A façonnée à la main : ', "l'IA apprend ce qu'on a prévu pour elle"]],
          0.82, 2.45, 6.35, 4.35, { fontSize: 13.5, space: 8 });
  card(s, 7.65, 1.9, 5.08, 2.4, YEL);
  tag(s, "L'IA COMME OUTIL", 7.65, 1.9, 2.05);
  txt(s, [{ text: 'DQN et PPO optimisés avec Claude (assistant IA). ', options: { bold: true } },
          { text: 'Gain de temps énorme, mais chaque choix doit être compris et vérifié : étude étape par étape, test de robustesse, rejeu des modèles.' }],
      7.85, 2.38, 4.7, 1.85, { fontSize: 13.5, valign: 'middle' });
  card(s, 7.65, 4.48, 5.08, 2.4);
  tag(s, 'AVEC PLUS DE TEMPS', 7.65, 4.48, 2.3, GREEN);
  bullets(s, ["Refaire l'expérience de l'ordre avec Q-Learning et SARSA (question ouverte de l'article)",
              '10 000 épisodes et plus de graines',
              "Tester la vraie question avec des joueurs humains"], 7.85, 5.0, 4.7, 1.82, { fontSize: 13, space: 6 });
  s.addNotes(NOTES.autocritique);
}

{
  const s = content('1-4 Le recul', 'WORLD 1-4 - LE RECUL', "CE QU'ON RETIENT", null);
  const take = [['1', 'Niveau discret : les tableaux suffisent', '95 % de victoires en 16 secondes, avec des résultats reproductibles au bit près.'],
                ['2', "Ce que voit l'IA compte plus que la taille du réseau", 'Notre DQN passe de 40 % à 94 % grâce à la vue complète ; le réseau convolutif, bien plus coûteux, n\'apporte rien.'],
                ['3', 'Sur le vrai jeu, le deep RL prend le relais', 'PPO : 81 % sur le niveau, 91 % sur la Route A. Et c\'est la récompense qui décide du comportement.']];
  take.forEach(([n, t, d], i) => {
    const cx = 0.6 + i * 4.14;
    card(s, cx, 1.5, 3.85, 3.95);
    s.addText(n, { x: cx + 0.25, y: 1.75, w: 0.75, h: 0.75, fontFace: FT, fontSize: 28, color: NAVY, fill: { color: YEL },
                   align: 'center', valign: 'middle', margin: 0, isTextBox: true, line: { color: BLACK, width: 1.25 } });
    txt(s, t, cx + 0.25, 2.7, 3.35, 0.95, { fontSize: 17, bold: true, valign: 'top' });
    txt(s, d, cx + 0.25, 3.7, 3.35, 1.6, { fontSize: 14, valign: 'top' });
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 5.75, w: 12.13, h: 1.12, fill: { color: NAVY }, line: { color: BLACK, width: 1.5 }, shadow: sh(3.5) });
  txt(s, [{ text: "Et l'article ? ", options: { bold: true, color: YEL } },
          { text: 'Ses grandes tendances tiennent (Monte Carlo au moins aussi bon, son DQN sous les tableaux), mais ses chiffres et sa conclusion sur DQN dépendent de détails qu\'il ne publie pas.', options: { color: WHITE } }],
      0.85, 5.8, 11.7, 1.02, { fontSize: 15, valign: 'middle' });
  s.addNotes(NOTES.conclusion);
}

// Merci / Questions ------------------------------------------------------------------
{
  pres.addSection({ title: 'Fin' });
  const s = newSlide('Fin');
  ['castle', 'flag_mario'].forEach((n) => sprite(s, n));
  bricks(s);
  bigTitle(s, 'MERCI POUR\nVOTRE ÉCOUTE', 0.8, 2.35, 6.9, 1.6, 43.7);
  s.addNotes(NOTES.merci);
}
{
  const s = newSlide('Fin');
  ['duo', 'bowser'].forEach((n) => sprite(s, n));
  bricks(s);
  bigTitle(s, 'AVEZ-VOUS DES\nQUESTIONS ?', 2.6, 1.3, W - 5.2, 1.6, 43.7);
  s.addNotes(NOTES.questions);
}

// =============================================================================
// ANNEXES (pour répondre aux questions du jury)
// =============================================================================
pres.addSection({ title: 'Annexes' });
{
  const s = content('Annexes', 'ANNEXE A', 'COMPORTEMENT EN JEU', 'Par partie, 500 dernières parties (v3, 6000 épisodes, 5 graines).');
  table(s, { x: 0.6, y: 1.95, colW: [2.75, 1.9, 1.9, 1.9, 1.88, 1.8], headH: 0.62, rowH: 0.58, size: 13.5,
    head: ['Algorithme', 'Ennemis\nécrasés', 'Briques\ncassées', 'Blocs ?\nfrappés', 'Pas par\npartie', '1re victoire\n(épisode)'],
    rows: [['Q-Learning', '6,1', '2,9', '4,3', '268', '1322 ± 356'], ['SARSA', '6,9', '3,6', '4,7', '266', '1178 ± 293'],
           ['Monte Carlo', '12,1', '4,9', '5,3', '503', '1108 ± 443'], ["DQN de l'article", '6,0', '2,2', '5,1', '205', '628 ± 194'],
           ['Notre DQN', '12,6', '5,0', '7,1', '246', '632 ± 117']],
    keys: ['ql', 'sarsa', 'mc', 'dqn', 'ours'], best: [[4, 0], [4, 1], [4, 2]] });
  card(s, 0.6, 5.65, 12.13, 1.2, 'FFF4C2');
  txt(s, "Article : 3,3 à 3,8 ennemis par partie pour les tableaux, 1,4 pour DQN. Nos agents en écrasent 2 à 4 fois plus : l'article ne précise pas les règles des ennemis (activation, rebond, chute), nos choix les rendent sans doute plus faciles à écraser.",
      0.85, 5.7, 11.7, 1.1, { fontSize: 13.5, valign: 'middle' });
  s.addNotes("Annexe : à montrer si le jury demande pourquoi nos retours sont plus élevés que ceux de l'article.");
}
{
  const s = content('Annexes', 'ANNEXE B', 'LES RÉGLAGES', "Ceux de l'article, et ce que nous avons changé.");
  table(s, { x: 0.6, y: 1.95, colW: [3.0, 4.4, 4.73], headH: 0.5, rowH: 0.5, size: 13,
    head: ['Réglage', "Article (et nos tableaux)", 'Notre DQN (étape 4)'], leftCols: [1, 2],
    rows: [['Épisodes', '10 000 (nous : 6000 pour tous)', '6000'], ['Graines', '5 (42 à 46)', '5 (42 à 46)'],
           ['Exploration ε', '1 → ×0,999 par épisode → 0,01 (DQN : 0,05)', '→ plancher 0,02'],
           ['γ (actualisation)', '0,99', '0,99'], ['α (tableaux)', '0,1', '-'],
           ["Ce que voit l'IA", '115 nombres (case + 4 lignes)', 'vue complète 14 × 28 en 6 calques'],
           ['Réseau DQN', '115 → 128 → 128 → 3', '~2 400 → 128 → 128 → 3 (319 363 poids)'],
           ['Mémoire de rejeu', '50 000 coups, paquets de 64', '100 000 coups, paquets de 64'],
           ['Apprentissage', 'lr 0,0001, cible copiée tous les 500 pas', 'idem, corrections limitées, meilleure version']] });
  s.addNotes("Annexe : réglages de l'article et de notre DQN.");
}
{
  const s = content('Annexes', 'ANNEXE C', "CE QUE VOIT LE DQN DE L'ARTICLE", 'Seules 4 lignes de 28 cases autour de Mario, plus sa position : ni trous ni sens des ennemis.');
  const ih = 5.0, iw = ih * 1650 / 1100;
  card(s, (W - iw) / 2 - 0.1, 1.87, iw + 0.2, ih + 0.16, WHITE);
  s.addImage({ path: asset('observation_v3.png'), x: (W - iw) / 2, y: 1.95, w: iw, h: ih, objectName: 'observation_v3' });
  s.addNotes("Annexe : pourquoi le DQN de l'article apprend le niveau par cœur.");
}
{
  const s = content('Annexes', 'ANNEXE D', 'NOTRE DQN, ÉTAPE PAR ÉTAPE', 'Graines 42 et 43, 6000 épisodes (étude d\'ablation).');
  table(s, { x: 0.6, y: 1.95, colW: [0.8, 5.2, 1.6, 1.75, 1.35, 1.43], headH: 0.62, rowH: 0.6, size: 13,
    head: ['Étape', 'Changement', 'Victoires', 'Robustesse\n(42 / 43)', 'Parties\npour 50 %', 'Parties\npour 80 %'],
    rows: [['0', "DQN de l'article (sa vue)", '44,2 ± 6,8 %', '62 / 74 %', '5047', 'jamais'],
           ['1', '+ vue complète (14 × 28 cases, 6 calques)', '81,8 ± 0,0 %', '96 / 78 %', '1999', '2900'],
           ['2', '1 + Double DQN, 3 pas, cible douce, corrections limitées, meilleure version', '78,2 ± 9,6 %', '80 / 90 %', '2730', '4330'],
           ['3', '1 + réseau convolutif (CNN), carte graphique', '76,6 ± 8,5 %', '- (poids perdus)', '2210', '3351'],
           ['4', '1 + ε plancher 0,02, mémoire 100 000, corrections limitées, meilleure version', '94,5 ± 1,8 %', '94 / 94 %', '1959', '3022']],
    best: [[4, 1], [4, 2], [4, 3]], firstBold: true, leftCols: [1] });
  card(s, 0.6, 5.85, 12.13, 1.0, 'FFF4C2');
  txt(s, "Ce qui compte : la vue complète (+38 points). Les améliorations connues de DQN et le CNN n'apportent rien ici ; l'étape 4 apporte la stabilité. Sur les 5 graines : 93,7 % de victoires, 94,4 % de robustesse.",
      0.85, 5.9, 11.7, 0.9, { fontSize: 13.5, valign: 'middle' });
  s.addNotes('Annexe : détail de l\'étude étape par étape de notre DQN.');
}
{
  const s = content('Annexes', 'ANNEXE E', 'PPO PAR GRAINE', 'Vrai jeu NES, 3 M de pas par graine.');
  table(s, { x: 0.6, y: 1.95, colW: [1.2, 1.55, 1.55, 1.6], headH: 0.6, rowH: 0.5, size: 13,
    head: ['Graine', 'Victoires', 'Robustesse', 'Sans hasard'],
    rows: [['42', '87,6 %', '54 %', '336 pas'], ['43', '74,8 %', '64 %', '326 pas'], ['44', '77,0 %', '52 %', '347 pas'],
           ['45', '86,4 %', '46 %', '361 pas'], ['46', '81,2 %', '82 %', '375 pas'], ['Moy.', '81,4 %', '59,6 %', '5 / 5']] });
  txt(s, 'PPO sur le niveau v3 du vrai jeu', 0.6, 5.65, 5.9, 0.3, { fontSize: 13, bold: true });
  table(s, { x: 6.85, y: 1.95, colW: [0.85, 1.1, 1.1, 1.1, 0.95, 0.78], headH: 0.6, rowH: 0.5, size: 12.5, headSize: 11,
    head: ['Graine', 'Victoires', 'Salle bonus', 'Champi-\ngnon', 'Fleur', 'Robus-\ntesse'],
    rows: [['42', '87,4 %', '90,4 %', '97,6 %', '91,4 %', '66 %'], ['43', '89,8 %', '92,0 %', '95,6 %', '93,6 %', '78 %'],
           ['44', '95,8 %', '96,2 %', '98,2 %', '97,8 %', '78 %'], ['45', '93,6 %', '95,6 %', '99,2 %', '96,6 %', '92 %'],
           ['46', '89,4 %', '95,0 %', '95,8 %', '85,8 %', '88 %'], ['Moy.', '91,2 %', '93,8 %', '97,3 %', '93,0 %', '80,4 %']] });
  txt(s, 'PPO Route A (tuyau, champignon, fleur) : 5 / 5 sans hasard', 6.85, 5.65, 5.9, 0.3, { fontSize: 13, bold: true });
  s.addNotes('Annexe : détail de PPO par graine.');
}
{
  const s = content('Annexes', 'ANNEXE F', 'ROUTE A : LES RÉGLAGES', 'Niveau, boutons et récompense de la version finale.');
  card(s, 0.6, 1.95, 5.9, 4.9);
  tag(s, 'CONFIGURATION FINALE', 0.6, 1.95, 2.6);
  bullets(s, [['Niveau : ', 'complet, avec salle bonus ; bloc champignon (col. 34) et bloc fleur pour Mario grand (col. 36) ajoutés'],
              ['Vue : ', '91 nombres (objets, pièces, tuyaux, boutons du pas précédent)'],
              ['8 boutons : ', 'rien, droite, droite + saut, droite + course, droite + saut + course, bas, gauche, gauche + saut'],
              ['Règle du blocage : ', '150 pas sans rien de neuf = partie perdue']], 0.82, 2.5, 5.5, 4.2, { fontSize: 13, space: 9 });
  table(s, { x: 6.85, y: 1.95, colW: [3.85, 2.03], headH: 0.5, rowH: 0.46, size: 13,
    head: ['Événement', 'Récompense'], leftCols: [],
    rows: [['Pièce', '+10'], ['Entrer dans la salle bonus', '+200'], ['Champignon ou fleur', '+150'], ['Bloc power-up frappé', '+25'],
           ["Se rapprocher d'un objet visible", '+2 par case'], ['Chaque seconde du chrono', '-0,5'], ['Mort ou blocage', '-50'], ['Drapeau', '+100']] });
  s.addNotes('Annexe : réglages de la Route A.');
}
{
  const s = content('Annexes', 'ANNEXE G', 'RÉFÉRENCES', null);
  const refs = [
    'J. Ponnock, L. Ho. Reinforcement Learning in Super Mario Bros: Curriculum, Pedagogy, and Optimal Level Design in World 1-1. arXiv:2606.29511, 2026.',
    'R. S. Sutton, A. G. Barto. Reinforcement Learning: An Introduction, 2e éd. MIT Press, 2018.',
    'C. J. C. H. Watkins, P. Dayan. Q-learning. Machine Learning 8(3-4), 1992.',
    'G. A. Rummery, M. Niranjan. On-line Q-learning using connectionist systems. Cambridge, 1994.',
    'Y. Bengio, J. Louradour, R. Collobert, J. Weston. Curriculum learning. ICML, 2009.',
    'V. Mnih et al. Human-level control through deep reinforcement learning. Nature 518, 2015.',
    'H. van Hasselt, A. Guez, D. Silver. Deep reinforcement learning with double Q-learning. AAAI, 2016.',
    'J. Schulman et al. Proximal Policy Optimization Algorithms. arXiv:1707.06347, 2017.',
    'D. Pathak et al. Curiosity-driven exploration by self-supervised prediction. ICML, 2017 (agent testé sur Super Mario Bros).',
    'C. Kautenja. gym-super-mario-bros. GitHub, 2018.',
    'S. Dahlskog, J. Togelius. Patterns and procedural content generation: revisiting Mario in World 1 Level 1. DPG, 2012.',
    'E. Strubell, A. Ganesh, A. McCallum. Energy and policy considerations for deep learning in NLP. ACL, 2019.',
    'CodeCarbon : outil de mesure de l\'empreinte carbone du calcul (codecarbon.io).'];
  card(s, 0.6, 1.5, 12.13, 5.38);
  bullets(s, refs, 0.85, 1.7, 11.7, 5.1, { fontSize: 13.5, space: 5 });
  s.addNotes('Annexe : références citées.');
}

pres.writeFile({ fileName: OUT }).then((f) => console.log('écrit :', f, '-', slideNo, 'diapos'));
