# Altru-Agent welcome artwork and login appearance

## Accepted behavior

Appearance settings select **None**, **Original logo**, or **Uploaded photo** (the intentional supplied `static/images/welcome-feast.png` asset, not an arbitrary upload endpoint). Original remains the default. None hides artwork only; text, suggestions and the composer are unchanged.

Photo targets are independent profile-owned settings: `welcome_artwork_height_desktop` (default 240) and `welcome_artwork_height_mobile` (default 160), bounded 64–600 CSS px. The mobile breakpoint is 768 CSS px, matching the app's mobile layout. Image height never derives from width. Preserve its natural aspect ratio, center horizontally, clip lateral overflow, and mask the container's outermost 18 px to alpha. Keep the supplied PNG bytes/transparency intact.

The height-only budget reserves 540 px for chrome, text, suggestions and the composer. Effective height is the saved target multiplied by `clamp((visualViewport.height - 540) / max(160, target), 0, 1)`. This deliberately conservative budget collapses artwork completely under severe height/keyboard constraints; it never changes saved values and restores them when space returns. Crossing the desktop/mobile breakpoint intentionally selects the other saved target. The baseline short-screen welcome content can still scroll; the composer stays separate.

Hydration does not save. Artwork writes contain only the changed key and use the existing settings FIFO. Profile-generation guards reject queued writes and ignore late responses after a switch. Backend validation uses the existing settings allowlist, enum and bounded-integer paths. No separate preference store is introduced.

## Saved halo and whole-group position

`welcome_logo_glow` defaults to true, preserving the original circular halo. The separate **Show logo glow** checkbox suppresses the actual `::before` pseudo-element (`content:none; display:none`) in both original and photo modes when false, without hiding the artwork. None mode suppresses both artwork and halo regardless of the saved toggle. The photo halo uses the existing theme-aware radial glow token behind the transparent artwork; it is not an opaque edge overlay.

`welcome_offset_desktop` and `welcome_offset_mobile` default to 0 CSS px and accept -300 through 300. Negative moves up, positive moves down. A single `.welcome-group` contains the selected artwork/logo, heading, descriptive paragraph and all three suggestion buttons. Apply one vertical transform to that wrapper, never the composer, header or sidebar. Zero retains centering when there is room.

Clamp the effective transform against the message viewport, visual viewport (including keyboard height/offset), and composer top, keeping an 8 px safety gap. Observe group/message size as well as window/visual-viewport resize; changes to text wrapping or chrome must re-evaluate the clamp. Saved offsets remain untouched and restore when there is space. Compact vertical padding/gaps on short screens, and preserve normal message scrolling if the content itself cannot fit; do not push an oversized group farther out of reach. Height still never derives from width.

All six artwork/halo/height/offset settings share the existing settings-file owner and one-field write path. This deliberately preserves current instance/profile-home settings ownership rather than introducing a new per-cookie store. A browser profile switch rehydrates that existing owner; guards prevent queued stale-profile writes or UI responses, not a migration of global appearance settings to a different storage model.

## Login

A blocking shared `appearance.js` resolver runs before CSS/paint on app and login pages. Login receives exactly two normalized allowlisted appearance attributes, theme and skin, from the existing settings owner; no general unauthenticated settings endpoint, settings blob, profile identifier or secret is added. Existing bot-name and locale rendering is unchanged.

Login uses the same stylesheet/palette tokens as the application, resolves Light/Dark/System with `matchMedia`, follows OS changes in System mode, and replaces stale browser appearance cache with the saved server selection. App-only extension skins remain app-only; unauthenticated login accepts built-in allowlisted palettes only. The current app boot/runtime extension handling remains intact.

Authentication, CSRF, password spaces, optional signed-in password reentry, OIDC and passkey flows are not changed. Existing session lifetime policy is preserved: password rotation changes accepted passwords but does not revoke all existing sessions; logout revokes its session.

## Verification boundary

Portable Chromium tests cover extracted real DOM/CSS plus a disposable loopback full HTTP handler using generated credentials and temporary application state. No runtime installs or production data are needed. Actual phone/keyboard, hardware passkey and external OIDC-provider certification remain separate. These commits do not authorize deployment, service restarts, publication or merge.
