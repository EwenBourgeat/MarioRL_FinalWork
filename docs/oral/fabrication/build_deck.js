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

var newSlide = function newSlide(section) {
  const s = pres.addSlide({ sectionTitle: section });
  s.background = { color: SKY };
  slideNo += 1;
  return s;
};

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

// --- version épurée : cartes blanches sans contour, ombre douce, titres en
// Montserrat ; la police pixel ne sert plus qu'aux petits repères « WORLD »
const soft = () => ({ type: 'outer', blur: 8, offset: 2, angle: 90, color: '0B1F44', opacity: 0.22 });

function greenGround(s) {          // diapos de contenu : fine bande de sol vert
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 7.34, w: W, h: 0.16, fill: { color: G_DARK }, line: NOLINE, objectName: 'sol' });
}

function pageNo(s) {
  s.addText(String(slideNo), { x: W - 1.0, y: 6.95, w: 0.62, h: 0.3, fontFace: FB, fontSize: 11, bold: true,
                               color: WHITE, align: 'right', valign: 'middle', margin: 0, isTextBox: true });
}

function header(s, world, title) {
  s.addText(world, { x: 0.6, y: 0.38, w: 9, h: 0.3, fontFace: FT, fontSize: 11, color: YEL, margin: 0,
                     valign: 'middle', isTextBox: true, objectName: 'monde' });
  s.addText(fr(title), { x: 0.6, y: 0.72, w: 12.13, h: 0.7, fontFace: FB, fontSize: 30, bold: true, color: WHITE,
                         margin: 0, valign: 'middle', isTextBox: true, objectName: 'titre' });
}

function content(section, world, title) {
  const s = newSlide(section);
  greenGround(s);
  header(s, world, title);
  pageNo(s);
  return s;
}

function card(s, x, y, w, h, fill = WHITE, name = 'carte') {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: NOLINE,
                                              shadow: soft(), objectName: name });
}

// petit titre en capitales en haut d'une carte
function tag(s, text, x, y, w, color = GREY, _c, size = 11.5) {
  s.addText(fr(text), { x: x + 0.3, y: y + 0.22, w: Math.max(w, 3) , h: 0.3, fontFace: FB, fontSize: size, bold: true,
                        color, margin: 0, valign: 'middle', isTextBox: true, charSpacing: 1, objectName: 'etiquette' });
}

function txt(s, text, x, y, w, h, o = {}) {
  s.addText(fr(text), Object.assign({ x, y, w, h, fontFace: FB, fontSize: 16, color: NAVY, margin: 0,
                                      valign: 'top', isTextBox: true }, o));
}

// liste à puces : items = chaînes ou [gras, suite]
function bullets(s, items, x, y, w, h, o = {}) {
  const size = o.fontSize || 16;
  const runs = [];
  items.forEach((it, i) => {
    const last = i === items.length - 1;
    const base = { bullet: { indent: 16 }, paraSpaceAfter: o.space || 12, breakLine: false };
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

// tableau en formes (Canva n'importe pas les tableaux PowerPoint)
function table(s, { x, y, colW, headH, rowH, head, rows, best = [], size = 14, headSize = 12, firstBold = true, leftCols = [] }) {
  const totW = colW.reduce((a, b) => a + b, 0);
  const totH = headH + rowH * rows.length;
  s.addShape(pres.shapes.RECTANGLE, { x, y, w: totW, h: totH, fill: { color: WHITE }, line: NOLINE, shadow: soft(),
                                      objectName: 'tableau_fond' });
  let cx = x;
  head.forEach((hd, j) => {
    const left = j === 0 || leftCols.includes(j);
    s.addText(fr(hd), { x: cx, y, w: colW[j], h: headH, fontFace: FB, fontSize: headSize, bold: true, color: WHITE,
                        fill: { color: NAVY }, align: left ? 'left' : 'center', valign: 'middle',
                        margin: mg(2, 6, 2, left ? 14 : 6), isTextBox: true, objectName: 'entete' });
    cx += colW[j];
  });
  rows.forEach((row, i) => {
    let cxx = x;
    const ry = y + headH + i * rowH;
    row.forEach((cell, j) => {
      const isBest = best.some(([bi, bj]) => bi === i && bj === j - 1);
      const fill = isBest ? 'FFF0B3' : (i % 2 ? 'F2F5FA' : WHITE);
      const left = j === 0 || leftCols.includes(j);
      s.addText(fr(cell), { x: cxx, y: ry, w: colW[j], h: rowH, fontFace: FB, fontSize: size,
                            bold: j === 0 ? firstBold : isBest, color: NAVY, fill: { color: fill },
                            align: left ? 'left' : 'center', valign: 'middle',
                            margin: left ? mg(2, 6, 2, 14) : 2, isTextBox: true, objectName: 'cellule' });
      cxx += colW[j];
    });
  });
  return y + totH;
}

// barres horizontales : items = {label, value (0-100), text, color}
function hbars(s, { x, y, labelW, barW, rowH, items, size = 15, max = 100 }) {
  items.forEach((it, i) => {
    const ry = y + i * rowH;
    const bh = rowH * 0.5;
    txt(s, it.label, x, ry, labelW - 0.15, rowH, { fontSize: size, bold: true, valign: 'middle' });
    const bw = Math.max(0.05, barW * it.value / max);
    s.addShape(pres.shapes.RECTANGLE, { x: x + labelW, y: ry + (rowH - bh) / 2, w: bw, h: bh,
                                        fill: { color: it.color }, line: NOLINE });
    txt(s, it.text, x + labelW + bw + 0.12, ry, 1.3, rowH, { fontSize: size, bold: true, valign: 'middle' });
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
}

// grand chiffre + légende, sur une carte blanche
function kpi(s, x, y, w, h, value, label, o = {}) {
  card(s, x, y, w, h, WHITE, 'kpi');
  txt(s, value, x + 0.25, y + 0.12, w - 0.4, h * 0.52, { fontSize: o.size || 30, bold: true, color: o.color || NAVY, valign: 'middle' });
  txt(s, label, x + 0.25, y + h * 0.6, w - 0.4, h * 0.34, { fontSize: o.labelSize || 13, color: GREY, valign: 'top' });
}

// phrase-clé en bas de diapo (blanc, sur le fond bleu)
function punch(s, text, y = 6.45) {
  txt(s, text, 0.6, y, 12.13, 0.5, { fontSize: 18, bold: true, color: WHITE, valign: 'middle' });
}

// grand titre des diapos « Mario » (blanc, ombre violette)
function bigTitle(s, text, x, y, w, h, size, color = WHITE, align = 'center') {
  s.addText(fr(text), { x, y, w, h, fontFace: FT, fontSize: size, color, align, valign: 'middle', margin: 0,
                    isTextBox: true, shadow: sh(Math.max(2, size * 0.05)), lineSpacingMultiple: 1.0, objectName: 'grand_titre' });
}

// =============================================================================
// DIAPO BONUS : PPO expliqué (fichier à part : Slide_PPO.pptx)
//   PPO_ONLY=1 DECK_OUT=docs/oral/Slide_PPO.pptx node build_deck.js
// =============================================================================
function ppoSlide() {
  const s = content('1-3 Le vrai jeu NES', 'WORLD 1-3  -  LE VRAI JEU NES', 'PPO : un acteur et un critique');
  // entrée
  card(s, 0.6, 1.8, 3.0, 2.95);
  tag(s, 'CE QUE VOIT MARIO', 0.6, 1.8, 2.6);
  txt(s, '62 nombres', 0.9, 2.45, 2.5, 0.7, { fontSize: 28, bold: true, color: ALGO.ppo, valign: 'middle' });
  txt(s, 'sa position, ses vitesses, les ennemis proches, le relief devant lui', 0.9, 3.2, 2.5, 1.4, { fontSize: 15 });
  // acteur
  card(s, 4.3, 1.8, 8.43, 1.4);
  tag(s, "L'ACTEUR · IL JOUE", 4.3, 1.8, 3.2, ALGO.ppo);
  txt(s, 'Choisit le bouton, en tirant au sort selon des probabilités', 4.6, 2.35, 4.0, 0.75, { fontSize: 16, bold: true, valign: 'middle' });
  hbars(s, { x: 8.9, y: 1.95, labelW: 1.05, barW: 2.0, rowH: 0.36, size: 13, items: [
    { label: 'Droite', value: 60, text: '60 %', color: ALGO.ppo },
    { label: 'Saut', value: 35, text: '35 %', color: 'E7A6CC' },
    { label: 'Rien', value: 5, text: '5 %', color: 'E7A6CC' }] });
  // critique
  card(s, 4.3, 3.35, 8.43, 1.4);
  tag(s, 'LE CRITIQUE · IL JUGE', 4.3, 3.35, 3.2, ALGO.ql);
  txt(s, "Juge la situation : combien de points j'espère à partir d'ici ?", 4.6, 3.9, 4.3, 0.75, { fontSize: 16, bold: true, valign: 'middle' });
  txt(s, '≈ 20 points', 8.9, 3.5, 3.6, 0.8, { fontSize: 30, bold: true, color: ALGO.ql, valign: 'middle', align: 'center' });
  txt(s, "(exemple : Mario devant un trou)", 8.9, 4.3, 3.6, 0.35, { fontSize: 12, color: GREY, align: 'center' });
  // flèches
  [[2.5, 3.0, 4.3, 2.5], [3.65, 3.8, 4.3, 4.05]].forEach(() => {});
  s.addShape(pres.shapes.LINE, { x: 3.65, y: 2.5, w: 0.6, h: 0.9, flipV: true, line: { color: WHITE, width: 2, endArrowType: 'triangle' } });
  s.addShape(pres.shapes.LINE, { x: 3.65, y: 3.3, w: 0.6, h: 0.75, line: { color: WHITE, width: 2, endArrowType: 'triangle' } });
  // apprentissage en 3 temps
  card(s, 0.6, 4.95, 12.13, 1.85);
  tag(s, 'COMMENT ILS APPRENNENT', 0.6, 4.95, 4);
  [['1', "L'acteur appuie sur un bouton"], ['2', 'On compare : points réels contre points prévus par le critique'],
   ['3', "Mieux que prévu : on augmente la probabilité de ce bouton"]].forEach(([n, t], i) => {
    const cx = 0.9 + i * 4.0;
    txt(s, n, cx, 5.55, 0.5, 0.9, { fontSize: 34, bold: true, color: ALGO.ppo, valign: 'middle' });
    txt(s, t, cx + 0.55, 5.55, 3.1, 1.0, { fontSize: 15, valign: 'middle' });
  });
  s.addNotes(`[1:00]
À l'écran : ce que voit Mario, l'acteur, le critique, et les 3 étapes.
On dit :
- PPO utilise deux petits réseaux de neurones qui se partagent le travail.
- Les deux reçoivent la même chose : 62 nombres qui décrivent la situation de Mario.
- L'acteur joue : il donne une probabilité pour chaque bouton, et on tire le bouton au sort selon ces probabilités.
- Le critique ne joue jamais : il juge la situation. Il dit combien de points on peut espérer à partir d'ici.
- Pour apprendre, on compare le résultat réel avec ce que le critique prévoyait.
- Si c'est mieux que prévu, l'acteur augmente la probabilité de ce bouton. Si c'est moins bien, il la diminue.
- Exemple : Mario est devant un trou, le critique espère 20 points. L'acteur saute et finit à 60 points. C'était une bonne idée, donc il refera ce saut.
- Le mot « proximal » veut dire que chaque correction est petite, pour ne pas tout casser d'un coup.`);
}

if (process.env.PPO_ONLY) {
  ppoSlide();
  pres.writeFile({ fileName: OUT }).then((f) => console.log('écrit :', f));
  // le reste du script construit le grand diaporama dans une instance jetable
  const sink = new pptxgen();
  sink.layout = 'LAYOUT_WIDE';
  newSlide = () => { slideNo += 1; const x = sink.addSlide(); x.background = { color: SKY }; return x; };
  pres.addSection = () => {};
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
  [4.847, 5.759, 6.676, 7.588].forEach((x) => sprite(s, 'coin', { x, y: 4.824 }));
}, NOTES.d1);

const K1 = 'WORLD 1-1  -  LA VEILLE', K2 = 'WORLD 1-2  -  LE DUEL SUR V3', K3 = 'WORLD 1-3  -  LE VRAI JEU NES', K4 = 'WORLD 1-4  -  LE RECUL';

{
  const s = content('1-1 La veille', K1, 'Le niveau 1-1 est-il une vraie leçon ?');
  card(s, 0.6, 1.8, 6.2, 3.3);
  tag(s, 'PRÉPUBLICATION ARXIV · JUIN 2026', 0.6, 1.8, 5);
  txt(s, 'Reinforcement Learning in Super Mario Bros: Curriculum, Pedagogy, and Optimal Level Design in World 1-1',
      0.9, 2.35, 5.6, 1.6, { fontSize: 19, bold: true, italic: true });
  txt(s, 'J. Ponnock & L. Ho · Johns Hopkins University', 0.9, 4.25, 5.6, 0.5, { fontSize: 15, color: GREY });
  [['QUESTION 1', 'Quel algorithme apprend le mieux le niveau ?'],
   ['QUESTION 2', "L'ordre d'origine du niveau accélère-t-il l'apprentissage ?"]].forEach(([q, t], i) => {
    const y = 1.8 + i * 1.72;
    card(s, 7.1, y, 5.63, 1.58);
    tag(s, q, 7.1, y, 3, ALGO.ql);
    txt(s, t, 7.4, y + 0.55, 5.1, 0.9, { fontSize: 19, bold: true, valign: 'middle' });
  });
  [['4', 'algorithmes'], ['3', 'versions du niveau'], ['120', 'entraînements']].forEach(([n, l], i) => {
    txt(s, [{ text: n + ' ', options: { fontSize: 34, bold: true } }, { text: l, options: { fontSize: 17 } }],
        0.6 + i * 4.1, 5.45, 4.0, 0.8, { color: WHITE, valign: 'middle' });
  });
  s.addNotes(NOTES.article);
}

{
  const s = content('1-1 La veille', K1, "D'où vient l'article");
  const tl = [['1992', 'Q-Learning', 'Watkins & Dayan'], ['2009', 'Curriculum', 'Bengio et al.'],
              ['2015', 'DQN', 'Mnih et al., Nature'], ['2017', 'PPO', 'Schulman et al.'], ['2026', "L'article", 'Ponnock & Ho']];
  s.addShape(pres.shapes.RECTANGLE, { x: 1.4, y: 3.9, w: 10.55, h: 0.05, fill: { color: WHITE }, line: NOLINE });
  tl.forEach(([yr, a, b], i) => {
    const cx = 1.4 + i * (10.55 / 4);
    const last = i === tl.length - 1;
    s.addShape(pres.shapes.OVAL, { x: cx - 0.13, y: 3.79, w: 0.27, h: 0.27, fill: { color: last ? YEL : WHITE }, line: NOLINE });
    txt(s, yr, cx - 1.2, 2.95, 2.4, 0.6, { fontSize: 28, bold: true, color: last ? YEL : WHITE, align: 'center', valign: 'middle' });
    txt(s, a, cx - 1.2, 4.3, 2.4, 0.45, { fontSize: 17, bold: true, color: WHITE, align: 'center' });
    txt(s, b, cx - 1.2, 4.75, 2.4, 0.4, { fontSize: 13, color: NAVY, align: 'center' });
  });
  punch(s, "Première tentative de mesurer la « pédagogie » d'un niveau avec des IA.", 6.0);
  s.addNotes(NOTES.veille);
}

{
  const s = content('1-1 La veille', K1, 'Le terrain et les 4 algorithmes');
  const lw = 12.13, lh = lw * 176 / 3392;
  card(s, 0.6, 1.8, 12.13, lh + 0.9);
  s.addImage({ path: asset('level_v3.png'), x: 0.6, y: 1.8, w: lw, h: lh, objectName: 'niveau_v3' });
  txt(s, 'Grille 212 × 14  ·  3 boutons : rien, droite, saut  ·  +100 au drapeau, -50 à la mort', 0.9, 1.8 + lh + 0.18, 11.6, 0.5,
      { fontSize: 15, bold: true, valign: 'middle' });
  const algos = [['Q-Learning', 'ql', 'Apprend à chaque pas'], ['SARSA', 'sarsa', 'À chaque pas, plus prudent'],
                 ['Monte Carlo', 'mc', 'Apprend en fin de partie'], ['DQN', 'dqn', 'Un réseau de neurones']];
  algos.forEach(([n, k, d], i) => {
    const cx = 0.6 + i * 3.08;
    card(s, cx, 3.75, 2.89, 2.1);
    txt(s, n, cx + 0.3, 3.98, 2.4, 0.55, { fontSize: 21, bold: true, color: ALGO[k], valign: 'middle' });
    txt(s, d, cx + 0.3, 4.6, 2.35, 1.0, { fontSize: 16 });
  });
  punch(s, 'Les 3 premiers remplissent un tableau de notes ; DQN généralise.', 6.15);
  s.addNotes(NOTES.terrain);
}

{
  const s = content('1-1 La veille', K1, "Ce que trouve l'article");
  card(s, 0.6, 1.8, 6.2, 4.4);
  tag(s, 'QUI APPREND LE MIEUX ? (VICTOIRES SUR V3)', 0.6, 1.8, 5.5);
  hbars(s, { x: 0.9, y: 2.45, labelW: 1.9, barW: 2.85, rowH: 0.85, items: [
    { label: 'Monte Carlo', value: 94.9, text: '94,9 %', color: ALGO.mc },
    { label: 'Q-Learning', value: 86.5, text: '86,5 %', color: ALGO.ql },
    { label: 'SARSA', value: 84.4, text: '84,4 %', color: ALGO.sarsa },
    { label: 'DQN', value: 76.4, text: '76,4 %', color: ALGO.dqn }] });
  card(s, 7.1, 1.8, 5.63, 4.4);
  tag(s, "L'ORDRE DU NIVEAU COMPTE-T-IL ?", 7.1, 1.8, 5);
  [["Ordre d'origine", '94,7 %', GREEN], ['Ordres au hasard', '89,0 %', ORANGE], ['Ordre inversé', '48,5 %', RED]].forEach(([a, v, c], i) => {
    const cy = 2.45 + i * 1.12;
    txt(s, a, 7.4, cy, 2.8, 0.9, { fontSize: 17, bold: true, valign: 'middle' });
    txt(s, v, 10.1, cy, 2.4, 0.9, { fontSize: 34, bold: true, color: c, valign: 'middle', align: 'right' });
  });
  punch(s, 'Leur conclusion : le 1-1 a une vraie structure pédagogique.', 6.4);
  s.addNotes(NOTES.findings);
}

{
  const s = content('1-1 La veille', K1, 'Notre lecture critique');
  const cols = [['FORCES', GREEN, ['Question originale', 'Environnement codé de zéro', 'Contrôle avec DQN bien pensé']],
                ['ERREURS', RED, ['Ordre inversé : 94,7 % écrit au lieu de 48,5 %', '« Seul ordre sans échec » : faux', 'Calcul du score maximal faux']],
                ['FAIBLESSES', ORANGE, ['10 ordres testés sur 720', 'Effet géant (d = 7) sur 5 graines', 'Aucun code publié']]];
  cols.forEach(([t, c, items], i) => {
    const cx = 0.6 + i * 4.14;
    card(s, cx, 1.8, 3.85, 4.1);
    tag(s, t, cx, 1.8, 3, c, null, 13);
    bullets(s, items, cx + 0.3, 2.45, 3.3, 3.3, { fontSize: 17, space: 16 });
  });
  punch(s, "Surtout : une IA qui apprend vite ne prouve pas qu'un humain apprend mieux.", 6.2);
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
  const s = content('1-2 Le duel sur v3', K2, 'Le même protocole pour tous');
  card(s, 0.6, 1.8, 5.0, 5.05);
  s.addImage({ path: asset('ecran_titre.png'), x: 0.9, y: 2.05, w: 4.4, h: 4.125, objectName: 'ecran_titre' });
  txt(s, 'Notre copie du niveau 1-1, physique NES', 0.9, 6.25, 4.4, 0.45, { fontSize: 13, color: GREY, align: 'center' });
  const rows = [['v3', 'le niveau avec ses 17 ennemis'], ['6000', 'épisodes par entraînement'], ['5', 'graines (42 à 46), même machine'],
                ['50', 'parties de test avec 2 % de hasard : la robustesse']];
  rows.forEach(([n, l], i) => {
    const cy = 1.85 + i * 1.22;
    card(s, 5.95, cy, 6.78, 1.06);
    txt(s, n, 6.2, cy, 1.6, 1.06, { fontSize: 32, bold: true, color: ALGO.ql, valign: 'middle' });
    txt(s, l, 7.85, cy, 4.7, 1.06, { fontSize: 17, valign: 'middle' });
  });
  s.addNotes(NOTES.protocole);
}

{
  const s = content('1-2 Le duel sur v3', K2, 'Les méthodes à tableau apprennent vite');
  const vw = 8.7, vh = vw * 666 / 1920;
  video(s, '01_qlearning_progression.mp4', 0.6, 1.8, vw, vh);
  txt(s, 'Q-Learning aux épisodes 100, 1000, 2200 et 6000', 0.6, 1.8 + vh + 0.1, vw, 0.35, { fontSize: 13, bold: true, color: WHITE });
  [['94,5 %', 'Q-Learning', 'ql'], ['96,2 %', 'SARSA', 'sarsa'], ['96,2 %', 'Monte Carlo', 'mc']].forEach(([v, n, k], i) => {
    kpi(s, 9.6, 1.8 + i * 1.08, 3.13, 0.95, v, n + ' · victoires', { size: 26, color: ALGO[k], labelSize: 12 });
  });
  punch(s, 'Monte Carlo attend les Goombas : 2× plus de pas, 2× plus d\'ennemis écrasés.', 6.0);
  s.addNotes(NOTES.tableaux);
}

{
  const s = content('1-2 Le duel sur v3', K2, 'DQN : de 40 % à 94 % de victoires');
  const vw = 12.13, vh = vw * 338 / 1920;
  video(s, '02_dqn_article_vs_notre.mp4', 0.6, 1.8, vw, vh);
  card(s, 0.6, 4.25, 7.6, 2.65);
  hbars(s, { x: 0.9, y: 4.4, labelW: 3.0, barW: 3.0, rowH: 0.47, size: 14, items: [
    { label: "DQN de l'article", value: 44.2, text: '44 %', color: ALGO.dqn },
    { label: '+ vue complète', value: 81.8, text: '82 %', color: ALGO.ours },
    { label: '+ Double DQN, 3 pas…', value: 78.2, text: '78 %', color: 'B9AEDF' },
    { label: '+ réseau convolutif', value: 76.6, text: '77 %', color: 'B9AEDF' },
    { label: '+ réglages fins', value: 94.5, text: '94,5 %', color: ALGO.ours }] });
  txt(s, '+38 points', 8.6, 4.35, 4.13, 0.8, { fontSize: 38, bold: true, color: WHITE });
  txt(s, "grâce à la vue complète : c'est ce que voit l'IA qui compte.", 8.6, 5.15, 4.13, 0.9, { fontSize: 17, bold: true, color: WHITE });
  txt(s, 'Optimisé avec Claude, vérifié étape par étape.', 8.6, 6.2, 4.13, 0.6, { fontSize: 14, color: NAVY });
  s.addNotes(NOTES.dqn);
}

{
  const s = content('1-2 Le duel sur v3', K2, 'Le tableau final');
  const head = ['Algorithme', 'Victoires', 'Robustesse*', 'Retour moyen', 'Parties pour 80 %', 'Morts'];
  const rows = PERF.map((r) => [r[0], r[2], r[3], r[5], r[6], r[7]]);
  const best = [[1, 0], [2, 0], [4, 1], [4, 2], [4, 3], [2, 4]];
  const end = table(s, { x: 0.6, y: 1.8, colW: [2.9, 1.9, 2.0, 1.8, 2.0, 1.53], headH: 0.6, rowH: 0.62, head, rows, best, size: 15 });
  txt(s, '* 50 parties avec 2 % de hasard : le même test pour tous, c\'est la colonne à comparer.', 0.6, end + 0.12, 12.13, 0.4,
      { fontSize: 13, color: WHITE });
  punch(s, "Notre DQN est le plus robuste. Article : MC 94,9 % · QL 86,5 % · SARSA 84,4 % · DQN 76,4 %.", 6.2);
  s.addNotes(NOTES.tableau_final);
}

// =============================================================================
// WORLD 1-3 : LE VRAI JEU NES
// =============================================================================
divider('1-3 Le vrai jeu NES', '1-3', 'LE VRAI JEU NES', 'PPO sur la vraie physique, puis la Route A', (s) => {
  ['coin_pipe', 'pipe_short', 'goomba', 'mario', 'tree'].forEach((n) => sprite(s, n));
}, NOTES.d3);

{
  const s = content('1-3 Le vrai jeu NES', K3, 'Passer au vrai jeu : PPO');
  card(s, 0.6, 1.8, 5.9, 4.1);
  tag(s, 'GRILLE DE L\'ARTICLE  VS  VRAI JEU', 0.6, 1.8, 5);
  [['Mouvement', '1 case par pas', 'élan, course'], ['Saut', 'toujours le même', 'selon la vitesse'], ["Vue de l'IA", 'sa case', '62 nombres']].forEach(([a, b, c], i) => {
    const cy = 2.5 + i * 1.05;
    txt(s, a, 0.9, cy, 1.8, 0.8, { fontSize: 15, bold: true, valign: 'middle' });
    txt(s, b, 2.7, cy, 1.75, 0.8, { fontSize: 15, color: GREY, valign: 'middle' });
    txt(s, c, 4.5, cy, 1.85, 0.8, { fontSize: 15, bold: true, color: ALGO.ppo, valign: 'middle' });
  });
  card(s, 6.83, 1.8, 5.9, 4.1);
  tag(s, 'PPO · OPENAI, 2017', 6.83, 1.8, 4, ALGO.ppo);
  bullets(s, [['Un acteur ', 'choisit le bouton'], ['Un critique ', 'juge la situation'],
              ['Par petits pas, ', '~17 000 poids'], ['Réglé avec Claude', '']], 7.13, 2.5, 5.3, 3.2, { fontSize: 18, space: 14 });
  punch(s, 'Une Q-table plafonne vers 35 % sur le vrai jeu : il faut une IA qui généralise.', 6.2);
  s.addNotes(NOTES.vrai_jeu);
}

{
  const s = content('1-3 Le vrai jeu NES', K3, 'PPO gagne 81 % des parties');
  const vw = 5.0, vh = vw * 720 / 768;
  video(s, '03_ppo_nes_v3.mp4', 0.6, 1.8, vw, vh);
  kpi(s, 6.0, 1.8, 3.25, 1.5, '81,4 %', 'victoires', { size: 34 });
  kpi(s, 9.48, 1.8, 3.25, 1.5, '5 / 5', 'parties sans hasard gagnées', { size: 34 });
  kpi(s, 6.0, 3.5, 3.25, 1.5, '59,6 %', 'robustesse', { size: 34 });
  kpi(s, 9.48, 3.5, 3.25, 1.5, '11 min', 'par graine (3 M de pas)', { size: 34 });
  txt(s, 'Point faible : il rattrape mal un bouton perturbé.', 6.0, 5.35, 6.73, 0.6, { fontSize: 17, bold: true, color: WHITE, valign: 'middle' });
  s.addNotes(NOTES.ppo);
}

{
  const s = content('1-3 Le vrai jeu NES', K3, 'Route A : jouer comme un humain');
  const vw = 5.0, vh = vw * 720 / 768;
  video(s, '04_ppo_route_a.mp4', 0.6, 1.8, vw, vh);
  [['91 %', 'victoires'], ['94 %', 'salle bonus'], ['97 %', 'champignon'], ['93 %', 'fleur']].forEach(([v, l], i) =>
    kpi(s, 6.0 + i * 1.72, 1.8, 1.6, 1.25, v, l, { size: 24, labelSize: 12 }));
  card(s, 6.0, 3.3, 6.73, 2.6);
  tag(s, "L'IA FAIT CE QU'ON RÉCOMPENSE, PAS CE QU'ON VEUT", 6.0, 3.3, 6, RED);
  [['Restait dans la salle bonus', 'pénalité de temps'], ['Collée contre un tuyau', 'règle du blocage'], ['Ne trouvait pas la fleur', 'bouton gauche']].forEach(([a, b], i) => {
    const cy = 3.9 + i * 0.6;
    txt(s, a, 6.3, cy, 3.6, 0.5, { fontSize: 15, valign: 'middle' });
    txt(s, b, 9.9, cy, 2.7, 0.5, { fontSize: 15, bold: true, color: GREEN, valign: 'middle' });
  });
  s.addNotes(NOTES.route_a);
}

// =============================================================================
// WORLD 1-4 : LE RECUL
// =============================================================================
divider('1-4 Le recul', '1-4', 'LE RECUL', 'Énergie, auto-critique et ce qu\'on retient', (s) => {
  ['star_brick', 'coin_pipe2', 'pipe_tall'].forEach((n) => sprite(s, n));
}, NOTES.d4);

{
  const s = content('1-4 Le recul', K4, "L'énergie consommée");
  const rows = COST.map((r) => [r[0], r[2], r[3], r[5]]);
  table(s, { x: 0.6, y: 1.8, colW: [2.7, 1.5, 1.6, 1.5], headH: 0.55, rowH: 0.58,
             head: ['Par graine', 'Durée', 'Énergie', 'vs Q-L'], rows, best: [[1, 1]], size: 15 });
  kpi(s, 8.3, 1.8, 4.43, 1.55, '113 Wh', 'tous nos entraînements ≈ 1 L d\'eau bouillie', { size: 34 });
  kpi(s, 8.3, 3.55, 4.43, 1.55, '75 %', 'pour le seul réseau convolutif, moins bon', { size: 34, color: RED });
  kpi(s, 8.3, 5.3, 4.43, 1.55, '×88', 'notre DQN face à Q-Learning', { size: 34, color: ALGO.ours });
  s.addNotes(NOTES.energie);
}

{
  const s = content('1-4 Le recul', K4, 'Notre auto-critique');
  card(s, 0.6, 1.8, 6.6, 5.05);
  tag(s, 'NOS LIMITES', 0.6, 1.8, 3, RED);
  bullets(s, ['6000 épisodes au lieu de 10 000', "Expérience sur l'ordre du niveau non refaite", 'Règles des ennemis devinées',
              'DQN réglé et évalué sur les mêmes graines', 'Énergie estimée, sans capteur'], 0.9, 2.45, 6.1, 4.2, { fontSize: 17, space: 14 });
  card(s, 7.5, 1.8, 5.23, 2.4);
  tag(s, "L'IA COMME OUTIL", 7.5, 1.8, 3, ALGO.ql);
  txt(s, 'Claude a optimisé DQN et PPO : un gain de temps, mais chaque choix a été vérifié.', 7.8, 2.4, 4.7, 1.6, { fontSize: 16, valign: 'middle' });
  card(s, 7.5, 4.45, 5.23, 2.4);
  tag(s, 'AVEC PLUS DE TEMPS', 7.5, 4.45, 3, GREEN);
  bullets(s, ["Refaire l'ordre du niveau avec Q-Learning et SARSA", 'Tester avec de vrais joueurs'], 7.8, 5.05, 4.7, 1.7, { fontSize: 16, space: 10 });
  s.addNotes(NOTES.autocritique);
}

{
  const s = content('1-4 Le recul', K4, "Ce qu'on retient");
  const take = [['1', 'Niveau simple : les tableaux suffisent', '95 % en 16 secondes'],
                ['2', "Ce que voit l'IA compte plus que la taille du réseau", 'DQN : 40 % → 94 %'],
                ['3', 'Sur le vrai jeu, le deep RL prend le relais', 'PPO : 81 %, Route A : 91 %']];
  take.forEach(([n, t, d], i) => {
    const cx = 0.6 + i * 4.14;
    card(s, cx, 1.8, 3.85, 4.0);
    txt(s, n, cx + 0.3, 2.0, 1, 0.9, { fontSize: 40, bold: true, color: ALGO.ql });
    txt(s, t, cx + 0.3, 2.95, 3.3, 1.5, { fontSize: 20, bold: true });
    txt(s, d, cx + 0.3, 4.75, 3.3, 0.8, { fontSize: 17, color: GREY });
  });
  punch(s, "L'article : tendances confirmées, mais ses chiffres dépendent de détails non publiés.", 6.15);
  s.addNotes(NOTES.conclusion);
}

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
  const s = content('Annexes', 'ANNEXE A', 'Comportement en jeu', 'Par partie, 500 dernières parties (v3, 6000 épisodes, 5 graines).');
  table(s, { x: 0.6, y: 1.95, colW: [2.75, 1.9, 1.9, 1.9, 1.88, 1.8], headH: 0.62, rowH: 0.58, size: 13.5,
    head: ['Algorithme', 'Ennemis\nécrasés', 'Briques\ncassées', 'Blocs ?\nfrappés', 'Pas par\npartie', '1re victoire\n(épisode)'],
    rows: [['Q-Learning', '6,1', '2,9', '4,3', '268', '1322 ± 356'], ['SARSA', '6,9', '3,6', '4,7', '266', '1178 ± 293'],
           ['Monte Carlo', '12,1', '4,9', '5,3', '503', '1108 ± 443'], ["DQN de l'article", '6,0', '2,2', '5,1', '205', '628 ± 194'],
           ['Notre DQN', '12,6', '5,0', '7,1', '246', '632 ± 117']],
    best: [[4, 0], [4, 1], [4, 2]] });
  card(s, 0.6, 5.65, 12.13, 1.2, 'FFF4C2');
  txt(s, "Article : 3,3 à 3,8 ennemis par partie pour les tableaux, 1,4 pour DQN. Nos agents en écrasent 2 à 4 fois plus : l'article ne précise pas les règles des ennemis (activation, rebond, chute), nos choix les rendent sans doute plus faciles à écraser.",
      0.85, 5.7, 11.7, 1.1, { fontSize: 13.5, valign: 'middle' });
  s.addNotes("Annexe : à montrer si le jury demande pourquoi nos retours sont plus élevés que ceux de l'article.");
}
{
  const s = content('Annexes', 'ANNEXE B', 'Les réglages', "Ceux de l'article, et ce que nous avons changé.");
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
  const s = content('Annexes', 'ANNEXE C', "Ce que voit le DQN de l'article", 'Seules 4 lignes de 28 cases autour de Mario, plus sa position : ni trous ni sens des ennemis.');
  const ih = 5.0, iw = ih * 1650 / 1100;
  card(s, (W - iw) / 2 - 0.1, 1.87, iw + 0.2, ih + 0.16, WHITE);
  s.addImage({ path: asset('observation_v3.png'), x: (W - iw) / 2, y: 1.95, w: iw, h: ih, objectName: 'observation_v3' });
  s.addNotes("Annexe : pourquoi le DQN de l'article apprend le niveau par cœur.");
}
{
  const s = content('Annexes', 'ANNEXE D', 'Notre DQN, étape par étape', 'Graines 42 et 43, 6000 épisodes (étude d\'ablation).');
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
  const s = content('Annexes', 'ANNEXE E', 'PPO par graine', 'Vrai jeu NES, 3 M de pas par graine.');
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
  const s = content('Annexes', 'ANNEXE F', 'Route A : les réglages', 'Niveau, boutons et récompense de la version finale.');
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
  const s = content('Annexes', 'ANNEXE G', 'Références', null);
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

if (!process.env.PPO_ONLY) pres.writeFile({ fileName: OUT }).then((f) => console.log('écrit :', f, '-', slideNo, 'diapos'));
