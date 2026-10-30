/* Saved profile-owned artwork. Hydration never writes preferences. */
(() => {
  'use strict';
  let saved = {}, ready = false;
  const generation = () => typeof _profileSwitchGeneration === 'undefined' ? 0 : _profileSwitchGeneration;
  let owner = generation();
  const label = (key,fallback) => typeof t === 'function' ? t(key) : fallback;
  const fields = {
    welcome_artwork: 'settingsWelcomeArtwork',
    welcome_logo_glow: 'settingsWelcomeLogoGlow',
    welcome_offset_desktop: 'settingsWelcomeOffsetDesktop',
    welcome_offset_mobile: 'settingsWelcomeOffsetMobile',
    welcome_artwork_height_desktop: 'settingsWelcomeHeightDesktop',
    welcome_artwork_height_mobile: 'settingsWelcomeHeightMobile'
  };
  function bounded(value, fallback, min = 64, max = 600) {
    return Number.isFinite(Number(value)) && Number(value) >= min && Number(value) <= max ? Math.round(Number(value)) : fallback;
  }
  function layout() {
    const host = document.getElementById('emptyState');
    const photo = host && host.querySelector('.welcome-photo');
    if (!photo) return;
    const target = matchMedia('(max-width: 768px)').matches ? saved.welcome_artwork_height_mobile : saved.welcome_artwork_height_desktop;
    // Height-only budget: horizontal resizing must never derive image height.
    // Reserve chrome, text/suggestions and composer; visualViewport covers keyboards.
    const viewport = window.visualViewport ? visualViewport.height : innerHeight;
    const ratio = Math.min(1, Math.max(0, (viewport - 540) / Math.max(160, target)));
    const height = target * ratio;
    photo.style.height = `${height}px`;
    const image = photo.querySelector('img');
    // Fade actual image edges when it fits, and clipping edges when it doesn't.
    // Width limits only the mask viewport; never derive the image height from it.
    photo.style.maxWidth = image.naturalWidth ? `${height * image.naturalWidth / image.naturalHeight}px` : '100%';
    const group = host.querySelector('.welcome-group');
    if (!group || !host.getClientRects().length) return;
    const rect = group.getBoundingClientRect();
    const previous = parseFloat(group.style.getPropertyValue('--welcome-offset')) || 0;
    const area = (host.closest('.messages') || host).getBoundingClientRect();
    const composer = document.querySelector('.composer-wrap');
    const viewportTop = window.visualViewport ? visualViewport.offsetTop : 0;
    const minimum = Math.max(area.top,viewportTop) + 8 - (rect.top - previous);
    const maximum = Math.min(area.bottom,composer ? composer.getBoundingClientRect().top : viewport + viewportTop,viewport + viewportTop) - 8 - (rect.bottom - previous);
    const wanted = matchMedia('(max-width: 768px)').matches ? saved.welcome_offset_mobile : saved.welcome_offset_desktop;
    // If content itself exceeds the available area, retain the normal scrollable
    // layout instead of pushing suggestions further outside its scroll viewport.
    const offset = minimum <= maximum ? Math.max(minimum,Math.min(maximum,wanted)) : 0;
    group.style.setProperty('--welcome-offset',`${offset}px`);
  }
  const observer = typeof ResizeObserver === 'function' ? new ResizeObserver(layout) : null;
  window.applyWelcomeArtwork = function(settings) {
    owner = generation();
    saved = {
      welcome_artwork: ['none','original','photo'].includes(settings.welcome_artwork) ? settings.welcome_artwork : 'original',
      welcome_logo_glow: settings.welcome_logo_glow !== false,
      welcome_offset_desktop: bounded(settings.welcome_offset_desktop,0,-300,300),
      welcome_offset_mobile: bounded(settings.welcome_offset_mobile,0,-300,300),
      welcome_artwork_height_desktop: bounded(settings.welcome_artwork_height_desktop,240),
      welcome_artwork_height_mobile: bounded(settings.welcome_artwork_height_mobile,160)
    };
    const host = document.getElementById('emptyState');
    if (host) {
      host.dataset.artwork = saved.welcome_artwork;
      host.dataset.logoGlow = String(saved.welcome_logo_glow);
      let group = host.querySelector('.welcome-group');
      if (!group) {
        group = document.createElement('div');
        group.className = 'welcome-group';
        while (host.firstChild) group.append(host.firstChild);
        host.append(group);
        if (observer) { observer.observe(group); observer.observe(host.closest('.messages') || host); }
      }
      if (!host.querySelector('.welcome-photo')) {
        const photo = document.createElement('div');
        photo.className = 'welcome-photo';
        const image = document.createElement('img');
        image.addEventListener('load',layout);
        image.src = 'static/images/welcome-feast.png';
        image.alt = '';
        photo.append(image);
        group.prepend(photo);
      }
    }
    for (const [key,id] of Object.entries(fields)) {
      const control = document.getElementById(id);
      if (control) { if(control.type === 'checkbox') control.checked = saved[key]; else control.value = saved[key]; control.disabled = false; }
    }
    ready = true;
    layout();
  };
  window.saveWelcomeArtwork = async function(control) {
    if (!ready || control.disabled || owner !== generation()) return;
    const requestOwner = generation();
    const key = Object.keys(fields).find(key => fields[key] === control.id);
    if (!key) return;
    const value = key === 'welcome_logo_glow' ? control.checked : key === 'welcome_artwork' ? control.value : Number(control.value);
    const isOffset = key.startsWith('welcome_offset_');
    if (key !== 'welcome_artwork' && key !== 'welcome_logo_glow' && (!Number.isInteger(value) || value < (isOffset ? -300 : 64) || value > (isOffset ? 300 : 600))) {
      control.reportValidity(); return;
    }
    control.disabled = true;
    try {
      // One changed field only, no broad appearance form defaults or debounce.
      const options = {method:'POST',body:JSON.stringify({[key]:value})};
      const result = typeof _enqueueSettingsPost === 'function' ? await _enqueueSettingsPost(options, requestOwner) : await api('/api/settings',options);
      if (requestOwner !== generation()) return;
      applyWelcomeArtwork(result);
      document.getElementById('welcomeArtworkStatus').textContent = label('settings_welcome_saved','Saved');
    } catch (error) {
      if (requestOwner !== generation()) return;
      control.disabled = false;
      document.getElementById('welcomeArtworkStatus').textContent = label('settings_welcome_failed','Save failed; retry your change.');
    }
  };
  window.addEventListener('resize', layout);
  if (window.visualViewport) {
    visualViewport.addEventListener('resize',layout);
    visualViewport.addEventListener('scroll',layout);
  }
})();
