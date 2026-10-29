# UI change log

This log tracks accepted fork changes. Keep it current with each related feature or fix, link the pull request or commit, and distinguish local verification from CI and deployed behavior. Do not add credentials, machine paths, private network details, user conversations, or deployment-only launchers. The release-maintained root CHANGELOG.md remains unchanged.

## Navigation and New chat

Tracking: [pull request #1](https://github.com/mygsunny/Altur-Agent-WebUI/pull/1), branch `ui/sidebar-new-chat`. Published as a reviewable feature branch; not merged into `altur-branding`. Local checks passed; GitHub reported no checks for the branch.

### Added
- A theme-aware **New chat** row immediately below conversation search and above date-grouped conversations, with the supplied rounded pencil-in-square icon.
- A matching compose action in the far-left navigation rail. It starts at the top by default, but is movable along with Chat and the ordinary navigation tabs.
- A global compose action that switches to Chat from other pages before invoking the existing new-conversation handler. Existing unsaved-settings guards and empty-chat/draft behavior remain in force.
- Long press for 500 ms to enter reorder mode, then drag an icon onto another icon to move it. Click outside or press Escape to finish.
- Keyboard reorder with Alt+ArrowUp and Alt+ArrowDown.
- Saved ordering through the existing per-profile tab_order setting and prepaint browser cache. Existing saved orders retain their prior placement unless changed.

### Final visual decisions
- New chat and Chat can both move. Settings stays at the bottom; the optional external dashboard retains its existing fixed placement.
- Reorder mode uses a visible nine-degree wiggle with slight horizontal movement. Each cycle lasts 280 ms, slowed from the initial stronger-wiggle implementation at the user's request.
- Respect reduced-motion preferences with a static outline instead of animation.
- The Chat panel header retains its original plus icon. The compose icon is in the far-left rail, not a replacement for the header plus.
- Existing theme colors, rounded controls and sidebar alignment are retained. Mobile sidebar action targets are at least 44 px high.

### Safety and regression fixes
- Persist only tab_order during rail reordering, not unhydrated appearance-form defaults.
- Queue order writes and wait for them before loading Settings, preventing immediate Settings navigation from restoring an older order.
- Retain Chat's always-visible protection independently of its new movable position.
- Suppress activation during a drag or long press, but restore normal clicks after Escape, pointer cancellation, window blur, or hiding the page.
- Version changed assets so refresh retrieves updated CSS and controller code without clearing browser storage.

### Verification
- `node tests/rail-reorder.browser.cjs`: Chromium DOM tests of compose navigation from Chat, Tasks, Settings, Skills, Memory and Kanban; long-press/drag for Chat and New chat; saved order restoration; click suppression and recovery; keyboard reordering; touch pointer cancellation; narrow settings writes; Settings hydration ordering; reduced-motion and light/dark presentation.
- `node tests/sidebar-new-chat.browser.cjs`: desktop and mobile-width alignment, minimum target sizes, and click/Enter/Space delegation in light and dark themes.
- Tests require an available Playwright installation with Chromium. They use normal `require('playwright')`; set PLAYWRIGHT_MODULE to a separately installed module location if needed. They run with disposable DOM state and blocked network requests, not a production account.
- Separately exercised actual settings save/load in a disposable application home, confirming movable Chat is preserved in tab_order while Chat/Settings cannot be hidden.
- Deployed source was read back over HTTP and compared with the tested files; health and login returned 200, unauthenticated protected session access returned 401.
- These are local checks, not a claim of GitHub CI, authenticated production browser automation, real backend chat creation, or physical touchscreen certification.

### Maintenance
- Continue this log for later changes, and publish the source, relevant tests and safe visual evidence together in feature commits and pull requests.
- Local installation migration, reversible backups, guarded launcher and password-management work have separate private deployment records; they are not part of the publishable application source in this change.

## Desktop conversation discovery and signed-in password changes

Tracking: branch `fix/desktop-session-discovery`, stacked on the navigation feature. Deployment is recorded separately; passing isolated checks does not imply the running service has reloaded.

### Fixed
- Recover user-visible Desktop, GUI and local conversations independently of the 20-session recent-agent feed. Busy delegated children no longer evict older standalone Desktop chats from discovery.
- Deduplicate recovery by conversation lineage. Keep profile scoping, project assignment, archived flags and explicit-session lookup narrowing intact.
- Exclude hidden and delegated rows from this recovery pass before selecting candidates. Keep background-source and ordinary CLI limits unchanged.
- Make current-password reentry optional for password changes from an existing authenticated login session, as requested by the owner. Login remains required; any supplied current password is still verified. Disabling authentication or switching to passwordless retains current-password verification. This intentionally changes the fork's prior reentry policy.
- Explain the optional field in Settings, including the stronger requirement for disabling authentication. Blank general settings saves still leave the password unchanged; password spaces remain significant.

### Local verification
- Seven disposable-SQLite discovery tests cover recent-child starvation, hidden/delegated/background exclusions, user forks, archive identity, explicit IDs, malformed metadata, legacy schemas and source filtering.
- Five policy tests exercise the actual settings-route guard and actual Settings save function, including unsigned refusal and the retained disable-authentication guard.
- Existing password-action and dialog tests were exercised with disposable DOM credentials; 25 cases passed. Both navigation browser suites, JavaScript syntax and whitespace checks also passed.
- An isolated loopback full-server test with generated fixture credentials returned 401 for unauthenticated protected access, 200 for a signed-in password rotation without reentry, 403 for disabling authentication without reentry, 401 for the old password and 200 for the new password. Authentication remained enabled.
- The same disposable server returned all four fixture Desktop roots despite 25 newer delegated children, and Chromium rendered all four roots visibly.
- These are local checks, not GitHub CI or a claim that a production password has been rotated.
