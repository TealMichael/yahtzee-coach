# Ceremony validation

- All 15 protected gameplay, coaching, data, avatar, dependency, and policy files match 2K.14.8 byte-for-byte.
- App AST comparison: only render_yesterday_final_standings_if_needed changed; the version label also advances.
- Only app.py and retro_podium.py changed at runtime.
- Exact policy SHA-256: cdb704537146aed438cf7f6b8f8a9d6ec9ac5e97d505bd50af1702bb5935b39b
- Source legacy suite: 72/73 initially; the sole old visual-style assertion was updated for the approved dark stage and then passed. New ceremony regression passed.
- Packaged build: 74/74 regression suites pass, including exhaustive verification of all 3,669,120 legal hold values.
- Chromium browser checks pass at 320, 375, 390, and 720 pixels: section bounds do not overlap and no horizontal overflow. Four-second completion, Skip, tap, Escape, and reduced motion pass.
- Physical iPhone/Safari behavior has not been tested here. The headless environment lacks medal emoji glyphs; mobile operating systems supply their own emoji fonts.
- The browser-upload ZIP contains 33 files and exactly reproduces the full release when overlaid on 2K.14.8. Only two runtime files change.
- After packaged tests passed, only this validation document was finalized; all packaged executable and test files were checked byte-for-byte against that tested extraction.
