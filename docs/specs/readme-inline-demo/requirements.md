# README Inline Demo Requirements

## Goal

Make the default GitHub README directly useful to Chinese readers and replace
abstract workflow diagrams with reproducible, privacy-safe page screenshots.

## Requirements

- **RID-001**: The repository `README.md` MUST present the Chinese operator
  guide inline before the English reference text; it MUST NOT require opening a
  second README to understand installation, operation, recovery, or pitfalls.
- **RID-002**: The README MUST include page screenshots rendered from the
  shipped MCP Apps widget code with synthetic project/job data only.
- **RID-003**: Screenshot captions MUST disclose that the page code is real and
  the displayed identifiers/content are synthetic demonstration data.
- **RID-004**: Screenshots and README text MUST NOT contain personal account
  names, real paths, device names, Tunnel profiles, conversation/thread/job IDs,
  browser chrome, bookmarks, notifications, or credentials.
- **RID-005**: The existing English introduction MUST remain available in the
  same `README.md` after the Chinese guide.

## Acceptance

Given an anonymous visitor opens the repository root, when GitHub renders
`README.md`, then the visitor can read the Chinese guide and view running,
completed, and recovery page states without opening another language file or
being exposed to private data.

## Non-goals

- Publishing screenshots of a real signed-in ChatGPT or Codex account.
- Claiming that the local demonstration shell is the ChatGPT product chrome.
- Changing Bridge runtime behavior.
