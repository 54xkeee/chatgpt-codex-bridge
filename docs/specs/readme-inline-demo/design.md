# README Inline Demo Design

## Decision

Reuse the exact `WIDGET_HTML` constant shipped by
`scripts/bridge/codex-mcp-guard.py`. Render it locally with a synthetic
`window.openai.toolOutput`, capture only the page viewport, and store the images
under `docs/assets/readme/`.

The default `README.md` will contain the complete Chinese guide first and keep
the concise English reference in a later section. `README.zh-CN.md` remains only
as a compatibility path; it is no longer the primary reading route.

## Screenshot states

1. `running`: synthetic background job with no user/account context.
2. `completed`: synthetic terminal result and explicit return button.
3. `interrupted`: synthetic recovery state showing the preserved local result.

Each image is a truthful rendering of the shipped component, not a generated or
edited product screenshot. A visible `DEMO / SYNTHETIC DATA` badge in the local
host page distinguishes it from a live ChatGPT capture.

## Failure and privacy controls

- Render from a temporary localhost page; never open an authenticated account.
- Use fixed identifiers such as `demo-job-0001` only.
- Capture the content viewport without browser chrome and keep the file extension
  consistent with the browser's emitted image format.
- Scan committed image metadata and OCR-visible companion strings before publish.
- Keep Mermaid only for optional architecture explanation, not as the requested
  product demonstration.

## Rollback

Revert the README/assets commit. No runtime, service, credential, or user data is
changed.
