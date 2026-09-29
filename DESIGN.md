# Alba design

This file sets how Alba looks and moves on screen. It governs the `web/` app (the six routes in `ARCHITECTURE.md`, "Auth and screens"), `mocks/index.html`, and `diagrams/c4.html`. It does not decide outcomes, states, fields, or the wording that templates own.

`ARCHITECTURE.md` wins over this file. `AGENTS.md` ("Data fetching and UI") binds every screen. If a pattern here needs a field the API does not return, the pattern waits: it is listed under **Open**, and nobody builds around it.

Decided with Jael on Sep 28, 2026:

- Glass for the conversation, paper for the record (see Principle 1).
- One sans family. Georgia is dropped from every surface.
- This file also governs `diagrams/c4.html`.
- The product web ships light only for the Oct 5 demo. `diagrams/c4.html` keeps the dark token set it already has.

## Sources

Frames were pulled from the videos locally for review. No asset from the Dribbble shots enters the repo: we take patterns, not images.

| Source | Taken | Left out |
|---|---|---|
| `mocks/index.html` (Sep 28) | Warm paper palette, green brand, uppercase kickers, the screen list, the Spanish labels | Georgia headings; raw state names on customer screens |
| `diagrams/c4.html` (Sep 28) | Tone set (green, amber, clay, slate), pills with a border, the colored left rule on spec cards, focus outline, reduced-motion handling, its dark set | Georgia headings |
| [AI Phone OS thinking mode](https://dribbble.com/shots/27637405-AI-Phone-OS-thinking-mode), Gleb Kuznetsov (Milkinside), video 50 s | Cards joined by thin connectors; a one-line status under a waiting mark; `--indigo` and `--haze` from the shot's palette (`#2F3954`, `#C7D1DF`) | The visible reasoning; photographs; generated widgets |
| [Wirely](https://dribbble.com/shots/26277782-Wirely-cloud-based-Fintech-SaaS-platform), Linkup ST, 8 stills | Smaller decimals on large amounts; tabular figures; the "details preserved as of creation" notice; review before confirm; a sticky summary panel on the right; a status pill with a check | Gauges and spending charts; side navigation; avatars |
| [GPT4 Chat OS Imagica](https://dribbble.com/shots/20904966-GPT4-Chat-OS-for-mobile-Imagica), Gleb Kuznetsov (Milkinside), video 42 s | The composer as one pill with the assistant mark; question chips | Image cards; pin and edit menus |
| [Natural Phone Home screen](https://dribbble.com/shots/25098782-Natural-Phone-Home-screen-design), Gleb Kuznetsov (Milkinside), video 28 s | A short action list with a count badge; the soft glow under the composer | Voice and camera input; weather and clock widgets |
| [Natural AI Phone launcher](https://dribbble.com/shots/24397341-Natural-AI-Phone-launcher), Gleb Kuznetsov (Milkinside), video 35 s | A centered waiting line over a quiet gradient; a row whose status changes in place | The dock; 3D objects |
| [Gen UI for AI phone OS launcher](https://dribbble.com/shots/27652758-Gen-UI-for-AI-phone-OS-launcher-by-Milkinside), Gleb Kuznetsov (Milkinside), video 36 s | A bottom sheet of chevron rows; a result card followed by next-step rows; dark circular send button; the cool surface range that `--mist-*` and `--lilac` are set from (frames sampled between `#CCD2DC` and `#E7E9ED`, lilac near `#DDCEDB`) | The "Low risk" badge; the reasoning paragraph; the stop button; context counters |

## Principles

1. **Glass is the conversation; paper is the record.** What the customer types or the assistant drafts sits on frosted glass over the mist background. What the policy decided, a template wrote, the file holds, or an event recorded sits on opaque paper: the certificate, template messages, product cards, the handoff packet, the trace, the C4 page. The surface tells the reader whether a line is a draft or a fact. The mock says it in one line: "El texto del modelo no es el expediente."
2. **Render typed fields, never prose.** Surface, tone, and label come from `messages.author`, `outcome`, `processes.state`, `reason_code`, and the product keys. Each map from a field to a look is defined once, next to the constants. A screen never matches a Spanish sentence to pick a style.
3. **Show steps, not thoughts.** The reference shots show the model reasoning while it works. Alba does not: the brief asks for explanations from sources, rules, and execution records, with no chain-of-thought (`PLAN.md` §2). While Alba works, the screen shows a mark and one neutral line. Afterwards the certificate shows facts and the deciding rule, and the agent sees the events.
4. **Ask only what the contract asks.** The customer can be asked which product and their monthly income (`ARCHITECTURE.md`, "What the customer can be asked"). No generated "what next" list, and no offer the system cannot keep: no limit, no rate for the new product, no account opening.
5. **Every outcome is calm.** `NOT_PREQUALIFIED` is a result, not an error. It uses the same card and the same motion as `PREQUALIFIED`, in a different tone. The word "simulado" is on every certificate tag.
6. **Amounts carry their currency code.** `1,559.57 USD`, never `$1,559.57`: MXN, ARS, COP, and USD all write `$`. The amount shows in the currency the API returns.

## Color

`web/` keeps these values in one tokens stylesheet under `web/src/`. Screens use the variables, never the hex.

### Mist: the conversation layer

| Token | Value | Use |
|---|---|---|
| `--mist-0` | `#F2F4F8` | Page, top of the gradient |
| `--mist-1` | `#E4E8F0` | Page, bottom of the gradient |
| `--lilac` | `#DDD6E8` | Radial glow, top right |
| `--haze` | `#C7D1DF` | Radial glow, bottom left |
| `--glass` | `rgba(255, 255, 255, 0.55)` with `backdrop-filter: blur(24px) saturate(1.2)` | Assistant bubbles, composer, sheets |
| `--glass-edge` | `rgba(255, 255, 255, 0.7)` | 1px inner edge on glass |
| `--glass-shadow` | `0 8px 32px rgba(47, 57, 84, 0.12)` | Shadow under glass |
| `--field-edge-cool` | `#7F869A` | Composer outline |
| `--ink-cool` | `#1C1F2A` | Text on mist and glass |
| `--muted-cool` | `#545A6B` | Secondary text on mist and glass |
| `--indigo` | `#2F3954` | Send button, focus ring on glass |
| `--indigo-8` | `rgba(47, 57, 84, 0.08)` | Customer bubble tint |

The page background is `linear-gradient(180deg, var(--mist-0), var(--mist-1))` with the two radial glows at 40% opacity or less. It does not move. The rainbow light in the shots comes from the 3D render set, not from the interface, and is not copied.

### Paper: the record layer

| Token | Value | Use |
|---|---|---|
| `--bg` | `#E7E1D6` | Page on agent screens and the C4 page |
| `--paper` | `#F3EFE7` | Raised sections, inactive rows |
| `--card` | `#FBF8F3` | Certificate, packet, product cards, template messages, C4 boxes |
| `--line` | `#D9D1C3` | Dividers. Decorative only: never the sole edge of a control |
| `--field-edge` | `#857D70` | Input and secondary-button borders on paper |
| `--ink` | `#1C1915` | Text on paper |
| `--muted` | `#5E584F` | Secondary text on paper |
| `--green` | `#1E3D32` | Brand, primary button, focus ring on paper |
| `--arrow` | `#7B7368` | Connectors on the trace and the C4 page |

The mock's `--line #e3dcd0` and `--clay #7a4b32` give way to the C4 values above and below.

### Tones

A tone is a text color plus a soft fill. It always comes with a text label: color alone never carries meaning.

| Tone | Text | Fill | Used for |
|---|---|---|---|
| green | `#1E3D32` | `#E7F0EB` | `PREQUALIFIED`; C4 "Defined" |
| stop | `#6D3228` | `#F3E8E4` | `NOT_PREQUALIFIED`, and nothing else |
| clay | `#8A4F33` | `#F6E8DF` | `REFER`; `human_active`; C4 "To define" |
| amber | `#7A5D12` | `#F6EED6` | `NEEDS_INFO`; C4 "Partial" |
| slate | `#34506B` | `#E4ECF3` | `ai_active`; C4 research refs |
| ink | `#1C1915` | `#F3EFE7` | `ended`; errors |

Errors use ink, not stop. On an Alba screen, the stop tone means one thing: the policy or the agent said no.

C4 box kinds keep their colors: person `#241F1B`, system `#1E3D32`, external `#6F675E`, highlighted link `#8A4F33`.

## Type

One sans family for every surface, plus a mono for identifiers.

```css
--font-sans: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
--font-mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
```

`web/` serves Inter from its own build, so no page calls a third-party font host. `mocks/index.html` and `diagrams/c4.html` are single static files and use the stack as written: Inter if installed, the system face otherwise.

Mono is for identifiers only: `customer_id`, rule ids, event names, state names, the policy version. It appears on agent screens, the trace, and the C4 page. Customer screens show no mono.

| Role | Size / line | Weight | Tracking | Where |
|---|---|---|---|---|
| display | 40 / 44 | 300 | -0.02em | Home greeting, login title |
| title | 28 / 34 | 400 | -0.01em | Screen titles, certificate product |
| heading | 20 / 26 | 500 | 0 | Card titles, packet sections |
| body | 16 / 24 | 400 | 0 | Messages, paragraphs |
| label | 14 / 20 | 500 | 0 | Buttons, rows, key-value keys |
| caption | 13 / 18 | 400 | 0 | Meta lines, notes, footers |
| kicker | 12 / 16 | 500 | 0.12em, uppercase | Section kickers |
| amount | 32 / 36 | 300 | -0.01em | Balances. Decimals and code at 0.6em, weight 400 |

- Weight 300 only at 28px and above.
- Nothing below 12px. When the C4 page is restyled, its 10.5px and 11px labels move to 12px.
- `font-variant-numeric: tabular-nums` on amounts, tables, codes, and timers.
- One number format everywhere, as the contract and the mock write it: comma thousands, dot decimals, two decimals on money, the code after a space (`306,753.45 MXN`). Scores are integers. Dates are written out in Spanish (`17 de junio de 2026`).

## Space, shape, elevation

- Spacing steps: 4, 8, 12, 16, 20, 24, 32, 40, 56 px. Side gutter: 16px on phones, 24px on desktop.
- Radii:

| Token | Value | Use |
|---|---|---|
| `--r-sheet` | 28px | Bottom sheets, full panels |
| `--r-card` | 20px | Cards, bubbles, the packet, C4 panes |
| `--r-row` | 14px | List rows, C4 boxes |
| `--r-field` | 12px | Inputs |
| `--r-pill` | 999px | Buttons, tags, the composer |

- A bubble has `--r-card` corners except a 6px corner on the author's side, at the bottom.
- **Glass floats; paper lies flat.** Glass gets the blur, `--glass-shadow`, and the 1px `--glass-edge`. Paper gets a 1px `--line` border and no shadow. The one shadow on paper is hover and focus on something clickable (as C4 boxes do today).

## Layout

- **Customer** (`/login`, `/`, `/case/:id`): mist background, one centered column, 640px max. On `/case/:id` the composer is docked to the bottom of the column, above the safe area. Phone first, like the reference shots.
- **Agent** (`/agent`, `/agent/case/:id`, `/agent/case/:id/trace`): `--bg` background, desktop first, 1200px max. `/agent/case/:id` has two columns, thread 1.15fr and packet 0.85fr (from the mock), with the packet sticky on the right. Below 1024px the columns stack with the packet first, because the packet is what the agent decides on.
- **C4 page**: keeps its layout (canvas plus a 350px side panel, one column below 1180px) and takes its tokens from this file.

## Components

### Composer (`/case/:id`)

- A glass pill, 56px tall, 1px `--field-edge-cool` outline, a text field, and a 44px circular send button in `--indigo` with a white arrow.
- No attach, microphone, or camera button: Alba has none of those inputs.
- A faint lilac-to-haze glow sits under the pill while it has focus.
- States: empty (send disabled); ready; sending (spinner in the button, field read-only until the API accepts); error (one line under the pill, the text kept, a retry).
- Enter sends. Shift+Enter adds a line.
- In `human_active` the composer stays, because the customer may still write and the message is stored (`ARCHITECTURE.md`, "Process"). A paper banner above it reads "Este caso lo ve una persona." No waiting mark shows, because the model is not called.
- In `ended` the certificate sits above the composer. A new message opens a new case (`ARCHITECTURE.md`, "Process").

### Messages (`/case/:id`; read-only on `/agent/case/:id`)

The surface follows `messages.author`:

| `author` | Side | Surface | Kicker |
|---|---|---|---|
| `customer` | Right | Glass tinted with `--indigo-8` | The customer's first name |
| `assistant` | Left | Clear glass | Alba |
| `template` | Left | Paper, 1px `--line` | Alba |

- Bubbles are 520px wide at most.
- The thread carries `lang="pt"` when the process `language` is `pt`.
- A new message fades in and rises 8px over `--t-enter`. The thread is a polite live region.
- The screen renders `messages` rows only. A turn whose `reply_ok` is false never reaches it (`ARCHITECTURE.md`, "Events").

### Waiting mark (`/case/:id`)

- Shown when the process is `ai_active` and the newest message is the customer's. Nowhere else.
- A 28px orb (radial blend of `--lilac`, `--haze`, and `--indigo` at low alpha) whose hue turns once every `--t-orb`, and one line in `--muted-cool`: "Alba está revisando tu mensaje." It sits in the thread where the next Alba message will appear.
- Never shown with it: reasoning text, a list of steps, a percentage, streamed tokens, or a stop button. Alba cannot cancel a command, so a stop button would lie.

### Product rows (`/`, and `/case/:id` while the thread is empty)

- A glass sheet with two chevron rows, one per product key: `credit_card` "Tarjeta de crédito", `personal_loan` "Préstamo personal".
- Choosing a row sends a customer message through the same endpoint as typing ("Quiero una tarjeta de crédito"). It does not set `product` on the process: the classified turn does.
- After `which_product` has been sent, the rows would need a typed field the API does not return yet. Until then the customer types the answer. See **Open**.

### Certificate (`/case/:id`)

A certificate exists only for `PREQUALIFIED` and `NOT_PREQUALIFIED` (from the policy, or from the agent close). It is paper, the full column width, `--r-card`, with a 6px left rule in the outcome tone (the C4 spec card). From top to bottom:

1. The outcome tag: "Precalifica · simulado" or "No precalifica · simulado".
2. The product, in title size.
3. The template paragraph, exactly as the API returns it.
4. "Hechos usados": key-value rows from `facts`. Income shows the local amount, the USD equivalent, and the exchange-rate date beside it (`ARCHITECTURE.md`, "Auth and screens").
5. "Regla que decide": the `deciding_rule` row.
6. A caption footer with `policy_version` and the dates of the facts, the way Wirely states that details are kept as of creation. When `decided_by` is `agent`, the footer adds "Revisado por una persona."

There is no slot for a credit limit, a rate for the new product, or a risk label. The Gen UI "Low risk" badge has no counterpart here (`PLAN.md` D4 is open). The card enters once over `--t-sheet`, with the same motion for both outcomes.

### Tags

A pill with a 1px border in the tone, the soft fill, and tone text at 12/16, weight 500 (the C4 `.pill`). The label is always present.

### Buttons

| Kind | Look | Use |
|---|---|---|
| Primary | `--green` fill, white text, pill | "Abrir sesión", "Volver a entrar" |
| Decisive | `--ink` fill, white text, pill | "Confirmar" in the agent confirm sheet |
| Secondary | No fill, 1px `--field-edge`, ink text, pill | "Precalificar", "No precalificar", "Elegir al azar", "Volver" |
| Send | 44px circle, `--indigo`, white icon | Composer |

- Every target is at least 44 by 44 px.
- Focus: 2px outline, offset 2px, `--green` on paper and `--indigo` on glass.
- Press: scale 0.98 over `--t-press`. Disabled: 45% opacity, not clickable.

### Fields

- White fill, 1px `--field-edge`, `--r-field`, 16px text (smaller text makes iOS zoom), label above in caption and `--muted`.
- The code field is one input: `inputmode="numeric"`, `autocomplete="one-time-code"`, tabular figures, 0.3em letter spacing.

### Login (`/login`)

- Mist background with paper cards, since the search results are rows from the file.
- A two-way switch, "Cliente" and "Agente", picks whether the search covers customers or agents (`POST /session/code` or `POST /agent/session`).
- A search field, then result rows: name, city, segment, masked document (the mock). "Elegir al azar" asks the API for a random row (`random=true`).
- The code card: masked email, code field, "Abrir sesión". A caption says the code lasts ten minutes (`ARCHITECTURE.md`, "Auth and screens").
- The test inbox shows only when the API returns the code (`DEMO_INBOX=1`). It has a dashed 1px `--field-edge` border and the kicker "Buzón de prueba", so nobody reads it as a bank feature.

### Home (`/`)

- A greeting in display size with the customer's first name, then the product cards, in the order the API returns them.
- A product card is paper. Kicker: product type and masked number ("Cuenta de ahorro · ••••5725"). Then the amount in amount size with its code, then a meta line (status, rate, days past due).
- A masked number reads to screen readers as "terminada en 5725".
- The product rows follow the cards.

### Session ended, loading, errors

- An expired session (401) replaces the screen with a paper card: "Tu sesión terminó", a caption, and "Volver a entrar". Nothing renews it silently (`ARCHITECTURE.md`, "Auth and screens").
- Every fetch has loading, error, and success (`AGENTS.md`).
- Loading: blocks in the target surface with a 1.2s opacity pulse, static under reduced motion.
- Error: a paper card in ink, the API's reason when it sends one, and "Reintentar".

### Agent queue (`/agent`)

- Header: the agent's name, specialty, and employee id in the kicker (the mock). The case count sits in a small ink badge beside the title.
- Rows are paper, `--r-row`: the customer's name at label weight 600; a caption with city, product, rule, and state (identifiers in mono); a clay "En revisión" tag; a chevron. The whole row is the link to "Abrir expediente".
- Empty state: "No hay casos en revisión."

### Agent case (`/agent/case/:id`)

- Left: the thread, read-only, as glass bubbles on a mist inset with `--r-card`. The conversation layer shows inside the record page. There is no composer, no reply box, and no text field (`ARCHITECTURE.md`, "Agent close").
- Right: the packet, paper, sticky, kicker "Paquete". Key-value rows from `analysis.completed`, in the mock's order: Pedido, Sesión, Score, Ingreso mensual, Ingreso en USD, Tarjeta activa, Regla, Política.
- Under the packet, two buttons of the same kind and size: "Precalificar", then "No precalificar". Neither takes focus on load and neither is tinted by outcome, so the layout does not lean toward an answer.
- Choosing one opens a confirm sheet, the review step Wirely shows before a payment. It names the outcome, says the customer gets a message and the case closes, and offers "Confirmar" (decisive) and "Volver".
- On success the case leaves the queue. A second close is rejected by the API (`agent_close:{process_id}`) and the screen shows that as an error.
- This confirm step is the agent's, not the customer consent that `PLAN.md` D8 asks about.

### Trace (`/agent/case/:id/trace`)

- Paper page, kicker "Registro". One card per event, in the order the API returns them: the event name in mono, the time, and the fields the rules match on. State changes show the state tag.
- A dashed 1.4px `--arrow` connector joins a card to the card named by its `caused_by_event_id`, the way the thinking-mode shot joins cards. No id, no line (`AGENTS.md`, "Events, rules, commands").

### C4 page

A record surface: paper tokens, the tones above, the box kinds above. When it is restyled, Georgia goes to the sans stack, labels under 12px go to 12px, and panes go to `--r-card`. It keeps its dark set and its layout.

### Mock

`mocks/index.html` follows this file when it is next edited. The dark rail at the top stays: it belongs to the walkthrough, not the bank (`README.md`). Raw identifiers such as `ai_active` belong in the walkthrough notes, not in the customer screen chrome.

## Motion

| Token | Value | Use |
|---|---|---|
| `--t-press` | 120ms | Button press |
| `--t-enter` | 200ms | Messages, rows, view changes |
| `--t-sheet` | 320ms | Sheets, the certificate |
| `--t-orb` | 4s, linear, loop | The waiting orb |
| `--ease` | `cubic-bezier(0.2, 0, 0, 1)` | Everything that is not a loop |

- Movement is 8px or less, except sheets.
- Only the orb and the loading pulse loop. No confetti or celebration on `PREQUALIFIED`.
- Under `prefers-reduced-motion: reduce`: fades only, 120ms at most, and the orb stands still.
- Under `prefers-reduced-transparency: reduce`, or without `backdrop-filter` support, glass becomes opaque `--mist-0` with the same edge.

## Accessibility

Contrast, WCAG 2.x formula, computed Sep 28, 2026 for the values in this file. Glass is measured as `--glass` composited over `--mist-1` (`#F3F5F8`) and over `--lilac` (`#F0EDF5`).

| Foreground | Background | Ratio | Needs |
|---|---|---|---|
| `--ink-cool` | `--mist-1` / glass over mist | 13.37 / 15.04 | 4.5 |
| `--muted-cool` | `--lilac` (lowest case) / `--mist-1` | 4.87 / 5.60 | 4.5 |
| white | `--indigo` / `--green` | 11.45 / 11.87 | 4.5 |
| `--ink` | `--bg` / `--card` | 13.46 / 16.53 | 4.5 |
| `--muted` | `--bg` / `--card` | 5.41 / 6.64 | 4.5 |
| Tone text | Its fill: green, stop, clay, amber, slate | 10.21, 8.18, 5.40, 5.33, 7.02 | 4.5 |
| `--field-edge` | `--card` / `--bg` | 3.84 / 3.12 | 3 |
| `--field-edge-cool` | Glass over mist | 3.33 | 3 |
| `--line` | `--card` | 1.43 | Decorative only |

- Tones always carry a text label.
- Focus is always visible (see Buttons).
- New messages and the waiting line are announced through a polite live region.
- The document is `lang="es"`. A Portuguese thread carries `lang="pt"`.

## Icons and imagery

- Inline SVG in a 20px box, 1.5px stroke, round caps, `currentColor`: send arrow, chevron, check, close, back, clock. No icon font and no icon package.
- The Alba mark is the orb, static at 20px, next to the "Alba" kicker.
- No photographs, avatars, or illustrations. The dataset has no images, so a face or a skyline would be made up.

## Interface copy

Interface labels are Spanish, as in the mock. Template sentences (`needs_income`, `refer_notice`, `which_product`, the agent-close message) are not in this file: they live in `api/policy/templates.py`, and `ARCHITECTURE.md` says they are not written yet.

Labels this file adds to the mock's: "Tarjeta de crédito", "Préstamo personal", "Quiero una tarjeta de crédito", "Alba está revisando tu mensaje.", "Revisado por una persona.", "Cliente", "Agente", "Elegir al azar", "Tu sesión terminó", "Volver a entrar", "Reintentar", "Confirmar", "Volver", "No hay casos en revisión.", "terminada en".

## Open

Each item needs a contract change before it is built. None is worked around in the meantime.

1. **Product rows after `which_product`.** The screen needs a typed field saying which template was sent last. A `messages` row has `author` and `body`, and no `template_id`.
2. **A countdown for the login code.** It needs the code's expiry in the `POST /session/code` response. Until then the caption states ten minutes.
3. **Naming the step in the waiting line.** It needs the pending command in the case response. Until then the line is fixed.
4. **Portuguese interface labels.** The contract localizes templates, not interface labels.
5. **How uncertainty shows on the certificate.** `PLAN.md` §2 marks it "Partial". This file gives the certificate no slot for it until that is decided.
6. **Customer consent before `policy.run`** (`PLAN.md` D8). If it is added, it uses the confirm sheet pattern with the primary button.

## Before a screen is called done

- Surface follows the source: glass for typed or drafted text, paper for decided or recorded facts.
- Colors, radii, and durations come from tokens. No raw hex in a component.
- Every fetch renders loading, error, and success.
- No raw state or event names on customer screens.
- Every tone has a text label. Every control has a visible focus ring and a 44px target.
- The screen is checked with reduced motion and reduced transparency on.
- No slot for a limit, a new-product rate, or a risk label.
