/* ============================================================
   AWS FinSecOps — Enjoy Module (Mini Games)
   All 6 games: Checkers, Chess, PacMan, Snake, Match, 2048
   ============================================================ */

(function () {
  'use strict';

  // ═══════════════════════════════════════════════════════════
  // SHARED UTILITIES
  // ═══════════════════════════════════════════════════════════

  let activeGameId = null;

  function el(tag, attrs, ...children) {
    const e = document.createElement(tag);
    if (attrs) Object.entries(attrs).forEach(([k, v]) => {
      if (k === 'className') e.className = v;
      else if (k === 'style' && typeof v === 'object') Object.assign(e.style, v);
      else if (k.startsWith('on')) e.addEventListener(k.slice(2).toLowerCase(), v);
      else e.setAttribute(k, v);
    });
    children.flat().forEach(c => {
      if (c == null) return;
      e.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
    });
    return e;
  }

  const RESET_SVG = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>';
  const EXPAND_SVG = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>';
  const SHRINK_SVG = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="4 14 10 14 10 20"/><polyline points="20 10 14 10 14 4"/><line x1="14" y1="10" x2="21" y2="3"/><line x1="3" y1="21" x2="10" y2="14"/></svg>';

  function makeBtn(label, onClick, cls) {
    const b = el('button', { className: 'enjoy-btn ' + (cls || ''), onClick });
    b.innerHTML = label;
    return b;
  }

  function makeStat(label, value) {
    const s = el('span', { className: 'enjoy-stat' });
    s.innerHTML = `<span class="enjoy-stat-label">${label}</span> <span class="enjoy-stat-value">${value}</span>`;
    return s;
  }

  // ── Focus Management ──
  function setFocus(gameId) {
    if (activeGameId === gameId) return;
    document.querySelectorAll('.enjoy-card.focused').forEach(c => c.classList.remove('focused'));
    activeGameId = gameId;
    const card = document.getElementById('game-' + gameId);
    if (card) card.classList.add('focused');
  }

  function bindFocus(gameId) {
    const card = document.getElementById('game-' + gameId);
    if (card) card.addEventListener('click', () => setFocus(gameId));
  }

  // ── Fullscreen Toggle ──
  function addFullscreenBtn(controlsEl, gameId, onResize) {
    const btn = el('button', { className: 'enjoy-fullscreen-btn', onClick: (e) => {
      e.stopPropagation();
      const card = document.getElementById('game-' + gameId);
      if (!card) return;
      const isFull = card.classList.toggle('fullscreen');
      btn.innerHTML = isFull ? SHRINK_SVG : EXPAND_SVG;
      if (onResize) setTimeout(onResize, 50);
    }});
    btn.innerHTML = EXPAND_SVG;
    btn.title = 'Fullscreen';
    controlsEl.appendChild(btn);
    return btn;
  }

  // ── State persistence helpers ──
  function saveState(key, data) {
    try { localStorage.setItem(key, JSON.stringify(data)); } catch {}
  }
  function loadState(key) {
    try { const d = localStorage.getItem(key); return d ? JSON.parse(d) : null; } catch { return null; }
  }

  // Escape key exits fullscreen
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const fs = document.querySelector('.enjoy-card.fullscreen');
      if (fs) {
        fs.classList.remove('fullscreen');
        const btn = fs.querySelector('.enjoy-fullscreen-btn');
        if (btn) btn.innerHTML = EXPAND_SVG;
      }
    }
  });

  // Click outside cards defocuses
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.enjoy-card')) {
      document.querySelectorAll('.enjoy-card.focused').forEach(c => c.classList.remove('focused'));
      activeGameId = null;
    }
  });

  // ═══════════════════════════════════════════════════════════
  // 1. AWSOPS CHECKERS
  // ═══════════════════════════════════════════════════════════

  function initCheckers() {
    const body = document.getElementById('checkers-body');
    const controls = document.getElementById('checkers-controls');
    const footer = document.getElementById('checkers-footer');
    if (!body) return;
    bindFocus('checkers');

    const SZ = 8;
    const DEPTH_MAP = { easy: 1, medium: 2, hard: 3 };
    let board, currentPlayer, selectedPos, validMoves, gameOver, mustContinueJump;
    let difficulty = 'medium', moveCount = 0, isThinking = false;
    let stats = loadState('enjoy_checkers_stats') || { wins: 0, losses: 0 };

    function createBoard() {
      const b = Array.from({ length: SZ }, () => Array(SZ).fill(null));
      for (let r = 0; r < 3; r++)
        for (let c = 0; c < SZ; c++)
          if ((r + c) % 2 === 1) b[r][c] = { player: 'ai', type: 'normal' };
      for (let r = 5; r < SZ; r++)
        for (let c = 0; c < SZ; c++)
          if ((r + c) % 2 === 1) b[r][c] = { player: 'human', type: 'normal' };
      return b;
    }

    function cloneBoard(b) { return b.map(r => r.map(c => c ? { ...c } : null)); }

    function getMoves(b, pos, mustJump) {
      const p = b[pos.row][pos.col];
      if (!p) return [];
      const dirs = p.type === 'king' ? [-1, 1] : (p.player === 'human' ? [-1] : [1]);
      const moves = [];
      for (const dr of dirs) for (const dc of [-1, 1]) {
        const jr = pos.row + dr * 2, jc = pos.col + dc * 2;
        const mr = pos.row + dr, mc = pos.col + dc;
        if (jr >= 0 && jr < SZ && jc >= 0 && jc < SZ) {
          const mid = b[mr][mc], dest = b[jr][jc];
          if (mid && mid.player !== p.player && !dest)
            moves.push({ from: pos, to: { row: jr, col: jc }, captures: [{ row: mr, col: mc }], isJump: true });
        }
      }
      if (moves.length > 0 || mustJump) return moves;
      for (const dr of dirs) for (const dc of [-1, 1]) {
        const nr = pos.row + dr, nc = pos.col + dc;
        if (nr >= 0 && nr < SZ && nc >= 0 && nc < SZ && !b[nr][nc])
          moves.push({ from: pos, to: { row: nr, col: nc }, captures: [], isJump: false });
      }
      return moves;
    }

    function getAllMoves(b, player) {
      const all = [];
      let hasJump = false;
      for (let r = 0; r < SZ; r++) for (let c = 0; c < SZ; c++) {
        const p = b[r][c];
        if (p && p.player === player) {
          const ms = getMoves(b, { row: r, col: c });
          ms.forEach(m => { if (m.isJump) hasJump = true; all.push(m); });
        }
      }
      return hasJump ? all.filter(m => m.isJump) : all;
    }

    function applyMove(b, move) {
      const nb = cloneBoard(b);
      const piece = nb[move.from.row][move.from.col];
      nb[move.to.row][move.to.col] = piece;
      nb[move.from.row][move.from.col] = null;
      move.captures.forEach(c => { nb[c.row][c.col] = null; });
      if (piece.type === 'normal') {
        if ((piece.player === 'human' && move.to.row === 0) || (piece.player === 'ai' && move.to.row === SZ - 1))
          nb[move.to.row][move.to.col] = { ...piece, type: 'king' };
      }
      return nb;
    }

    function evaluate(b) {
      let score = 0;
      for (let r = 0; r < SZ; r++) for (let c = 0; c < SZ; c++) {
        const p = b[r][c];
        if (!p) continue;
        const val = 1 + (p.type === 'king' ? 0.5 : 0);
        const posBonus = p.player === 'ai' ? r * 0.1 : (7 - r) * 0.1;
        score += p.player === 'ai' ? (val * 10 + posBonus) : -(val * 10 + posBonus);
      }
      return score;
    }

    function minimax(b, depth, alpha, beta, maximizing) {
      const player = maximizing ? 'ai' : 'human';
      const moves = getAllMoves(b, player);
      if (depth === 0 || moves.length === 0) return { score: evaluate(b), move: null };
      let bestMove = null;
      if (maximizing) {
        let max = -Infinity;
        for (const m of moves) {
          let nb = applyMove(b, m);
          if (m.isJump) { let chain = getMoves(nb, m.to, true); while (chain.length > 0) { nb = applyMove(nb, chain[0]); chain = getMoves(nb, chain[0].to, true); } }
          const r = minimax(nb, depth - 1, alpha, beta, false);
          if (r.score > max) { max = r.score; bestMove = m; }
          alpha = Math.max(alpha, r.score);
          if (beta <= alpha) break;
        }
        return { score: max, move: bestMove };
      } else {
        let min = Infinity;
        for (const m of moves) {
          let nb = applyMove(b, m);
          if (m.isJump) { let chain = getMoves(nb, m.to, true); while (chain.length > 0) { nb = applyMove(nb, chain[0]); chain = getMoves(nb, chain[0].to, true); } }
          const r = minimax(nb, depth - 1, alpha, beta, true);
          if (r.score < min) { min = r.score; bestMove = m; }
          beta = Math.min(beta, r.score);
          if (beta <= alpha) break;
        }
        return { score: min, move: bestMove };
      }
    }

    function persistCheckers() {
      saveState('enjoy_checkers_game', { board, currentPlayer, difficulty, moveCount, gameOver });
    }

    function newGame() {
      board = createBoard();
      currentPlayer = 'human'; selectedPos = null; validMoves = [];
      gameOver = null; mustContinueJump = null; moveCount = 0; isThinking = false;
      persistCheckers();
      render();
    }

    function checkGameOver() {
      const hm = getAllMoves(board, 'human'), am = getAllMoves(board, 'ai');
      let hc = 0, ac = 0;
      for (let r = 0; r < SZ; r++) for (let c = 0; c < SZ; c++) {
        const p = board[r][c]; if (p) { if (p.player === 'human') hc++; else ac++; }
      }
      if (hc === 0 || hm.length === 0) { gameOver = 'ai'; stats.losses++; saveState('enjoy_checkers_stats', stats); }
      else if (ac === 0 || am.length === 0) { gameOver = 'human'; stats.wins++; saveState('enjoy_checkers_stats', stats); }
    }

    function aiMove() {
      if (gameOver || currentPlayer !== 'ai') return;
      isThinking = true; render();
      setTimeout(() => {
        const result = minimax(board, DEPTH_MAP[difficulty], -Infinity, Infinity, true);
        if (result.move) {
          board = applyMove(board, result.move);
          if (result.move.isJump) { let chain = getMoves(board, result.move.to, true); while (chain.length > 0) { board = applyMove(board, chain[0]); chain = getMoves(board, chain[0].to, true); } }
          moveCount++;
        }
        currentPlayer = 'human'; isThinking = false;
        checkGameOver(); persistCheckers(); render();
      }, 400);
    }

    function handleClick(r, c) {
      if (currentPlayer !== 'human' || gameOver || isThinking) return;
      setFocus('checkers');
      const piece = board[r][c], pos = { row: r, col: c };
      if (mustContinueJump) {
        const jm = validMoves.find(m => m.to.row === r && m.to.col === c);
        if (jm) {
          board = applyMove(board, jm); moveCount++;
          const chain = getMoves(board, jm.to, true);
          if (chain.length > 0) { mustContinueJump = jm.to; selectedPos = jm.to; validMoves = chain; }
          else { mustContinueJump = null; selectedPos = null; validMoves = []; currentPlayer = 'ai'; checkGameOver(); persistCheckers(); setTimeout(aiMove, 100); }
          render();
        }
        return;
      }
      if (piece && piece.player === 'human') {
        const allPlayerMoves = getAllMoves(board, 'human');
        const hasJumps = allPlayerMoves.some(m => m.isJump);
        let pMoves = getMoves(board, pos);
        if (hasJumps) pMoves = pMoves.filter(m => m.isJump);
        selectedPos = pos; validMoves = pMoves; render(); return;
      }
      if (selectedPos) {
        const move = validMoves.find(m => m.to.row === r && m.to.col === c);
        if (move) {
          board = applyMove(board, move); moveCount++;
          if (move.isJump) { const chain = getMoves(board, move.to, true); if (chain.length > 0) { mustContinueJump = move.to; selectedPos = move.to; validMoves = chain; render(); return; } }
          selectedPos = null; validMoves = []; mustContinueJump = null; currentPlayer = 'ai';
          checkGameOver(); persistCheckers(); render(); setTimeout(aiMove, 100);
        } else { selectedPos = null; validMoves = []; render(); }
      }
    }

    function render() {
      body.innerHTML = '';
      const card = document.getElementById('game-checkers');
      const isFull = card && card.classList.contains('fullscreen');
      const cellSz = isFull ? Math.min(56, (window.innerHeight - 160) / SZ) : Math.min(40, (body.clientWidth - 40) / SZ);
      const grid = el('div', { className: 'board-grid', style: { gridTemplateColumns: `repeat(${SZ}, ${cellSz}px)` } });
      for (let r = 0; r < SZ; r++) for (let c = 0; c < SZ; c++) {
        const isDark = (r + c) % 2 === 1;
        const cell = el('div', {
          className: `board-cell ${isDark ? 'dark' : 'light'}${selectedPos && selectedPos.row === r && selectedPos.col === c ? ' selected' : ''}${validMoves.some(m => m.to.row === r && m.to.col === c && !m.isJump) ? ' valid-move' : ''}${validMoves.some(m => m.to.row === r && m.to.col === c && m.isJump) ? ' valid-move capture-move' : ''}`,
          style: { width: cellSz + 'px', height: cellSz + 'px' },
          onClick: () => handleClick(r, c)
        });
        const p = board[r][c];
        if (p) cell.appendChild(el('div', { className: `checker-piece ${p.player === 'human' ? 'player' : 'ai'}${p.type === 'king' ? ' king' : ''}${selectedPos && selectedPos.row === r && selectedPos.col === c ? ' selected-piece' : ''}` }));
        grid.appendChild(cell);
      }
      body.appendChild(grid);
      if (gameOver) {
        const ov = el('div', { className: 'enjoy-overlay' });
        ov.innerHTML = `<div class="enjoy-overlay-title">${gameOver === 'human' ? t('enjoy_you_win') : t('enjoy_game_over')}</div><div class="enjoy-overlay-sub">${moveCount} ${t('enjoy_moves')}</div>`;
        ov.appendChild(el('button', { className: 'enjoy-overlay-btn', onClick: newGame }, t('enjoy_play_again')));
        body.appendChild(ov);
      }
      footer.innerHTML = '';
      const statusTxt = isThinking ? t('enjoy_ai_thinking') : (gameOver ? '' : (currentPlayer === 'human' ? t('enjoy_your_turn') : ''));
      if (statusTxt) footer.appendChild(el('span', { className: `enjoy-status ${isThinking ? 'thinking' : ''}` }, statusTxt));
      footer.appendChild(makeStat(t('enjoy_wins'), stats.wins));
      footer.appendChild(makeStat(t('enjoy_losses'), stats.losses));
    }

    // Restore state
    const saved = loadState('enjoy_checkers_game');
    if (saved && saved.board && !saved.gameOver) {
      board = saved.board; currentPlayer = saved.currentPlayer || 'human';
      difficulty = saved.difficulty || 'medium'; moveCount = saved.moveCount || 0;
      gameOver = saved.gameOver || null;
      selectedPos = null; validMoves = []; mustContinueJump = null; isThinking = false;
    } else {
      board = createBoard(); currentPlayer = 'human';
      selectedPos = null; validMoves = []; gameOver = null; mustContinueJump = null; moveCount = 0; isThinking = false;
    }

    controls.innerHTML = '';
    const sel = el('select', { className: 'enjoy-select', onChange: (e) => { difficulty = e.target.value; } });
    ['easy', 'medium', 'hard'].forEach(d => { const opt = el('option', { value: d }, t('enjoy_' + d)); if (d === difficulty) opt.selected = true; sel.appendChild(opt); });
    controls.appendChild(sel);
    controls.appendChild(makeBtn(RESET_SVG, newGame));
    addFullscreenBtn(controls, 'checkers', render);
    render();
    if (currentPlayer === 'ai' && !gameOver) setTimeout(aiMove, 300);
  }

  // ═══════════════════════════════════════════════════════════
  // 2. AWSOPS CHESS
  // ═══════════════════════════════════════════════════════════

  function initChess() {
    const body = document.getElementById('chess-body');
    const controls = document.getElementById('chess-controls');
    const footer = document.getElementById('chess-footer');
    if (!body) return;
    bindFocus('chess');

    const SYMBOLS = {
      white: { K: '\u2654', Q: '\u2655', R: '\u2656', B: '\u2657', N: '\u2658', P: '\u2659' },
      black: { K: '\u265A', Q: '\u265B', R: '\u265C', B: '\u265D', N: '\u265E', P: '\u265F' }
    };
    const VALS = { K: 0, Q: 900, R: 500, B: 330, N: 320, P: 100 };
    const PAWN_T = [[0,0,0,0,0,0,0,0],[50,50,50,50,50,50,50,50],[10,10,20,30,30,20,10,10],[5,5,10,25,25,10,5,5],[0,0,0,20,20,0,0,0],[5,-5,-10,0,0,-10,-5,5],[5,10,10,-20,-20,10,10,5],[0,0,0,0,0,0,0,0]];
    const KNIGHT_T = [[-50,-40,-30,-30,-30,-30,-40,-50],[-40,-20,0,0,0,0,-20,-40],[-30,0,10,15,15,10,0,-30],[-30,5,15,20,20,15,5,-30],[-30,0,15,20,20,15,0,-30],[-30,5,10,15,15,10,5,-30],[-40,-20,0,5,5,0,-20,-40],[-50,-40,-30,-30,-30,-30,-40,-50]];

    let state, selectedSq, validMovesSq, playerColor, difficulty, isThinkingC, promotionPending;
    let chessStats = loadState('enjoy_chess_stats') || { wins: 0, losses: 0, draws: 0 };

    function initBoard() {
      const b = Array.from({ length: 8 }, () => Array(8).fill(null));
      const back = ['R','N','B','Q','K','B','N','R'];
      for (let c = 0; c < 8; c++) { b[1][c] = { type: 'P', color: 'black' }; b[6][c] = { type: 'P', color: 'white' }; b[0][c] = { type: back[c], color: 'black' }; b[7][c] = { type: back[c], color: 'white' }; }
      return b;
    }

    function initState() {
      return { board: initBoard(), turn: 'white', moveHistory: [], castling: { white: { k: true, q: true }, black: { k: true, q: true } }, enPassant: null, halfMove: 0, fullMove: 1, capturedByWhite: [], capturedByBlack: [] };
    }

    function valid(r, c) { return r >= 0 && r < 8 && c >= 0 && c < 8; }

    function pieceMoves(b, r, c, st) {
      const p = b[r][c]; if (!p) return [];
      const moves = [], { color, type } = p;
      const dirs = { R: [[0,1],[0,-1],[1,0],[-1,0]], B: [[1,1],[1,-1],[-1,1],[-1,-1]], Q: [[0,1],[0,-1],[1,0],[-1,0],[1,1],[1,-1],[-1,1],[-1,-1]], K: [[0,1],[0,-1],[1,0],[-1,0],[1,1],[1,-1],[-1,1],[-1,-1]], N: [[2,1],[2,-1],[-2,1],[-2,-1],[1,2],[1,-2],[-1,2],[-1,-2]] };
      if (type === 'P') {
        const d = color === 'white' ? -1 : 1, start = color === 'white' ? 6 : 1;
        if (valid(r+d, c) && !b[r+d][c]) { moves.push({row:r+d,col:c}); if (r === start && !b[r+2*d][c]) moves.push({row:r+2*d,col:c}); }
        for (const dc of [-1,1]) { const nr=r+d,nc=c+dc; if (valid(nr,nc)) { if ((b[nr][nc] && b[nr][nc].color !== color) || (st.enPassant && st.enPassant.row===nr && st.enPassant.col===nc)) moves.push({row:nr,col:nc}); }}
      } else if (type === 'N') {
        for (const [dr,dc] of dirs.N) { const nr=r+dr,nc=c+dc; if (valid(nr,nc) && (!b[nr][nc] || b[nr][nc].color !== color)) moves.push({row:nr,col:nc}); }
      } else if (type === 'K') {
        for (const [dr,dc] of dirs.K) { const nr=r+dr,nc=c+dc; if (valid(nr,nc) && (!b[nr][nc] || b[nr][nc].color !== color)) moves.push({row:nr,col:nc}); }
        const rights = st.castling[color], br = color === 'white' ? 7 : 0;
        if (r === br && c === 4) { if (rights.k && !b[br][5] && !b[br][6]) moves.push({row:br,col:6}); if (rights.q && !b[br][1] && !b[br][2] && !b[br][3]) moves.push({row:br,col:2}); }
      } else {
        const d = type === 'R' ? dirs.R : type === 'B' ? dirs.B : dirs.Q;
        for (const [dr,dc] of d) { let nr=r+dr,nc=c+dc; while (valid(nr,nc)) { if (!b[nr][nc]) { moves.push({row:nr,col:nc}); } else { if (b[nr][nc].color !== color) moves.push({row:nr,col:nc}); break; } nr+=dr; nc+=dc; } }
      }
      return moves;
    }

    function findKing(b, color) { for (let r=0;r<8;r++) for(let c=0;c<8;c++) if(b[r][c]&&b[r][c].type==='K'&&b[r][c].color===color) return {row:r,col:c}; return null; }

    function inCheck(b, color, st) {
      const kp = findKing(b, color); if (!kp) return false;
      const opp = color === 'white' ? 'black' : 'white';
      for (let r=0;r<8;r++) for(let c=0;c<8;c++) if (b[r][c]&&b[r][c].color===opp) { if (pieceMoves(b,r,c,st).some(m=>m.row===kp.row&&m.col===kp.col)) return true; }
      return false;
    }

    function makeChessMove(st, from, to, promo) {
      const nb = st.board.map(r => [...r]);
      const piece = nb[from.row][from.col];
      const capW = [...(st.capturedByWhite || [])];
      const capB = [...(st.capturedByBlack || [])];

      // Track captured piece
      let captured = nb[to.row][to.col];

      // En passant capture
      if (piece.type === 'P' && st.enPassant && to.row === st.enPassant.row && to.col === st.enPassant.col) {
        const epRow = piece.color === 'white' ? to.row+1 : to.row-1;
        captured = nb[epRow][to.col];
        nb[epRow][to.col] = null;
      }

      // Record capture
      if (captured) {
        if (piece.color === 'white') capW.push(captured.type);
        else capB.push(captured.type);
      }

      if (piece.type === 'K' && Math.abs(to.col - from.col) === 2) {
        const castle = to.col > from.col ? 'k' : 'q';
        const rfc = castle === 'k' ? 7 : 0, rtc = castle === 'k' ? 5 : 3;
        nb[from.row][rtc] = nb[from.row][rfc]; nb[from.row][rfc] = null;
      }
      nb[to.row][to.col] = piece; nb[from.row][from.col] = null;
      if (piece.type === 'P' && (to.row === 0 || to.row === 7)) nb[to.row][to.col] = { type: promo || 'Q', color: piece.color };
      const nc = { white: { ...st.castling.white }, black: { ...st.castling.black } };
      if (piece.type === 'K') nc[piece.color] = { k: false, q: false };
      if (piece.type === 'R') { if (from.col === 0) nc[piece.color].q = false; if (from.col === 7) nc[piece.color].k = false; }
      let nep = null;
      if (piece.type === 'P' && Math.abs(to.row - from.row) === 2) nep = { row: (from.row + to.row) / 2, col: from.col };
      return { board: nb, turn: st.turn === 'white' ? 'black' : 'white', moveHistory: [...st.moveHistory, { from, to }], castling: nc, enPassant: nep, halfMove: st.halfMove + 1, fullMove: st.turn === 'black' ? st.fullMove + 1 : st.fullMove, capturedByWhite: capW, capturedByBlack: capB };
    }

    function allLegal(st, color) {
      const moves = [];
      for (let r=0;r<8;r++) for(let c=0;c<8;c++) {
        const p = st.board[r][c];
        if (p && p.color === color) { for (const to of pieceMoves(st.board, r, c, st)) { const ns = makeChessMove(st, {row:r,col:c}, to); if (!inCheck(ns.board, color, ns)) moves.push({ from: {row:r,col:c}, to }); } }
      }
      return moves;
    }

    function gameResult(st) {
      const lm = allLegal(st, st.turn);
      if (lm.length === 0) return inCheck(st.board, st.turn, st) ? 'checkmate' : 'stalemate';
      return 'ongoing';
    }

    function evalBoard(st) {
      let score = 0;
      for (let r=0;r<8;r++) for(let c=0;c<8;c++) {
        const p = st.board[r][c]; if (!p) continue;
        let v = VALS[p.type];
        if (p.type === 'P') v += p.color === 'white' ? PAWN_T[r][c] : PAWN_T[7-r][c];
        else if (p.type === 'N') v += p.color === 'white' ? KNIGHT_T[r][c] : KNIGHT_T[7-r][c];
        score += p.color === 'white' ? v : -v;
      }
      if (inCheck(st.board, 'black', st)) score += 50;
      if (inCheck(st.board, 'white', st)) score -= 50;
      return score;
    }

    function chessMinimax(st, depth, alpha, beta, max) {
      if (depth === 0) return evalBoard(st);
      const gr = gameResult(st);
      if (gr === 'checkmate') return max ? -10000 : 10000;
      if (gr === 'stalemate') return 0;
      const moves = allLegal(st, st.turn);
      if (max) { let mx = -Infinity; for (const m of moves) { mx = Math.max(mx, chessMinimax(makeChessMove(st, m.from, m.to), depth-1, alpha, beta, false)); alpha = Math.max(alpha, mx); if (beta <= alpha) break; } return mx; }
      else { let mn = Infinity; for (const m of moves) { mn = Math.min(mn, chessMinimax(makeChessMove(st, m.from, m.to), depth-1, alpha, beta, true)); beta = Math.min(beta, mn); if (beta <= alpha) break; } return mn; }
    }

    function findBest(st, depth) {
      const moves = allLegal(st, st.turn); if (moves.length === 0) return null;
      let best = moves[0], bestScore = st.turn === 'white' ? -Infinity : Infinity;
      for (const m of moves) {
        const s = chessMinimax(makeChessMove(st, m.from, m.to), depth-1, -Infinity, Infinity, st.turn === 'black');
        if (st.turn === 'white' && s > bestScore) { bestScore = s; best = m; }
        else if (st.turn === 'black' && s < bestScore) { bestScore = s; best = m; }
      }
      return best;
    }

    function persistChess() {
      saveState('enjoy_chess_game', { state, playerColor, difficulty });
    }

    function newChessGame() {
      state = initState(); selectedSq = null; validMovesSq = []; playerColor = 'white'; isThinkingC = false; promotionPending = null;
      persistChess(); renderChess();
    }

    function endGame(gr) {
      if (gr === 'stalemate') chessStats.draws++;
      else { const winner = state.turn === 'white' ? 'black' : 'white'; if (winner === playerColor) chessStats.wins++; else chessStats.losses++; }
      saveState('enjoy_chess_stats', chessStats);
    }

    function doAiMove() {
      if (state.turn === playerColor || gameResult(state) !== 'ongoing') return;
      isThinkingC = true; renderChess();
      setTimeout(() => {
        const depth = difficulty === 1 ? 2 : difficulty === 2 ? 3 : 4;
        const best = findBest(state, depth);
        if (best) state = makeChessMove(state, best.from, best.to);
        isThinkingC = false;
        const gr = gameResult(state);
        if (gr !== 'ongoing') endGame(gr);
        persistChess(); renderChess();
      }, 300);
    }

    function handleChessClick(r, c) {
      if (state.turn !== playerColor || gameResult(state) !== 'ongoing' || isThinkingC) return;
      setFocus('chess');
      const piece = state.board[r][c];
      if (selectedSq) {
        const isValid = validMovesSq.some(m => m.row === r && m.col === c);
        if (isValid) {
          const mp = state.board[selectedSq.row][selectedSq.col];
          if (mp && mp.type === 'P' && (r === 0 || r === 7)) { promotionPending = { from: selectedSq, to: { row: r, col: c } }; selectedSq = null; validMovesSq = []; renderChess(); return; }
          state = makeChessMove(state, selectedSq, { row: r, col: c });
          selectedSq = null; validMovesSq = [];
          const gr = gameResult(state);
          if (gr !== 'ongoing') endGame(gr);
          persistChess(); renderChess(); setTimeout(doAiMove, 100); return;
        }
        if (selectedSq.row === r && selectedSq.col === c) { selectedSq = null; validMovesSq = []; renderChess(); return; }
      }
      if (piece && piece.color === playerColor) {
        selectedSq = { row: r, col: c };
        validMovesSq = pieceMoves(state.board, r, c, state).filter(to => { const ns = makeChessMove(state, {row:r,col:c}, to); return !inCheck(ns.board, playerColor, ns); });
        renderChess();
      } else { selectedSq = null; validMovesSq = []; renderChess(); }
    }

    function handlePromotion(type) {
      if (!promotionPending) return;
      state = makeChessMove(state, promotionPending.from, promotionPending.to, type);
      promotionPending = null; persistChess(); renderChess(); setTimeout(doAiMove, 100);
    }

    function renderChess() {
      body.innerHTML = '';
      const card = document.getElementById('game-chess');
      const isFull = card && card.classList.contains('fullscreen');
      const cellSz = isFull ? Math.min(60, (window.innerHeight - 160) / 8) : Math.min(44, (body.clientWidth - 40) / 8);
      const rows = playerColor === 'white' ? [0,1,2,3,4,5,6,7] : [7,6,5,4,3,2,1,0];
      const cols = playerColor === 'white' ? [0,1,2,3,4,5,6,7] : [7,6,5,4,3,2,1,0];
      const lastMove = state.moveHistory.length > 0 ? state.moveHistory[state.moveHistory.length - 1] : null;
      const isCheck = inCheck(state.board, state.turn, state);

      const grid = el('div', { className: 'board-grid', style: { gridTemplateColumns: `repeat(8, ${cellSz}px)` } });
      for (const r of rows) for (const cIdx of cols) {
        const isLight = (r + cIdx) % 2 === 0;
        const isSelected = selectedSq && selectedSq.row === r && selectedSq.col === cIdx;
        const isValid = validMovesSq.some(m => m.row === r && m.col === cIdx);
        const isLast = lastMove && ((lastMove.from.row === r && lastMove.from.col === cIdx) || (lastMove.to.row === r && lastMove.to.col === cIdx));
        const piece = state.board[r][cIdx];
        const isCheckSq = isCheck && piece && piece.type === 'K' && piece.color === state.turn;
        const cell = el('div', {
          className: `board-cell ${isLight ? 'light' : 'dark'}${isSelected ? ' selected' : ''}${isValid && !piece ? ' valid-move' : ''}${isValid && piece ? ' valid-move capture-move' : ''}${isLast ? ' last-move' : ''}${isCheckSq ? ' in-check' : ''}`,
          style: { width: cellSz + 'px', height: cellSz + 'px' },
          onClick: () => handleChessClick(r, cIdx)
        });
        if (piece) {
          const span = el('span', { className: `chess-piece ${piece.color === 'white' ? 'white-piece' : 'black-piece'}`, style: { fontSize: (cellSz * 0.75) + 'px' } }, SYMBOLS[piece.color][piece.type]);
          cell.appendChild(span);
        }
        grid.appendChild(cell);
      }
      // Build layout: side panel + board
      const layout = el('div', { style: { display: 'flex', gap: '12px', alignItems: 'flex-start', justifyContent: 'center', flexWrap: 'wrap', width: '100%' } });

      // Side panel: turn indicator + captured pieces + stats
      const panel = el('div', { style: { display: 'flex', flexDirection: 'column', gap: '8px', minWidth: '100px', fontSize: '12px' } });

      // Turn indicator
      const turnColor = state.turn === 'white' ? '#f0d9b5' : '#333';
      const turnText = state.turn === playerColor ? (t('enjoy_your_turn') || 'Your Turn') : (isThinkingC ? (t('enjoy_ai_thinking') || 'AI Thinking...') : (t('enjoy_opponent_turn') || 'Opponent'));
      const turnDot = state.turn === 'white' ? '⬜' : '⬛';
      panel.appendChild(el('div', { style: { padding: '6px 10px', background: 'var(--bg-input)', border: '1px solid var(--border)', borderRadius: '6px', textAlign: 'center', fontWeight: '700', color: state.turn === playerColor ? 'var(--accent)' : 'var(--text-muted)' } }, `${turnDot} ${turnText}`));

      // Captured by player (pieces you took)
      const capByPlayer = playerColor === 'white' ? (state.capturedByWhite || []) : (state.capturedByBlack || []);
      const capByOpponent = playerColor === 'white' ? (state.capturedByBlack || []) : (state.capturedByWhite || []);
      const oppColor = playerColor === 'white' ? 'black' : 'white';

      const ORDER = ['Q','R','B','N','P'];
      const sortCap = arr => [...arr].sort((a, b) => ORDER.indexOf(a) - ORDER.indexOf(b));

      const renderCaptured = (pieces, color, label) => {
        const box = el('div', { style: { padding: '6px 10px', background: 'var(--bg-input)', border: '1px solid var(--border)', borderRadius: '6px' } });
        box.appendChild(el('div', { style: { fontSize: '10px', color: 'var(--text-muted)', marginBottom: '3px', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.5px' } }, label));
        const val = VALS;
        const totalVal = pieces.reduce((s, t) => s + (val[t] || 0), 0);
        const pStr = sortCap(pieces).map(t => SYMBOLS[color][t]).join('');
        box.appendChild(el('div', { style: { fontSize: '16px', letterSpacing: '1px', minHeight: '22px' } }, pStr || '—'));
        if (totalVal > 0) box.appendChild(el('div', { style: { fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' } }, `+${totalVal}`));
        return box;
      };

      panel.appendChild(renderCaptured(capByPlayer, oppColor, t('enjoy_captured') || 'Captured'));
      panel.appendChild(renderCaptured(capByOpponent, playerColor, t('enjoy_lost') || 'Lost'));

      // Stats
      const statsBox = el('div', { style: { padding: '6px 10px', background: 'var(--bg-input)', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '11px' } });
      statsBox.appendChild(el('div', { style: { fontSize: '10px', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.5px' } }, t('enjoy_stats') || 'Statistics'));
      const statsGrid = el('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '4px', textAlign: 'center' } });
      const mkStat = (label, val, color) => {
        const d = el('div');
        d.appendChild(el('div', { style: { fontSize: '16px', fontWeight: '700', color } }, String(val)));
        d.appendChild(el('div', { style: { fontSize: '9px', color: 'var(--text-muted)' } }, label));
        return d;
      };
      statsGrid.appendChild(mkStat(t('enjoy_wins') || 'Win', chessStats.wins, '#16a34a'));
      statsGrid.appendChild(mkStat(t('enjoy_losses') || 'Loss', chessStats.losses, '#dc2626'));
      statsGrid.appendChild(mkStat(t('enjoy_draws') || 'Draw', chessStats.draws, 'var(--text-muted)'));
      statsBox.appendChild(statsGrid);

      // Move counter + check status
      const moveInfo = el('div', { style: { marginTop: '6px', fontSize: '10px', color: 'var(--text-muted)' } },
        `Move ${state.fullMove} · ${state.moveHistory.length} moves`);
      statsBox.appendChild(moveInfo);
      if (isCheck && gameResult(state) === 'ongoing') {
        statsBox.appendChild(el('div', { style: { marginTop: '4px', color: '#dc2626', fontWeight: '700', fontSize: '11px' } }, '⚠ CHECK'));
      }
      panel.appendChild(statsBox);

      layout.appendChild(panel);
      layout.appendChild(grid);
      body.appendChild(layout);

      if (promotionPending) {
        const modal = el('div', { className: 'promotion-modal' });
        const opts = el('div', { className: 'promotion-options' });
        ['Q','R','B','N'].forEach(t => opts.appendChild(el('button', { className: 'promotion-btn', onClick: () => handlePromotion(t) }, SYMBOLS[playerColor][t])));
        modal.appendChild(opts); body.appendChild(modal);
      }

      const gr = gameResult(state);
      if (gr !== 'ongoing') {
        const winner = state.turn === 'white' ? 'black' : 'white';
        const ov = el('div', { className: 'enjoy-overlay' });
        ov.innerHTML = `<div class="enjoy-overlay-title">${gr === 'checkmate' ? (winner === playerColor ? t('enjoy_you_win') : t('enjoy_checkmate')) : t('enjoy_stalemate')}</div>`;
        ov.appendChild(el('button', { className: 'enjoy-overlay-btn', onClick: newChessGame }, t('enjoy_play_again')));
        body.appendChild(ov);
      }

      footer.innerHTML = '';
      const turnLabel = state.turn === playerColor ? (t('enjoy_your_turn') || 'Your Turn') : (t('enjoy_opponent_turn') || 'AI Turn');
      const statusTxt = isThinkingC ? t('enjoy_ai_thinking') : (isCheck && gr === 'ongoing' ? `⚠ ${t('enjoy_check')}` : `${turnLabel} · ${t('enjoy_move')} ${state.fullMove}`);
      footer.appendChild(el('span', { className: `enjoy-status ${isThinkingC ? 'thinking' : isCheck ? 'check' : ''}` }, statusTxt));
    }

    // Restore
    const saved = loadState('enjoy_chess_game');
    if (saved && saved.state && saved.state.board) {
      state = saved.state; playerColor = saved.playerColor || 'white'; difficulty = saved.difficulty || 2;
      selectedSq = null; validMovesSq = []; isThinkingC = false; promotionPending = null;
    } else {
      state = initState(); playerColor = 'white'; difficulty = 2;
      selectedSq = null; validMovesSq = []; isThinkingC = false; promotionPending = null;
    }

    controls.innerHTML = '';
    const sel = el('select', { className: 'enjoy-select', onChange: (e) => { difficulty = parseInt(e.target.value); } });
    [[1, t('enjoy_easy')], [2, t('enjoy_medium')], [3, t('enjoy_hard')]].forEach(([v, l]) => { const o = el('option', { value: v }, l); if (v === difficulty) o.selected = true; sel.appendChild(o); });
    controls.appendChild(sel);
    controls.appendChild(makeBtn('↔ ' + t('enjoy_flip'), () => { playerColor = playerColor === 'white' ? 'black' : 'white'; persistChess(); renderChess(); }));
    controls.appendChild(makeBtn(RESET_SVG, newChessGame));
    addFullscreenBtn(controls, 'chess', renderChess);
    renderChess();
    if (state.turn !== playerColor && gameResult(state) === 'ongoing') setTimeout(doAiMove, 300);
  }

  // ═══════════════════════════════════════════════════════════
  // 3. AWSOPS MAN (Pac-Man style)
  // ═══════════════════════════════════════════════════════════

  function initPacMan() {
    const body = document.getElementById('man-body');
    const controls = document.getElementById('man-controls');
    const footer = document.getElementById('man-footer');
    if (!body) return;
    bindFocus('man');

    const W = 21, H = 21, CELL = 16;
    const CW = W * CELL, CH = H * CELL;
    let canvas, ctx;
    let gameState = 'idle', score = 0, lives = 3, level = 1;
    let highScore = parseInt(localStorage.getItem('enjoy_man_highscore') || '0');
    let player, ghosts, dots, powerUps, dir, nextDir, dotCount;
    let loopId, lastPlayerMove = 0, lastGhostMove = 0;
    const PLAYER_SPEED = 150;  // ms between player moves
    const GHOST_SPEED  = 220;  // ms between ghost moves (slower than player)

    const MAZE = [
      [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
      [1,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1],
      [1,0,1,1,0,1,1,1,0,0,1,0,0,1,1,1,0,1,1,0,1],
      [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
      [1,0,1,1,0,1,0,1,1,1,1,1,1,1,0,1,0,1,1,0,1],
      [1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1],
      [1,1,1,1,0,1,1,1,0,0,1,0,0,1,1,1,0,1,1,1,1],
      [1,1,1,1,0,1,0,0,0,0,0,0,0,0,0,1,0,1,1,1,1],
      [1,1,1,1,0,1,0,1,1,2,2,2,1,1,0,1,0,1,1,1,1],
      [0,0,0,0,0,0,0,1,2,2,2,2,2,1,0,0,0,0,0,0,0],
      [1,1,1,1,0,1,0,1,1,1,1,1,1,1,0,1,0,1,1,1,1],
      [1,1,1,1,0,1,0,0,0,0,0,0,0,0,0,1,0,1,1,1,1],
      [1,1,1,1,0,1,0,1,1,1,1,1,1,1,0,1,0,1,1,1,1],
      [1,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1],
      [1,0,1,1,0,1,1,1,0,0,1,0,0,1,1,1,0,1,1,0,1],
      [1,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,1],
      [1,1,0,1,0,1,0,1,1,1,1,1,1,1,0,1,0,1,0,1,1],
      [1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1],
      [1,0,1,1,1,1,1,1,0,0,1,0,0,1,1,1,1,1,1,0,1],
      [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
      [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    ];

    function canMove(x, y) {
      if (x < 0 || x >= W || y < 0 || y >= H) return y === 9 && (x === -1 || x === W);
      return MAZE[y][x] !== 1;
    }

    function initLevel() {
      player = { x: 10, y: 15 };
      dir = { x: 0, y: 0 }; nextDir = { x: 0, y: 0 };
      ghosts = [
        { x: 9, y: 9, color: '#ff4444', dx: 0, dy: -1, scared: false, scaredTimer: 0, releaseAt: 0 },
        { x: 10, y: 9, color: '#ffb8ff', dx: 0, dy: -1, scared: false, scaredTimer: 0, releaseAt: 3000 },
        { x: 11, y: 9, color: '#00ffff', dx: 0, dy: -1, scared: false, scaredTimer: 0, releaseAt: 6000 },
        { x: 10, y: 8, color: '#ffb852', dx: 1, dy: 0, scared: false, scaredTimer: 0, releaseAt: 9000 },
      ];
      dots = []; powerUps = []; dotCount = 0;
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
        if (MAZE[y][x] === 0) {
          if ((x === 1 && y === 3) || (x === 19 && y === 3) || (x === 1 && y === 17) || (x === 19 && y === 17))
            powerUps.push({ x, y, active: true });
          else if (!(x === 10 && y === 15))
            { dots.push({ x, y, active: true }); dotCount++; }
        }
      }
    }

    let gameStartTime = 0;

    function startGame() {
      score = 0; lives = 3; level = 1;
      initLevel();
      gameState = 'playing';
      body.innerHTML = '';
      canvas = el('canvas', { className: 'game-canvas', width: CW, height: CH, tabindex: '0' });
      ctx = canvas.getContext('2d');
      body.appendChild(canvas);
      canvas.focus();
      const now = performance.now();
      lastPlayerMove = now; lastGhostMove = now; gameStartTime = now;
      loopId = requestAnimationFrame(gameLoop);
    }

    function movePlayer(ts) {
      if (ts - lastPlayerMove < PLAYER_SPEED) return;
      lastPlayerMove = ts;
      const nx = player.x + nextDir.x, ny = player.y + nextDir.y;
      if (canMove(nx, ny)) dir = { ...nextDir };
      const mx = player.x + dir.x, my = player.y + dir.y;
      if (canMove(mx, my)) {
        player.x = mx; player.y = my;
        if (player.x < 0) player.x = W - 1;
        else if (player.x >= W) player.x = 0;
      }
      const di = dots.findIndex(d => d.active && d.x === player.x && d.y === player.y);
      if (di >= 0) { dots[di].active = false; score += 10; dotCount--; }
      const pi = powerUps.findIndex(p => p.active && p.x === player.x && p.y === player.y);
      if (pi >= 0) {
        powerUps[pi].active = false; score += 50;
        ghosts.forEach(g => { g.scared = true; g.scaredTimer = 8000; }); // 8 seconds scared
      }
      if (dotCount <= 0 && powerUps.every(p => !p.active)) { level++; initLevel(); gameStartTime = ts; }
    }

    function moveGhosts(ts) {
      if (ts - lastGhostMove < GHOST_SPEED) return;
      const dt = ts - lastGhostMove;
      lastGhostMove = ts;
      const elapsed = ts - gameStartTime;

      ghosts.forEach(g => {
        // Ghost not yet released
        if (elapsed < g.releaseAt) return;

        const possible = [{x:0,y:-1},{x:0,y:1},{x:-1,y:0},{x:1,y:0}].filter(d => {
          const nx = g.x + d.x, ny = g.y + d.y;
          return canMove(nx, ny) && !(d.x === -g.dx && d.y === -g.dy);
        });
        if (possible.length === 0) { g.dx = -g.dx; g.dy = -g.dy; return; }

        if (g.scared) {
          // Flee: maximize distance from player
          possible.sort((a, b) => {
            const da = Math.abs(g.x+a.x-player.x)+Math.abs(g.y+a.y-player.y);
            const db = Math.abs(g.x+b.x-player.x)+Math.abs(g.y+b.y-player.y);
            return db - da;
          });
        } else {
          // Chase: minimize distance — but only 50% of the time to keep it fair
          possible.sort((a, b) => {
            const da = Math.abs(g.x+a.x-player.x)+Math.abs(g.y+a.y-player.y);
            const db = Math.abs(g.x+b.x-player.x)+Math.abs(g.y+b.y-player.y);
            return da - db;
          });
        }
        const chosen = Math.random() < 0.5 ? possible[0] : possible[Math.floor(Math.random() * possible.length)];
        g.dx = chosen.x; g.dy = chosen.y;
        g.x += g.dx; g.y += g.dy;
        if (g.x < 0) g.x = W - 1; else if (g.x >= W) g.x = 0;

        if (g.scared) {
          g.scaredTimer -= dt;
          if (g.scaredTimer <= 0) g.scared = false;
        }
      });

      // Collision check
      ghosts.forEach(g => {
        if (elapsed < g.releaseAt) return;
        if (g.x === player.x && g.y === player.y) {
          if (g.scared) {
            g.scared = false; g.x = 10; g.y = 9;
            g.releaseAt = elapsed + 5000; // respawn after 5 seconds
            score += 200;
          } else {
            lives--;
            if (lives <= 0) {
              gameState = 'gameover';
              if (score > highScore) { highScore = score; localStorage.setItem('enjoy_man_highscore', String(highScore)); }
            } else {
              player = { x: 10, y: 15 }; dir = { x: 0, y: 0 }; nextDir = { x: 0, y: 0 };
              // Brief invulnerability — push ghosts back
              ghosts.forEach(gg => { if (elapsed >= gg.releaseAt) { gg.releaseAt = elapsed + 2000; } });
            }
          }
        }
      });
    }

    function drawGame() {
      if (!ctx) return;
      const styles = getComputedStyle(document.documentElement);
      const bgColor = styles.getPropertyValue('--bg-base').trim() || '#0d1b2a';
      const wallColor = styles.getPropertyValue('--accent').trim() || '#ff9900';
      const borderColor = styles.getPropertyValue('--border').trim() || '#1e3a5f';

      ctx.fillStyle = bgColor;
      ctx.fillRect(0, 0, CW, CH);
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
        if (MAZE[y][x] === 1) {
          ctx.fillStyle = borderColor;
          ctx.fillRect(x*CELL, y*CELL, CELL, CELL);
          ctx.strokeStyle = wallColor; ctx.lineWidth = 0.5;
          ctx.strokeRect(x*CELL+0.5, y*CELL+0.5, CELL-1, CELL-1);
        }
      }
      dots.forEach(d => { if (!d.active) return; ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(d.x*CELL+CELL/2, d.y*CELL+CELL/2, 2, 0, Math.PI*2); ctx.fill(); });
      powerUps.forEach(p => { if (!p.active) return; ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(p.x*CELL+CELL/2, p.y*CELL+CELL/2, 5, 0, Math.PI*2); ctx.fill(); });
      // Player
      const mouthAngle = (Math.sin(Date.now()/100)*0.3)+0.3;
      const angle = dir.x===1?0:dir.x===-1?Math.PI:dir.y===1?Math.PI/2:dir.y===-1?-Math.PI/2:0;
      ctx.fillStyle = '#ffcc00'; ctx.beginPath();
      ctx.arc(player.x*CELL+CELL/2, player.y*CELL+CELL/2, CELL/2-1, angle+mouthAngle, angle+Math.PI*2-mouthAngle);
      ctx.lineTo(player.x*CELL+CELL/2, player.y*CELL+CELL/2); ctx.fill();
      // Ghosts
      const elapsedMs = performance.now() - gameStartTime;
      ghosts.forEach(g => {
        if (elapsedMs < g.releaseAt) return;
        ctx.fillStyle = g.scared ? '#2222ff' : g.color;
        const gx = g.x*CELL+CELL/2, gy = g.y*CELL+CELL/2;
        ctx.beginPath(); ctx.arc(gx, gy-2, CELL/2-2, Math.PI, 0);
        ctx.lineTo(gx+CELL/2-2, gy+CELL/2-2);
        for (let i = 0; i < 3; i++) ctx.lineTo(gx+CELL/2-2-((i+1)*(CELL-4)/3), gy+CELL/2-2-(i%2===0?0:4));
        ctx.lineTo(gx-CELL/2+2, gy+CELL/2-2); ctx.fill();
        ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(gx-3, gy-3, 3, 0, Math.PI*2); ctx.arc(gx+3, gy-3, 3, 0, Math.PI*2); ctx.fill();
        ctx.fillStyle = g.scared ? '#fff' : '#000'; ctx.beginPath(); ctx.arc(gx-3+g.dx, gy-3+g.dy, 1.5, 0, Math.PI*2); ctx.arc(gx+3+g.dx, gy-3+g.dy, 1.5, 0, Math.PI*2); ctx.fill();
      });
    }

    function gameLoop(ts) {
      if (gameState !== 'playing') {
        cancelAnimationFrame(loopId);
        showOverlay();
        return;
      }
      movePlayer(ts);
      moveGhosts(ts);
      drawGame();
      updatePacFooter();
      loopId = requestAnimationFrame(gameLoop);
    }

    function showOverlay() {
      // Don't clear canvas — draw overlay on top
      const ov = el('div', { className: 'enjoy-overlay' });
      if (gameState === 'gameover') {
        ov.innerHTML = `<div class="enjoy-overlay-title">${t('enjoy_game_over')}</div><div class="enjoy-overlay-sub">${t('enjoy_score')}: ${score}</div>`;
        if (score === highScore && score > 0) ov.innerHTML += `<div class="enjoy-overlay-sub" style="color:var(--yellow)">🏆 ${t('enjoy_high_score')}!</div>`;
        ov.appendChild(el('button', { className: 'enjoy-overlay-btn', onClick: startGame }, t('enjoy_play_again')));
      } else {
        ov.innerHTML = `<div class="enjoy-overlay-title" style="color:var(--yellow)">AwsOps Man</div><div class="enjoy-overlay-sub">${t('enjoy_arrows_or_wasd')}</div>`;
        ov.appendChild(el('button', { className: 'enjoy-overlay-btn', onClick: startGame }, t('enjoy_start_game')));
      }
      body.appendChild(ov);
    }

    function updatePacFooter() {
      footer.innerHTML = '';
      footer.appendChild(makeStat(t('enjoy_score'), score));
      footer.appendChild(makeStat(t('enjoy_lives'), '♥'.repeat(Math.max(0, lives))));
      footer.appendChild(makeStat(t('enjoy_level'), level));
      footer.appendChild(makeStat(t('enjoy_best'), highScore));
    }

    function renderInitial() {
      body.innerHTML = '';
      canvas = el('canvas', { className: 'game-canvas', width: CW, height: CH });
      ctx = canvas.getContext('2d');
      body.appendChild(canvas);
      initLevel(); drawGame();
      showOverlay();
      updatePacFooter();
    }

    // Keyboard — only when this game is focused
    document.addEventListener('keydown', (e) => {
      if (activeGameId !== 'man' || gameState !== 'playing') return;
      const k = e.key.toLowerCase();
      if (k === 'arrowup' || k === 'w') { nextDir = { x: 0, y: -1 }; e.preventDefault(); }
      else if (k === 'arrowdown' || k === 's') { nextDir = { x: 0, y: 1 }; e.preventDefault(); }
      else if (k === 'arrowleft' || k === 'a') { nextDir = { x: -1, y: 0 }; e.preventDefault(); }
      else if (k === 'arrowright' || k === 'd') { nextDir = { x: 1, y: 0 }; e.preventDefault(); }
    });

    controls.innerHTML = '';
    addFullscreenBtn(controls, 'man', null);
    renderInitial();
  }

  // ═══════════════════════════════════════════════════════════
  // 4. AWSOPS SNAKE
  // ═══════════════════════════════════════════════════════════

  function initSnake() {
    const body = document.getElementById('snake-body');
    const controls = document.getElementById('snake-controls');
    const footer = document.getElementById('snake-footer');
    if (!body) return;
    bindFocus('snake');

    const GRID = 20, CW = 360, CH = 360;
    const CELL_SZ = CW / GRID;
    const INIT_SPEED = 150, MIN_SPEED = 60;
    let canvas, ctx, snake, direction, nextDirection, food, gameState, score, highScore, speed, loopId, lastMoveTs;

    highScore = parseInt(localStorage.getItem('enjoy_snake_highscore') || '0');

    function getColors() {
      const s = getComputedStyle(document.documentElement);
      return { bg: s.getPropertyValue('--bg-base').trim() || '#0d1b2a', grid: s.getPropertyValue('--border').trim() || '#1e3a5f', snake: s.getPropertyValue('--accent').trim() || '#ff9900', head: s.getPropertyValue('--green').trim() || '#10b981', food: '#ef4444', foodGlow: 'rgba(239,68,68,0.3)' };
    }

    function genFood() {
      let f; do { f = { x: Math.floor(Math.random() * GRID), y: Math.floor(Math.random() * GRID) }; } while (snake.some(s => s.x === f.x && s.y === f.y));
      return f;
    }

    function initGame() {
      snake = [{ x: 10, y: 10 }, { x: 9, y: 10 }, { x: 8, y: 10 }];
      direction = { x: 1, y: 0 }; nextDirection = { x: 1, y: 0 };
      score = 0; speed = INIT_SPEED; food = genFood();
    }

    function moveSnakeStep() {
      direction = { ...nextDirection };
      const head = { x: snake[0].x + direction.x, y: snake[0].y + direction.y };
      if (head.x < 0 || head.x >= GRID || head.y < 0 || head.y >= GRID) return die();
      if (snake.some(s => s.x === head.x && s.y === head.y)) return die();
      snake.unshift(head);
      if (head.x === food.x && head.y === food.y) { score += 10; speed = Math.max(MIN_SPEED, speed - 3); food = genFood(); }
      else snake.pop();
    }

    function die() {
      gameState = 'gameover';
      if (score > highScore) { highScore = score; localStorage.setItem('enjoy_snake_highscore', String(highScore)); }
    }

    function drawSnake() {
      const C = getColors();
      ctx.fillStyle = C.bg; ctx.fillRect(0, 0, CW, CH);
      ctx.strokeStyle = C.grid; ctx.lineWidth = 0.3;
      for (let i = 0; i <= GRID; i++) { ctx.beginPath(); ctx.moveTo(i*CELL_SZ,0); ctx.lineTo(i*CELL_SZ,CH); ctx.stroke(); ctx.beginPath(); ctx.moveTo(0,i*CELL_SZ); ctx.lineTo(CW,i*CELL_SZ); ctx.stroke(); }
      ctx.fillStyle = C.foodGlow; ctx.beginPath(); ctx.arc(food.x*CELL_SZ+CELL_SZ/2, food.y*CELL_SZ+CELL_SZ/2, CELL_SZ*0.8, 0, Math.PI*2); ctx.fill();
      ctx.fillStyle = C.food; ctx.beginPath(); ctx.arc(food.x*CELL_SZ+CELL_SZ/2, food.y*CELL_SZ+CELL_SZ/2, CELL_SZ/2-2, 0, Math.PI*2); ctx.fill();
      snake.forEach((seg, i) => {
        ctx.fillStyle = i === 0 ? C.head : C.snake;
        const x = seg.x*CELL_SZ+1, y = seg.y*CELL_SZ+1, sz = CELL_SZ-2;
        ctx.beginPath(); ctx.roundRect(x, y, sz, sz, i === 0 ? sz/3 : sz/4); ctx.fill();
        if (i === 0) { ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(x+sz/3, y+sz/3, 2.5, 0, Math.PI*2); ctx.arc(x+sz*2/3, y+sz/3, 2.5, 0, Math.PI*2); ctx.fill(); }
      });
    }

    function snakeLoop(ts) {
      if (gameState !== 'playing') { cancelAnimationFrame(loopId); showSnakeOverlay(); return; }
      if (ts - lastMoveTs >= speed) { moveSnakeStep(); lastMoveTs = ts; }
      drawSnake(); updateSnakeFooter();
      loopId = requestAnimationFrame(snakeLoop);
    }

    function startSnake() {
      initGame(); gameState = 'playing';
      body.innerHTML = '';
      canvas = el('canvas', { className: 'game-canvas', width: CW, height: CH, tabindex: '0' });
      ctx = canvas.getContext('2d'); body.appendChild(canvas); canvas.focus();
      lastMoveTs = performance.now();
      loopId = requestAnimationFrame(snakeLoop);
    }

    function showSnakeOverlay() {
      const ov = el('div', { className: 'enjoy-overlay' });
      if (gameState === 'gameover') {
        ov.innerHTML = `<div class="enjoy-overlay-title">${t('enjoy_game_over')}</div><div class="enjoy-overlay-sub">${t('enjoy_score')}: ${score}</div>`;
        if (score === highScore && score > 0) ov.innerHTML += `<div class="enjoy-overlay-sub" style="color:var(--yellow)">🏆 ${t('enjoy_high_score')}!</div>`;
        ov.appendChild(el('button', { className: 'enjoy-overlay-btn', onClick: startSnake }, t('enjoy_play_again')));
      } else {
        ov.innerHTML = `<div class="enjoy-overlay-title" style="color:var(--green)">AwsOps Snake</div><div class="enjoy-overlay-sub">${t('enjoy_arrows_or_wasd')}</div>`;
        ov.appendChild(el('button', { className: 'enjoy-overlay-btn', onClick: startSnake }, t('enjoy_start_game')));
      }
      body.appendChild(ov);
    }

    function updateSnakeFooter() {
      footer.innerHTML = '';
      footer.appendChild(makeStat(t('enjoy_score'), score));
      footer.appendChild(makeStat(t('enjoy_speed'), Math.round((INIT_SPEED - speed) / 3) + 1));
      footer.appendChild(makeStat(t('enjoy_best'), highScore));
    }

    function renderSnakeUI() {
      body.innerHTML = '';
      canvas = el('canvas', { className: 'game-canvas', width: CW, height: CH });
      ctx = canvas.getContext('2d'); body.appendChild(canvas);
      initGame(); drawSnake(); showSnakeOverlay(); updateSnakeFooter();
    }

    document.addEventListener('keydown', (e) => {
      if (activeGameId !== 'snake' || gameState !== 'playing') return;
      const k = e.key.toLowerCase();
      if ((k === 'arrowup' || k === 'w') && direction.y !== 1) { nextDirection = { x: 0, y: -1 }; e.preventDefault(); }
      else if ((k === 'arrowdown' || k === 's') && direction.y !== -1) { nextDirection = { x: 0, y: 1 }; e.preventDefault(); }
      else if ((k === 'arrowleft' || k === 'a') && direction.x !== 1) { nextDirection = { x: -1, y: 0 }; e.preventDefault(); }
      else if ((k === 'arrowright' || k === 'd') && direction.x !== -1) { nextDirection = { x: 1, y: 0 }; e.preventDefault(); }
    });

    controls.innerHTML = '';
    addFullscreenBtn(controls, 'snake', null);
    gameState = 'idle'; renderSnakeUI();
  }

  // ═══════════════════════════════════════════════════════════
  // 5. AWSOPS MATCH (Memory Card Game)
  // ═══════════════════════════════════════════════════════════

  function initMatch() {
    const body = document.getElementById('match-body');
    const controls = document.getElementById('match-controls');
    const footer = document.getElementById('match-footer');
    if (!body) return;
    bindFocus('match');

    const CARD_ICONS = [
      { id: 'server', svg: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>', color: 'var(--blue)' },
      { id: 'cloud', svg: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/></svg>', color: 'var(--accent)' },
      { id: 'shield', svg: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>', color: 'var(--green)' },
      { id: 'database', svg: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>', color: 'var(--yellow)' },
      { id: 'globe', svg: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>', color: 'var(--blue)' },
      { id: 'lock', svg: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>', color: 'var(--accent)' },
      { id: 'cpu', svg: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/></svg>', color: 'var(--green)' },
      { id: 'network', svg: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="5" r="3"/><circle cx="5" cy="19" r="3"/><circle cx="19" cy="19" r="3"/><line x1="12" y1="8" x2="5" y2="16"/><line x1="12" y1="8" x2="19" y2="16"/></svg>', color: 'var(--yellow)' },
      { id: 'storage', svg: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="1" y="6" width="22" height="12" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>', color: 'var(--blue)' },
      { id: 'key', svg: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.78 7.78 5.5 5.5 0 0 1 7.78-7.78zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>', color: 'var(--accent)' },
      { id: 'lambda', svg: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M4 20L12 4L16 14L22 14"/><line x1="4" y1="20" x2="10" y2="20"/></svg>', color: 'var(--green)' },
      { id: 'terminal', svg: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>', color: 'var(--yellow)' },
    ];

    const DIFF = { easy: { rows: 3, cols: 4, pairs: 6 }, medium: { rows: 4, cols: 4, pairs: 8 }, hard: { rows: 4, cols: 6, pairs: 12 } };
    let difficulty = 'easy', cards = [], flippedCards = [], moves = 0, time = 0, isPlaying = false, gameWon = false, timerId;
    let highScores = loadState('enjoy_match_scores') || { easy: null, medium: null, hard: null };

    function shuffle(arr) { const a = [...arr]; for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }

    function persistMatch() {
      saveState('enjoy_match_game', { cards, difficulty, moves, time, isPlaying, gameWon, flippedCards: [] });
    }

    function startMatch() {
      const cfg = DIFF[difficulty];
      cards = shuffle(CARD_ICONS.slice(0, cfg.pairs).flatMap(ic => [
        { id: ic.id + '-1', iconId: ic.id, matched: false },
        { id: ic.id + '-2', iconId: ic.id, matched: false },
      ]));
      flippedCards = []; moves = 0; time = 0; isPlaying = true; gameWon = false;
      if (timerId) clearInterval(timerId);
      timerId = setInterval(() => { if (isPlaying && !gameWon) { time++; updateMatchFooter(); } }, 1000);
      persistMatch(); renderMatch();
    }

    function handleCardClick(cardId) {
      if (flippedCards.length >= 2 || flippedCards.includes(cardId) || gameWon) return;
      setFocus('match');
      const card = cards.find(c => c.id === cardId);
      if (!card || card.matched) return;
      flippedCards.push(cardId);
      renderMatch();
      if (flippedCards.length === 2) {
        moves++;
        const c1 = cards.find(c => c.id === flippedCards[0]), c2 = cards.find(c => c.id === flippedCards[1]);
        if (c1.iconId === c2.iconId) {
          setTimeout(() => { c1.matched = true; c2.matched = true; flippedCards = []; checkWin(); persistMatch(); renderMatch(); }, 400);
        } else {
          setTimeout(() => { flippedCards = []; renderMatch(); }, 800);
        }
      }
    }

    function checkWin() {
      if (cards.every(c => c.matched)) {
        gameWon = true; isPlaying = false;
        if (timerId) clearInterval(timerId);
        const hs = highScores[difficulty];
        if (!hs || moves < hs.moves || (moves === hs.moves && time < hs.time)) {
          highScores[difficulty] = { moves, time };
          localStorage.setItem('enjoy_match_scores', JSON.stringify(highScores));
        }
      }
    }

    function fmtTime(s) { return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); }

    function updateMatchFooter() {
      footer.innerHTML = '';
      footer.appendChild(makeStat(t('enjoy_moves'), moves));
      footer.appendChild(makeStat(t('enjoy_time'), fmtTime(time)));
      const hs = highScores[difficulty];
      if (hs) footer.appendChild(makeStat(t('enjoy_best'), hs.moves + ' / ' + fmtTime(hs.time)));
    }

    function renderMatch() {
      body.innerHTML = '';
      const cfg = DIFF[difficulty];
      if (!isPlaying && cards.length === 0) {
        const ov = el('div', { className: 'enjoy-overlay', style: { position: 'relative', background: 'transparent' } });
        ov.innerHTML = `<div class="enjoy-overlay-title" style="color:var(--blue)">AwsOps Match</div><div class="enjoy-overlay-sub">${t('enjoy_desc_match')}</div>`;
        ov.appendChild(el('button', { className: 'enjoy-overlay-btn', onClick: startMatch }, t('enjoy_start_game')));
        body.appendChild(ov); updateMatchFooter(); return;
      }
      const grid = el('div', { className: 'match-grid', style: { gridTemplateColumns: `repeat(${cfg.cols}, 56px)` } });
      cards.forEach(card => {
        const icon = CARD_ICONS.find(i => i.id === card.iconId);
        const isFlipped = flippedCards.includes(card.id) || card.matched;
        const cardEl = el('div', { className: `match-card${isFlipped ? ' flipped' : ''}${card.matched ? ' matched' : ''}`, onClick: () => handleCardClick(card.id) });
        const inner = el('div', { className: 'match-card-inner' });
        const back = el('div', { className: 'match-card-face match-card-back' });
        back.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/></svg>';
        const front = el('div', { className: 'match-card-face match-card-front' });
        if (icon) { front.innerHTML = icon.svg; front.style.color = icon.color; }
        inner.appendChild(back); inner.appendChild(front); cardEl.appendChild(inner); grid.appendChild(cardEl);
      });
      body.appendChild(grid);
      if (gameWon) {
        const ov = el('div', { className: 'enjoy-overlay' });
        ov.innerHTML = `<div class="enjoy-overlay-title">${t('enjoy_congratulations')}</div><div class="enjoy-overlay-sub">${t('enjoy_completed_in')} ${moves} ${t('enjoy_moves').toLowerCase()}, ${fmtTime(time)}</div>`;
        ov.appendChild(el('button', { className: 'enjoy-overlay-btn', onClick: startMatch }, t('enjoy_play_again')));
        body.appendChild(ov);
      }
      updateMatchFooter();
    }

    // Restore
    const saved = loadState('enjoy_match_game');
    if (saved && saved.cards && saved.cards.length > 0 && saved.isPlaying && !saved.gameWon) {
      cards = saved.cards; difficulty = saved.difficulty || 'easy'; moves = saved.moves || 0; time = saved.time || 0;
      isPlaying = true; gameWon = false; flippedCards = [];
      timerId = setInterval(() => { if (isPlaying && !gameWon) { time++; updateMatchFooter(); } }, 1000);
    }

    controls.innerHTML = '';
    const sel = el('select', { className: 'enjoy-select', onChange: (e) => { difficulty = e.target.value; cards = []; isPlaying = false; if (timerId) clearInterval(timerId); renderMatch(); } });
    ['easy', 'medium', 'hard'].forEach(d => { const o = el('option', { value: d }, t('enjoy_' + d)); if (d === difficulty) o.selected = true; sel.appendChild(o); });
    controls.appendChild(sel);
    controls.appendChild(makeBtn(RESET_SVG, () => { cards = []; isPlaying = false; if (timerId) clearInterval(timerId); saveState('enjoy_match_game', null); renderMatch(); }));
    addFullscreenBtn(controls, 'match', renderMatch);
    renderMatch();
  }

  // ═══════════════════════════════════════════════════════════
  // 6. AWSOPS 2048
  // ═══════════════════════════════════════════════════════════

  function init2048() {
    const body = document.getElementById('g2048-body');
    const controls = document.getElementById('g2048-controls');
    const footer = document.getElementById('g2048-footer');
    if (!body) return;
    bindFocus('2048');

    const TILE_COLORS = {
      2:    { bg: 'var(--blue)',   text: '#fff' }, 4:    { bg: '#2563eb', text: '#fff' },
      8:    { bg: '#06b6d4',       text: '#fff' }, 16:   { bg: '#0891b2', text: '#fff' },
      32:   { bg: 'var(--accent)', text: '#000' }, 64:   { bg: '#d97706', text: '#fff' },
      128:  { bg: 'var(--green)',  text: '#fff' }, 256:  { bg: '#059669', text: '#fff' },
      512:  { bg: '#eab308',       text: '#000' }, 1024: { bg: '#f97316', text: '#fff' },
      2048: { bg: '#a855f7',       text: '#fff' }, 4096: { bg: '#7c3aed', text: '#fff' },
      8192: { bg: '#ef4444',       text: '#fff' },
    };

    let grid, score, bestScore, gameOver, won, keepPlaying;
    bestScore = parseInt(localStorage.getItem('enjoy_2048_best') || '0');

    function empty() { return Array.from({ length: 4 }, () => Array(4).fill(null)); }
    function addRandom(g) {
      const ng = g.map(r => [...r]); const cells = [];
      for (let r = 0; r < 4; r++) for (let c = 0; c < 4; c++) if (!ng[r][c]) cells.push([r, c]);
      if (cells.length === 0) return ng;
      const [r, c] = cells[Math.floor(Math.random() * cells.length)];
      ng[r][c] = Math.random() < 0.9 ? 2 : 4; return ng;
    }
    function initGrid() { let g = empty(); g = addRandom(g); g = addRandom(g); return g; }

    function slideLine(line) {
      const tiles = line.filter(t => t !== null); const result = []; let sc = 0, moved = false; let i = 0;
      while (i < tiles.length) { if (i + 1 < tiles.length && tiles[i] === tiles[i + 1]) { const m = tiles[i] * 2; result.push(m); sc += m; i += 2; } else { result.push(tiles[i]); i++; } }
      while (result.length < 4) result.push(null);
      for (let j = 0; j < 4; j++) if (line[j] !== result[j]) moved = true;
      return { line: result, score: sc, moved };
    }

    function moveGrid(g, dir) {
      const ng = g.map(r => [...r]); let totalScore = 0, anyMoved = false;
      if (dir === 'left') { for (let r = 0; r < 4; r++) { const { line, score: s, moved } = slideLine(ng[r]); ng[r] = line; totalScore += s; if (moved) anyMoved = true; } }
      else if (dir === 'right') { for (let r = 0; r < 4; r++) { const { line, score: s, moved } = slideLine([...ng[r]].reverse()); ng[r] = line.reverse(); totalScore += s; if (moved) anyMoved = true; } }
      else if (dir === 'up') { for (let c = 0; c < 4; c++) { const col = [ng[0][c],ng[1][c],ng[2][c],ng[3][c]]; const { line, score: s, moved } = slideLine(col); for (let r=0;r<4;r++) ng[r][c]=line[r]; totalScore+=s; if (moved) anyMoved=true; } }
      else if (dir === 'down') { for (let c = 0; c < 4; c++) { const col = [ng[3][c],ng[2][c],ng[1][c],ng[0][c]]; const { line, score: s, moved } = slideLine(col); for (let r=0;r<4;r++) ng[3-r][c]=line[r]; totalScore+=s; if (moved) anyMoved=true; } }
      return { grid: ng, score: totalScore, moved: anyMoved };
    }

    function canMove(g) { for (let r=0;r<4;r++) for(let c=0;c<4;c++) { if (!g[r][c]) return true; if (c<3 && g[r][c]===g[r][c+1]) return true; if (r<3 && g[r][c]===g[r+1][c]) return true; } return false; }
    function hasWon(g) { for (let r=0;r<4;r++) for(let c=0;c<4;c++) if(g[r][c]===2048) return true; return false; }

    function persist2048() {
      saveState('enjoy_2048_game', { grid, score, bestScore, gameOver, won, keepPlaying });
    }

    function handleMove(dir) {
      if (gameOver) return;
      const result = moveGrid(grid, dir);
      if (result.moved) {
        grid = addRandom(result.grid); score += result.score;
        if (score > bestScore) { bestScore = score; localStorage.setItem('enjoy_2048_best', String(bestScore)); }
        if (!won && !keepPlaying && hasWon(grid)) won = true;
        if (!canMove(grid)) gameOver = true;
        persist2048(); render2048();
      }
    }

    function newGame2048() {
      grid = initGrid(); score = 0; gameOver = false; won = false; keepPlaying = false;
      persist2048(); render2048();
    }

    function render2048() {
      body.innerHTML = '';
      const g = el('div', { className: 'g2048-grid' });
      for (let r = 0; r < 4; r++) for (let c = 0; c < 4; c++) {
        const v = grid[r][c];
        const colors = v ? (TILE_COLORS[v] || { bg: '#ef4444', text: '#fff' }) : null;
        const cell = el('div', { className: `g2048-cell${v ? '' : ' empty'}`, style: v ? { background: colors.bg, color: colors.text } : {} });
        if (v) cell.textContent = v;
        g.appendChild(cell);
      }
      body.appendChild(g);
      if (won && !keepPlaying) {
        const ov = el('div', { className: 'enjoy-overlay' });
        ov.innerHTML = `<div class="enjoy-overlay-title" style="color:var(--yellow)">${t('enjoy_you_win')}</div>`;
        const btns = el('div', { style: { display: 'flex', gap: '8px' } });
        btns.appendChild(el('button', { className: 'enjoy-overlay-btn', onClick: () => { won = false; keepPlaying = true; persist2048(); render2048(); } }, t('enjoy_keep_playing')));
        btns.appendChild(el('button', { className: 'enjoy-overlay-btn', onClick: newGame2048 }, t('enjoy_new_game')));
        ov.appendChild(btns); body.appendChild(ov);
      }
      if (gameOver) {
        const ov = el('div', { className: 'enjoy-overlay' });
        ov.innerHTML = `<div class="enjoy-overlay-title">${t('enjoy_game_over')}</div><div class="enjoy-overlay-sub">${t('enjoy_score')}: ${score}</div>`;
        ov.appendChild(el('button', { className: 'enjoy-overlay-btn', onClick: newGame2048 }, t('enjoy_try_again')));
        body.appendChild(ov);
      }
      footer.innerHTML = '';
      footer.appendChild(makeStat(t('enjoy_score'), score));
      footer.appendChild(makeStat(t('enjoy_best'), bestScore));
    }

    // Keyboard — only when focused
    document.addEventListener('keydown', (e) => {
      if (activeGameId !== '2048') return;
      const k = e.key.toLowerCase();
      if (k === 'arrowup' || k === 'w') { handleMove('up'); e.preventDefault(); }
      else if (k === 'arrowdown' || k === 's') { handleMove('down'); e.preventDefault(); }
      else if (k === 'arrowleft' || k === 'a') { handleMove('left'); e.preventDefault(); }
      else if (k === 'arrowright' || k === 'd') { handleMove('right'); e.preventDefault(); }
    });

    // Restore
    const saved = loadState('enjoy_2048_game');
    if (saved && saved.grid) {
      grid = saved.grid; score = saved.score || 0; bestScore = parseInt(localStorage.getItem('enjoy_2048_best') || '0');
      gameOver = saved.gameOver || false; won = saved.won || false; keepPlaying = saved.keepPlaying || false;
    } else {
      grid = initGrid(); score = 0; gameOver = false; won = false; keepPlaying = false;
    }

    controls.innerHTML = '';
    controls.appendChild(makeBtn(RESET_SVG, newGame2048));
    addFullscreenBtn(controls, '2048', render2048);
    render2048();
  }

  // ═══════════════════════════════════════════════════════════
  // INIT ALL GAMES
  // ═══════════════════════════════════════════════════════════

  document.addEventListener('DOMContentLoaded', () => {
    initCheckers();
    initChess();
    initPacMan();
    initSnake();
    initMatch();
    init2048();
  });

})();
