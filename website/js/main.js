// ===== GO Corporation WPC Fence Website — Main JS =====

document.addEventListener('DOMContentLoaded', () => {
  // Mobile nav toggle
  const nav = document.querySelector('.nav');
  const toggle = document.querySelector('.nav-toggle');
  if (toggle) {
    toggle.addEventListener('click', () => nav.classList.toggle('open'));
    document.addEventListener('click', (e) => {
      if (!nav.contains(e.target)) nav.classList.remove('open');
    });
  }

  // Nav scroll effect
  window.addEventListener('scroll', () => {
    nav?.classList.toggle('scrolled', window.scrollY > 20);
  });

  // Active nav link
  const currentPage = location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-links a').forEach(a => {
    if (a.getAttribute('href') === currentPage) a.classList.add('active');
  });

  // Fade-in on scroll
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible'); });
  }, { threshold: 0.1 });
  document.querySelectorAll('.fade-in').forEach(el => observer.observe(el));

  // Lazy load images
  document.querySelectorAll('img[loading="lazy"]').forEach(img => {
    if (img.complete) img.classList.add('loaded');
    else img.addEventListener('load', () => img.classList.add('loaded'));
  });

  // Tabs
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const group = btn.closest('.tabs-container') || document;
      group.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      group.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      btn.classList.add('active');
      const target = document.getElementById(btn.dataset.tab);
      if (target) target.classList.add('active');
    });
  });

  // Gallery filters
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const filter = btn.dataset.filter;
      document.querySelectorAll('.gallery-item').forEach(item => {
        item.style.display = (!filter || filter === 'all' || item.dataset.category === filter) ? '' : 'none';
      });
    });
  });

  // Lightbox
  const lightbox = document.querySelector('.lightbox');
  const lbImg = lightbox?.querySelector('img');
  let lbImages = [];
  let lbIndex = 0;

  document.querySelectorAll('.gallery-item').forEach((item, i) => {
    const img = item.querySelector('img');
    if (img) lbImages.push(img.src);
    item.addEventListener('click', () => {
      lbIndex = i;
      openLightbox();
    });
  });

  function openLightbox() {
    if (!lightbox || !lbImg) return;
    // Recount visible images
    const visibleItems = [...document.querySelectorAll('.gallery-item')].filter(i => i.style.display !== 'none');
    const visibleSrcs = visibleItems.map(i => i.querySelector('img')?.src).filter(Boolean);
    if (visibleSrcs.length === 0) return;
    lbImages = visibleSrcs;
    if (lbIndex >= lbImages.length) lbIndex = 0;
    lbImg.src = lbImages[lbIndex];
    lightbox.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  lightbox?.querySelector('.lightbox-close')?.addEventListener('click', closeLightbox);
  lightbox?.addEventListener('click', (e) => { if (e.target === lightbox) closeLightbox(); });

  function closeLightbox() {
    lightbox?.classList.remove('active');
    document.body.style.overflow = '';
  }

  lightbox?.querySelector('.lightbox-prev')?.addEventListener('click', (e) => {
    e.stopPropagation();
    lbIndex = (lbIndex - 1 + lbImages.length) % lbImages.length;
    if (lbImg) lbImg.src = lbImages[lbIndex];
  });
  lightbox?.querySelector('.lightbox-next')?.addEventListener('click', (e) => {
    e.stopPropagation();
    lbIndex = (lbIndex + 1) % lbImages.length;
    if (lbImg) lbImg.src = lbImages[lbIndex];
  });

  document.addEventListener('keydown', (e) => {
    if (!lightbox?.classList.contains('active')) return;
    if (e.key === 'Escape') closeLightbox();
    if (e.key === 'ArrowLeft') lightbox.querySelector('.lightbox-prev')?.click();
    if (e.key === 'ArrowRight') lightbox.querySelector('.lightbox-next')?.click();
  });
});

// ===== Fence Configurator Calculator =====
function calculateFence() {
  const height = parseFloat(document.getElementById('fence-height')?.value) || 2.0;
  const length = parseFloat(document.getElementById('fence-length')?.value) || 10;
  const bayWidth = parseFloat(document.getElementById('bay-width')?.value) || 2.0;
  const gates = parseInt(document.getElementById('gate-count')?.value) || 0;
  const series = document.getElementById('fence-series')?.value || 'coex';

  const bays = Math.ceil(length / bayWidth);
  const posts = bays + 1;
  const boardsPerBay = height <= 2.0 ? 13 : 20;
  const totalBoards = bays * boardsPerBay;

  // Pricing
  let pricePerBay;
  if (height <= 2.0) {
    pricePerBay = series === 'coex' ? 6500 : 5500;
  } else {
    pricePerBay = series === 'coex' ? 13000 : 11000;
  }
  const gatePrice = 15000;
  const totalPrice = (bays * pricePerBay) + (gates * gatePrice);
  const pricePerMeter = Math.round(totalPrice / length);

  // Update results
  const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  set('result-bays', bays);
  set('result-posts', posts);
  set('result-boards', totalBoards);
  set('result-gates', gates);
  set('result-length', length + 'm');
  set('result-height', height + 'm');
  set('result-total', '฿' + totalPrice.toLocaleString());
  set('result-per-meter', '฿' + pricePerMeter.toLocaleString() + '/m');

  const resultEl = document.querySelector('.config-result');
  if (resultEl) resultEl.style.display = 'block';
}

// ===== Smooth scroll for anchor links =====
document.addEventListener('click', (e) => {
  const link = e.target.closest('a[href^="#"]');
  if (!link) return;
  const target = document.querySelector(link.getAttribute('href'));
  if (target) {
    e.preventDefault();
    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
});
