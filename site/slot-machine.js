/* Isolated schematic slot machine. No PROGRAMME / app.js.
   Usage: mountSlotMachine(root, { lang, haptic, onSpinEnd, onJackpot })
   Returns { destroy, spin, setLang }. */
(function (global) {
  'use strict';

  const SYMBOLS = ['star', 'mic', 'poster'];
  const ICONS = {
    star: '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
    mic: '<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/>',
    poster: '<path d="M2 3h20"/><path d="M21 3v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V3"/><path d="m7 21 5-5 5 5"/>',
  };
  const CELL = 24;
  const STRIP = 48;
  const BOOM_MS = 2200;
  const COPY = {
    ru: { label: 'Игровой автомат. Нажмите, чтобы крутить', boom: 'БАХ' },
    en: { label: 'Slot machine. Tap to spin', boom: 'BOOM' },
  };

  function randInt(n) {
    if (n <= 1) return 0;
    const cryptoObj = global.crypto;
    if (!cryptoObj || typeof cryptoObj.getRandomValues !== 'function') {
      throw new Error('CSPRNG unavailable');
    }
    const buf = new Uint32Array(1);
    const range = 0x100000000;
    const limit = range - (range % n);
    for (;;) {
      cryptoObj.getRandomValues(buf);
      const x = buf[0];
      if (x < limit) return x % n;
    }
  }

  function prefersReducedMotion() {
    try { return !!(global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches); }
    catch { return false; }
  }

  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    if (attrs) {
      for (const [k, v] of Object.entries(attrs)) {
        if (v === null || v === undefined || v === false) continue;
        if (k === 'class') node.className = v;
        else if (k.startsWith('on') && typeof v === 'function') node.addEventListener(k.slice(2), v);
        else if (k === 'html') node.innerHTML = v;
        else if (v === true) node.setAttribute(k, '');
        else node.setAttribute(k, String(v));
      }
    }
    for (const child of children.flat()) {
      if (child === null || child === undefined || child === false) continue;
      node.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return node;
  }

  function symbolCell(name) {
    return el('span', {
      class: 'slot-sym',
      html: `<svg viewBox="0 0 24 24" aria-hidden="true">${ICONS[name]}</svg>`,
    });
  }

  function buildReel() {
    const reel = el('span', { class: 'slot-reel' });
    for (let i = 0; i < STRIP; i++) reel.append(symbolCell(SYMBOLS[i % SYMBOLS.length]));
    return reel;
  }

  function mountSlotMachine(root, opts) {
    if (!root) throw new Error('mountSlotMachine: root required');
    const options = opts || {};
    let lang = options.lang === 'en' ? 'en' : 'ru';
    const hapticOn = options.haptic !== false;
    let busy = false;
    let boomTimer = null;
    const reels = [];

    const boomWord = el('span', { class: 'slot-boom-word' }, COPY[lang].boom);
    const boom = el('div', { class: 'slot-boom', 'aria-hidden': 'true' },
      el('span', { class: 'slot-burst' }), boomWord);
    const windows = el('span', { class: 'slot-windows' });
    for (let i = 0; i < 3; i++) {
      const strip = buildReel();
      reels.push({ el: strip, index: 0 });
      windows.append(el('span', { class: 'slot-window' }, strip));
    }
    const hit = el('button', {
      class: 'slot-hit',
      type: 'button',
      'aria-label': COPY[lang].label,
    },
      el('span', { class: 'slot-body' }, windows),
      el('span', { class: 'slot-arm', 'aria-hidden': 'true' },
        el('span', { class: 'slot-knob' }),
        el('span', { class: 'slot-stem' })));
    const wrap = el('div', { class: 'slot' }, boom, hit);
    root.replaceChildren(wrap);

    function strings() { return COPY[lang]; }

    function haptic(kind) {
      if (!hapticOn) return;
      try {
        if (typeof navigator === 'undefined' || typeof navigator.vibrate !== 'function') return;
        navigator.vibrate(kind === 'win' ? [18, 40, 18] : 18);
      } catch { /* ignore */ }
    }

    function clearBoom() {
      clearTimeout(boomTimer);
      boomTimer = null;
      wrap.classList.remove('is-boom', 'is-jackpot');
    }

    function showBoom() {
      clearTimeout(boomTimer);
      wrap.classList.add('is-boom', 'is-jackpot');
      boomTimer = setTimeout(clearBoom, BOOM_MS);
    }

    function setReel(reel, index, animate, duration) {
      if (!animate) {
        reel.el.style.transition = 'none';
        reel.el.style.transform = `translateY(${-index * CELL}px)`;
        reel.index = index;
        return;
      }
      reel.el.style.transition = `transform ${duration}ms cubic-bezier(.15, .8, .1, 1)`;
      reel.el.style.transform = `translateY(${-index * CELL}px)`;
      reel.index = index;
    }

    function waitTransition(node, ms) {
      return new Promise((resolve) => {
        if (prefersReducedMotion() || ms <= 0) { resolve(); return; }
        let done = false;
        const finish = () => {
          if (done) return;
          done = true;
          node.removeEventListener('transitionend', onEnd);
          resolve();
        };
        const onEnd = (e) => { if (e.target === node && e.propertyName === 'transform') finish(); };
        node.addEventListener('transitionend', onEnd);
        setTimeout(finish, ms + 80);
      });
    }

    async function spin() {
      if (busy) return null;
      busy = true;
      hit.disabled = true;
      clearBoom();
      wrap.classList.add('is-spinning');
      haptic('tick');

      const results = [randInt(3), randInt(3), randInt(3)];
      const reduce = prefersReducedMotion();
      const pending = [];

      for (let i = 0; i < 3; i++) {
        const reel = reels[i];
        const loops = 5 + i;
        const cur = reel.index;
        const delta = (results[i] - (cur % 3) + 3) % 3;
        let next = cur + loops * 3 + delta;
        if (next > STRIP - 4) {
          const base = cur % 3;
          setReel(reel, base, false);
          next = base + loops * 3 + ((results[i] - base + 3) % 3);
        }
        const duration = reduce ? 0 : 700 + i * 280;
        if (reduce) {
          setReel(reel, next, false);
          pending.push(Promise.resolve());
        } else {
          // reflow so a wrap reset is not merged with the spin
          void reel.el.offsetWidth;
          setReel(reel, next, true, duration);
          pending.push(waitTransition(reel.el, duration).then(() => haptic('tick')));
        }
      }

      await Promise.all(pending);
      wrap.classList.remove('is-spinning');
      const symbols = results.map((i) => SYMBOLS[i]);
      const jackpot = symbols[0] === symbols[1] && symbols[1] === symbols[2];
      const payload = { symbols, jackpot };
      if (jackpot) {
        haptic('win');
        showBoom();
        if (typeof options.onJackpot === 'function') options.onJackpot(payload);
      }
      if (typeof options.onSpinEnd === 'function') options.onSpinEnd(payload);
      busy = false;
      hit.disabled = false;
      return payload;
    }

    function onClick(e) {
      e.preventDefault();
      spin().catch(() => {
        busy = false;
        hit.disabled = false;
        wrap.classList.remove('is-spinning');
      });
    }
    hit.addEventListener('click', onClick);

    function setLang(next) {
      lang = next === 'en' ? 'en' : 'ru';
      hit.setAttribute('aria-label', strings().label);
      boomWord.textContent = strings().boom;
    }

    function destroy() {
      clearBoom();
      hit.removeEventListener('click', onClick);
      root.replaceChildren();
    }

    return { destroy, spin, setLang };
  }

  global.mountSlotMachine = mountSlotMachine;
})(typeof window !== 'undefined' ? window : this);
