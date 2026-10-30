/* Blocking shared app/login resolver; executes before the stylesheet/first paint. */
(() => {
  'use strict';
  const root = document.documentElement;
  const themes = new Set(['light','dark','system']);
  const skins = new Set(['codex','terracotta','default','ares','mono','graphite','github','slate','poseidon','sisyphus','charizard','sienna','catppuccin','hepburn','nous','geist-contrast','neon','neon-soft','neon-paint','zeus','verdigris']);
  const legacy = {slate:['dark','slate'],solarized:['dark','poseidon'],monokai:['dark','sisyphus'],nord:['dark','slate'],oled:['dark','default']};
  window.resolveApplicationAppearance = (theme, skin) => {
    theme = typeof theme === 'string' ? theme.trim().toLowerCase() : '';
    skin = typeof skin === 'string' ? skin.trim().toLowerCase() : '';
    const migrated = legacy[theme];
    return {theme:migrated ? migrated[0] : themes.has(theme) ? theme : 'dark',skin:skins.has(skin) ? skin : migrated ? migrated[1] : 'default'};
  };
  const authoritative = root.hasAttribute('data-appearance-theme');
  let theme = root.dataset.appearanceTheme, skin = root.dataset.appearanceSkin;
  try {
    if (!authoritative) { theme = localStorage.getItem('hermes-theme'); skin = localStorage.getItem('hermes-skin'); }
  } catch (_) {}
  const appearance = resolveApplicationAppearance(theme,skin);
  // A trusted installed extension can register its cached skin later on the app.
  if (!authoritative && skin && /^[a-z0-9-]+$/.test(skin) && !skins.has(skin) && !legacy[skin]) appearance.skin = skin;
  const media = matchMedia('(prefers-color-scheme: dark)');
  function apply() {
    root.classList.toggle('dark',appearance.theme === 'dark' || appearance.theme === 'system' && media.matches);
    if (appearance.skin === 'default') delete root.dataset.skin;
    else root.dataset.skin = appearance.skin;
    root.style.colorScheme = root.classList.contains('dark') ? 'dark' : 'light';
  }
  apply();
  if (authoritative) {
    try { localStorage.setItem('hermes-theme',appearance.theme); localStorage.setItem('hermes-skin',appearance.skin); } catch (_) {}
    media.addEventListener('change',apply);
  }
})();
