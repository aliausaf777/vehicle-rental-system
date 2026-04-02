/* Elite Auto Rentals — Global JS */

// ── Sticky nav ──────────────────────────────────────────────
const nav = document.getElementById('main-nav');
if (nav) {
  function updateNav() { nav.classList.toggle('scrolled', window.scrollY > 40); }
  window.addEventListener('scroll', updateNav, { passive: true });
  updateNav();
}

// ── Smooth anchor scroll ────────────────────────────────────
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    const t = document.querySelector(a.getAttribute('href'));
    if (t) { e.preventDefault(); t.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
  });
});

// ── Toast helper ────────────────────────────────────────────
window.showToast = function(msg, type = '') {
  let stack = document.querySelector('.toast-stack');
  if (!stack) { stack = document.createElement('div'); stack.className = 'toast-stack'; document.body.appendChild(stack); }
  const t = document.createElement('div');
  t.className = 'toast' + (type ? ' ' + type : '');
  t.textContent = msg;
  stack.appendChild(t);
  setTimeout(() => t.remove(), 3800);
};

// ── Card number formatter ────────────────────────────────────
const cardInput = document.getElementById('cardNum');
if (cardInput) {
  cardInput.addEventListener('input', function () {
    let v = this.value.replace(/\D/g, '').substring(0, 16);
    this.value = v.replace(/(.{4})/g, '$1 ').trim();
  });
}

// ── Expiry formatter ─────────────────────────────────────────
const expiry = document.getElementById('expiryInput');
if (expiry) {
  expiry.addEventListener('input', function () {
    let v = this.value.replace(/\D/g, '');
    if (v.length >= 2) v = v.slice(0, 2) + ' / ' + v.slice(2, 4);
    this.value = v;
  });
}

// ── Modal helpers ─────────────────────────────────────────────
window.openModal = id => document.getElementById(id)?.classList.add('open');
window.closeModal = id => document.getElementById(id)?.classList.remove('open');
document.querySelectorAll('.modal-bg').forEach(m => {
  m.addEventListener('click', e => { if (e.target === m) m.classList.remove('open'); });
});