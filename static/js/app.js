document.addEventListener('DOMContentLoaded', () => {
  const loader = document.getElementById('page-loader');
  window.setTimeout(() => loader?.classList.add('hidden'), 420);

  document.querySelectorAll('.message button').forEach(button => {
    button.addEventListener('click', () => button.closest('.message')?.remove());
  });
  window.setTimeout(() => document.querySelectorAll('.message').forEach(x => x.remove()), 5200);

  const revealItems = document.querySelectorAll('.reveal:not(.visible)');
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });
    revealItems.forEach(el => observer.observe(el));
  } else {
    revealItems.forEach(el => el.classList.add('visible'));
  }

  const menu = document.querySelector('.menu-toggle');
  const nav = document.querySelector('.main-nav');
  menu?.addEventListener('click', () => {
    const open = nav?.classList.toggle('open');
    menu.setAttribute('aria-expanded', String(Boolean(open)));
  });

  document.querySelectorAll('[data-step]').forEach(button => {
    button.addEventListener('click', () => {
      const input = button.parentElement?.querySelector('input');
      if (!input) return;
      const step = Number(button.dataset.step || 0);
      const min = Number(input.min || 1);
      const max = Number(input.max || 999);
      const current = Number(input.value || min);
      input.value = Math.max(min, Math.min(max, current + step));
    });
  });

  document.querySelectorAll('[data-wishlist]').forEach(button => {
    button.addEventListener('click', async event => {
      event.preventDefault();
      const id = button.dataset.wishlist;
      try {
        const response = await fetch(`/wishlist/toggle/${id}/`, {
          method: 'POST',
          headers: { 'X-CSRFToken': getCookie('csrftoken'), 'X-Requested-With': 'XMLHttpRequest' }
        });
        if (response.status === 403) { window.location.href = '/login/'; return; }
        const data = await response.json();
        button.textContent = data.added ? '♥ Save' : '♡ Save';
        button.classList.toggle('saved', data.added);
        toast(data.message);
      } catch {
        toast('Please sign in to save this weave.', 'error');
      }
    });
  });

  document.querySelectorAll('form[data-confirm]').forEach(form => {
    form.addEventListener('submit', event => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  const salesCanvas = document.getElementById('salesChart');
  if (salesCanvas && window.salesData) drawSalesChart(salesCanvas, window.salesData);
  if (window.bestData) renderBestSellers(window.bestData);
});

function getCookie(name) {
  return document.cookie.split('; ').find(row => row.startsWith(`${name}=`))?.split('=').slice(1).join('=') || '';
}

function drawSalesChart(canvas, data) {
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const width = canvas.clientWidth || 700;
  const height = 170;
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, width, height);
  const values = data.map(item => Number(item.total) || 0);
  const max = Math.max(...values, 1);
  const pad = { left: 10, right: 10, top: 18, bottom: 22 };
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;

  ctx.strokeStyle = '#e2ddd2'; ctx.lineWidth = 1;
  [0, .5, 1].forEach(ratio => {
    const y = pad.top + innerH * (1 - ratio);
    ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(width - pad.right, y); ctx.stroke();
  });
  if (!values.length) return;

  const points = values.map((value, i) => ({
    x: pad.left + (innerW * i / Math.max(values.length - 1, 1)),
    y: pad.top + innerH * (1 - value / max)
  }));
  ctx.beginPath();
  points.forEach((point, i) => i ? ctx.lineTo(point.x, point.y) : ctx.moveTo(point.x, point.y));
  ctx.strokeStyle = '#657458'; ctx.lineWidth = 3; ctx.lineJoin = 'round'; ctx.lineCap = 'round'; ctx.stroke();
  points.forEach(point => { ctx.beginPath(); ctx.arc(point.x, point.y, 3.5, 0, Math.PI * 2); ctx.fillStyle = '#d3b36a'; ctx.fill(); });
}

function renderBestSellers(data) {
  const target = document.getElementById('best-list');
  if (!target) return;
  target.innerHTML = data.map((item, index) => `
    <div class="admin-row">
      <div><b>${index + 1}. ${escapeHtml(item.product_name)}</b><small>Units sold</small></div>
      <strong>${Number(item.units) || 0}</strong>
    </div>`).join('') || '<p class="muted">Sales data will appear after orders.</p>';
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, char => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', "'":'&#39;', '"':'&quot;' }[char]));
}

function toast(text, type = 'success') {
  let box = document.querySelector('.messages');
  if (!box) { box = document.createElement('div'); box.className = 'messages'; document.body.appendChild(box); }
  const item = document.createElement('div');
  item.className = `message ${type}`;
  item.innerHTML = `<span>${escapeHtml(text)}</span><button type="button" aria-label="Dismiss">×</button>`;
  box.appendChild(item);
  item.querySelector('button').addEventListener('click', () => item.remove());
  window.setTimeout(() => item.remove(), 4000);
}
