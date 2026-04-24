/* ============================================
   PANPRUKSA — Main JavaScript
   ============================================ */

// --- Navigation Toggle ---
const navToggle = document.getElementById('navToggle');
const navOverlay = document.getElementById('navOverlay');
const header = document.getElementById('header');

if (navToggle) {
  navToggle.addEventListener('click', () => {
    document.body.classList.toggle('nav-open');
  });
}

// Close nav on link click
document.querySelectorAll('.nav-menu a').forEach(link => {
  link.addEventListener('click', () => {
    document.body.classList.remove('nav-open');
  });
});

// --- Header Scroll Behavior ---
let lastScroll = 0;
const heroEl = document.querySelector('.hero');

window.addEventListener('scroll', () => {
  const scrollY = window.scrollY;

  // Scrolled state
  if (scrollY > 80) {
    header.classList.add('scrolled');
  } else {
    header.classList.remove('scrolled');
  }

  // Hero visible state (white logo/menu)
  if (heroEl) {
    const heroBottom = heroEl.offsetHeight - 100;
    if (scrollY < heroBottom) {
      header.classList.add('hero-visible');
    } else {
      header.classList.remove('hero-visible');
    }
  }

  lastScroll = scrollY;
});

// --- Scroll Animations (Intersection Observer) ---
// Add js-loaded class to enable animations only after observer is set up
document.documentElement.classList.add('js-loaded');

const observerOptions = {
  threshold: 0.05,
  rootMargin: '0px 0px 0px 0px'
};

const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      observer.unobserve(entry.target);
    }
  });
}, observerOptions);

document.querySelectorAll('.fade-up').forEach(el => observer.observe(el));

// Fallback: make everything visible after 2s if observer didn't fire
setTimeout(() => {
  document.querySelectorAll('.fade-up:not(.visible)').forEach(el => {
    el.classList.add('visible');
  });
}, 2000);

// --- Contact Form → Slack Webhook ---
const contactForm = document.getElementById('contactForm');
const formStatus = document.getElementById('formStatus');

if (contactForm) {
  contactForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = new FormData(contactForm);
    const data = Object.fromEntries(formData);

    // Update button state
    const submitBtn = contactForm.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'SENDING...';
    submitBtn.disabled = true;

    try {
      // Post to Slack webhook
      const slackPayload = {
        text: `:house: *New Panpruksa Lead*\n\n*Name:* ${data.name}\n*Email:* ${data.email}\n*Phone:* ${data.phone || 'Not provided'}\n*Company:* ${data.company || 'Not provided'}\n*Country:* ${data.country}\n*Message:* ${data.message}`
      };

      // Webhook URL loaded from data attribute on form element
      const webhookUrl = contactForm.dataset.webhook || '';
      const response = await fetch(webhookUrl, {
        method: 'POST',
        mode: 'no-cors',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(slackPayload)
      });

      // no-cors means we can't read the response, but if it doesn't throw, it worked
      formStatus.className = 'form-status success';
      formStatus.textContent = 'Thank you for your enquiry. We will be in touch shortly.';
      contactForm.reset();

    } catch (error) {
      formStatus.className = 'form-status error';
      formStatus.textContent = 'Something went wrong. Please email us at contact@panpruksa.com';
    }

    submitBtn.textContent = originalText;
    submitBtn.disabled = false;
  });
}
