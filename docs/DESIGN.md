# Design System Notes — OpenCode-Inspired

Inspected on 2026-11-24 via HTTP (`https://opencode.ai/`, `shell-D8x4Q6q5.css`,
`home-B2nwsUqQ.css`) and its Markdown source. Browser screenshot tooling was not
available during the initial reference inspection, so fidelity is based on the
shipped CSS tokens and rendered markup, not pixel screenshots. The implemented
app was later checked with Playwright at desktop, tablet, and mobile sizes; see
[`VERIFICATION.md`](VERIFICATION.md).

## Observed source tokens (dark theme)

| Token | OpenCode value | LYFTR usage |
|-------|----------------|-------------|
| Page background | `#0c0c0c` | `bg-canvas` |
| Raised surface | `#161616` | `bg-surface` |
| Recessed surface | `#1a1a1a` | `bg-surface-weak` |
| Strong surface | `#242424` | `bg-surface-strong` |
| Border | `#2e2e2e` | `border-line` |
| Strong border | `#4b4b4b` | `border-line-strong` |
| Text strong | `#fafafa` | `text-ink` |
| Text | `#aeaeae` | `text-body` |
| Text weak | `#8f8f8f` | `text-muted` |
| Text weaker | `#6a6a6a` | `text-faint` |
| Accent | `#6b8fff` | `accent` (links, focus, live) |
| Success | `#54d483` | cache-hit / healthy |
| Warning | `#f4b434` | degraded |
| Danger | `#ed5a5a` | errors |
| Type sans | Inter | Inter |
| Type mono | OpenTUI Mono | JetBrains Mono (open-source substitute) |
| Base font size | 15px | 15px |
| Meta font | 12–13px mono, uppercase, tracking ~0.08em | metadata labels |
| Radius | 3–8px (mostly square) | 2–6px |
| Sidebar | 236px (14.75rem) | 264px |
| Gutter / edge | 16px / 24px | same |
| Page max | 1728px | reading column max 860px |

## Transferable visual language

- Near-black canvas with hairline 1px separators; surfaces are only one or two
  steps lighter than the page.
- Mono is used for labels, indices, metadata and buttons; Inter for reading.
- Numbered navigation (`[01]`, `[02]`) and uppercase micro-labels create the
  developer-tool character.
- Buttons are compact (36–40px), square, and rely on borders, not shadows.
- Hover states are quiet: surface shift, text brightening, 2px accent rule.
- Large headlines use mono with tight letter-spacing; body copy is restrained.
- One accent color (blue) plus semantic green/amber/red. No gradients except
  very subtle radial atmosphere.
- Buttons and links use a 2px accent focus-visible outline with offset;
  textareas use a border shift.

## LYFTR adaptation

- Static in-flow left rail on desktop and an off-canvas slide-over with overlay
  on mobile, with brand block, numbered section links, session facts, system
  prompt, connection status and version. Mobile adds a top bar menu button.
- Chat is the primary canvas: max 860px reading column, generous vertical
  rhythm, and spacing between message groups.
- Assistant messages are not chat bubbles. They are document-like blocks with a
  mono speaker line, 2px accent rail for live inference and green rail for cache
  hits. User turns are compact raised panels aligned right.
- Metadata is a wrapping strip of `LABEL value` pairs in mono, separated by
  hairlines, with semantic source color. This mirrors OpenCode's spec-sheet
  aesthetic rather than SaaS pill clutter.
- Composer is a raised, bordered field pinned to the bottom of the chat column,
  with a mono header row (MESSAGE / character count), auto-growing textarea,
  compact send control, and a small failover/cache/memory caption. No floating
  rounded pill.
- Empty state reads like a product hero: eyebrow, mono headline, description,
  capability grid with numbered cells, and three example prompts.
- Motion is limited to 150–220ms fades/slides, typing cursor, and scroll
  behavior; respects `prefers-reduced-motion`.

## Branding

- Name: **LYFTR AI**
- Subtitle: **Reliable AI. Every Response.**
- Description: "An intelligent conversational AI powered by automatic model
  failover, response caching, and persistent conversation memory."
- No OpenCode names, copy, logos or assets are used.
