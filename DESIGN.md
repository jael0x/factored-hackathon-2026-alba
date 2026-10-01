# Alba design

This file sets how Alba looks and moves on screen. It governs the `web/` app (the routes in `ARCHITECTURE.md`, "Auth and screens"), `mocks/index.html`, and `diagrams/c4.html`. It does not decide outcomes, states, fields, or the wording that templates own.

`ARCHITECTURE.md` wins over this file. `AGENTS.md` ("Data fetching and UI") binds every screen. If a pattern here needs a field the API does not return, the pattern waits: it is listed under **Open**, and nobody builds around it.

Decided with Jael:

- Sep 28, 2026: glass for the conversation, a different surface for the record (Principle 1). One sans family; Georgia is dropped. This file also governs `diagrams/c4.html`. The product web ships light only for the Oct 5 demo; the C4 page keeps a dark set.
- Sep 30, 2026: the login is two columns (title, description, and the always-visible notice on the left; the form on the right), vertically centered. The demo search is a popover under a dashed "Demo" button in the app bar, hidden until pressed. The code step stacks its actions.
- Sep 29, 2026: no cream anywhere. Records are solid white, and the one key record per screen is a deep indigo panel. Glass sits over a blurred color field so the effect shows. Screens fill the browser like the real app; the mock's notes live in a drawer. Buttons stay forest green, so green means both "act" and "pre-qualifies".

## Sources

Frames were pulled from the videos locally for review. No asset from the Dribbble shots enters the repo: we take patterns, not images.

| Source | Taken | Left out |
|---|---|---|
| `mocks/index.html` (Sep 28) | Green brand, the screen list, the Spanish labels | The cream paper palette (dropped Sep 29); Georgia headings; raw state names on customer screens |
| `diagrams/c4.html` (Sep 28) | Tone set (green, amber, clay, slate), pills with a border, the colored left rule on spec cards, focus outline, reduced-motion handling, a dark set | Georgia headings; the warm palette in both sets |
| [AI Phone OS thinking mode](https://dribbble.com/shots/27637405-AI-Phone-OS-thinking-mode), Gleb Kuznetsov (Milkinside), video 50 s | Cards joined by thin connectors; a one-line status under a waiting mark; `--indigo` and `--haze` from the shot's palette (`#2F3954`, `#C7D1DF`) | The visible reasoning; photographs; generated widgets |
| [Wirely](https://dribbble.com/shots/26277782-Wirely-cloud-based-Fintech-SaaS-platform), Linkup ST, 8 stills | Smaller decimals on large amounts; tabular figures; the "details preserved as of creation" notice; review before confirm; the deep blue translucent panel for the key action; a slim sidebar app shell; white cards with soft shadows on a blurred field | Gauges and spending charts; avatars |
| [GPT4 Chat OS Imagica](https://dribbble.com/shots/20904966-GPT4-Chat-OS-for-mobile-Imagica), Gleb Kuznetsov (Milkinside), video 42 s | The composer as one pill with the assistant mark; question chips | Image cards; pin and edit menus |
| [Natural Phone Home screen](https://dribbble.com/shots/25098782-Natural-Phone-Home-screen-design), Gleb Kuznetsov (Milkinside), video 28 s | A short action list with a count badge; the soft glow under the composer | Voice and camera input; weather and clock widgets |
| [Natural AI Phone launcher](https://dribbble.com/shots/24397341-Natural-AI-Phone-launcher), Gleb Kuznetsov (Milkinside), video 35 s | A centered waiting line over a quiet gradient; a row whose status changes in place | The dock; 3D objects |
| [Gen UI for AI phone OS launcher](https://dribbble.com/shots/27652758-Gen-UI-for-AI-phone-OS-launcher-by-Milkinside), Gleb Kuznetsov (Milkinside), video 36 s | Glass over a soft, blurred indigo-silver field; a bottom sheet of chevron rows; a result card followed by next-step rows; the surface range the aurora is set from (frames sampled between `#CCD2DC` and `#E7E9ED`, lilac near `#DDCEDB`, palette `#374772`, `#576692`, `#C0C5D4`) | The "Low risk" badge; the reasoning paragraph; the stop button; context counters |

## Principles

1. **Glass is the conversation; solid is the record.** What the customer types or the assistant drafts sits on frosted glass. What the policy decided, a template wrote, the file holds, or an event recorded sits on an opaque white surface: template messages, product cards, the trace, the C4 page. The one record a screen exists for (the certificate for the customer, the packet for the agent) is a deep indigo panel. The surface tells the reader whether a line is a draft or a fact. The mock says it in one line: "El texto del modelo no es el expediente."
2. **Render typed fields, never prose.** Surface, tone, and label come from `messages.author`, `outcome`, `processes.state`, `reason_code`, and the product keys. Each map from a field to a look is defined once, next to the constants. A screen never matches a Spanish sentence to pick a style.
3. **Show steps, not thoughts.** The reference shots show the model reasoning while it works. Alba does not: the brief asks for explanations from sources, rules, and execution records, with no chain-of-thought (`PLAN.md` §2). While the client waits for the API, the thread shows the typing indicator the contract names, "escribiendo…" (`ARCHITECTURE.md`, "UI wait state"). Afterwards the certificate shows facts and the deciding rule, and the agent sees the events.
4. **Ask only what the contract asks.** The customer can be asked three things: which product, whether to start the pre-qualification, and their monthly income (`ARCHITECTURE.md`, "What the customer can be asked"). No generated "what next" list, and no offer the system cannot keep: no limit, no rate for the new product, no account opening.
5. **Every outcome is calm.** `NOT_PREQUALIFIED` is a result, not an error. It uses the same panel and the same motion as `PREQUALIFIED`, in a different tone. The word "simulado" is on every certificate tag.
6. **Amounts carry their currency code.** `1,559.57 USD`, never `$1,559.57`: MXN, ARS, COP, and USD all write `$`. The amount shows in the currency the API returns.

## Color

`web/` keeps these values in one tokens stylesheet under `web/src/`. Screens use the variables, never the hex. No surface is cream, beige, or warm paper.

### Aurora: the page

Every product screen sits on the aurora: a cool base gradient with large blurred color fields that give the glass something to blur.

| Token | Value | Use |
|---|---|---|
| `--aurora-base` | `linear-gradient(160deg, #EEF1F7, #E3E8F2 45%, #DCE1EE)` | The base |
| `--aurora-indigo` | `#6F7FB8` at 55% | Top-right field, the darkest |
| `--aurora-lilac` | `#D9CDEB` | Left field |
| `--aurora-ice` | `#BFD3EA` | Bottom-right field |
| `--aurora-rose` | `#EBD6E6` at 60% | Small top-left field |
| `--aurora-periwinkle` | `#788AC4` at 35% | Bottom-left field, under the composer |
| `--aurora-silk` | a diagonal band of `#374772` at 32% | One soft fold, like the Gen UI fabric |

- The fields are fixed to the viewport, blurred 60 to 90px, with a 3.5% grain overlay. They do not move.
- Text never sits on the bare aurora in `--muted`: it drops to 2.8:1 where the aurora is darkest. Text on the aurora is `--ink`, or it sits on glass or a solid surface.
- The rainbow light in the shots comes from the 3D render set, not from the interface, and is not copied.

### Glass: the conversation layer

| Token | Value | Use |
|---|---|---|
| `--glass` | `rgba(255, 255, 255, 0.55)` with `backdrop-filter: blur(28px) saturate(1.5)` | Assistant and customer bubbles, composer, sheets, app bar, sidebar, the agent's thread panel |
| `--glass-edge` | 1px `rgba(255, 255, 255, 0.65)` plus an inner top highlight `rgba(255, 255, 255, 0.8)` | Edge of every glass surface |
| `--glass-shadow` | `0 10px 40px rgba(37, 50, 86, 0.14), 0 1px 2px rgba(37, 50, 86, 0.06)` | Glass floats |
| `--field-edge-glass` | `#6B7286` | Composer outline |
| `--tint` | `rgba(55, 71, 114, 0.12)` over `--glass` | Customer bubble |

### Solid: the record layer

| Token | Value | Use |
|---|---|---|
| `--surface` | `#FFFFFF` | Template messages, product cards, result rows, the queue, trace cards, dialogs, the demo popover, the login notice, the session-ended card |
| `--surface-2` | `#F5F6FA` | Rows and insets inside a white surface |
| `--line` | `#DCE0E8` | Dividers. Decorative only: never the sole edge of a control |
| `--field-edge` | `#7F869A` | Input and secondary-button borders on white |
| `--solid-shadow` | `0 1px 2px rgba(37, 50, 86, 0.06), 0 8px 24px rgba(37, 50, 86, 0.08)` | Solid sits |
| `--ink` | `#1C1F2A` | All text on the aurora, glass, and white |
| `--muted` | `#4B5163` | Secondary text on glass and white |
| `--green` | `#1E3D32` | Brand, primary button, focus ring |
| `--indigo` | `#2F3954` | The orb, the aurora, the hero |
| `--arrow` | `#7F869A` | Connectors on the trace and the C4 page |

### Hero: the key record

| Token | Value | Use |
|---|---|---|
| `--hero` | `linear-gradient(150deg, #253256, #374772)` | The certificate, the agent packet |
| `--hero-ink` | `#FFFFFF` | Text |
| `--hero-muted` | `#C0C5D4` | Keys, captions |
| `--hero-line` | `rgba(255, 255, 255, 0.16)` | Row dividers |
| `--hero-edge` | `rgba(255, 255, 255, 0.55)` | Borders of controls on the hero |

The hero has a 1px `rgba(255, 255, 255, 0.18)` edge, a soft inner highlight at the top, and `--glass-shadow`. The focus ring on the hero is white.

### Tones

A tone is a text color and a border. It always comes with a text label: color alone never carries meaning. On white and glass a tag has a white fill; on the hero it has no fill and uses the light variant.

| Tone | On white and glass | On the hero | Used for |
|---|---|---|---|
| green | `#1E3D32` | `#A8DCC0` | `PREQUALIFIED`; C4 "Defined" |
| stop | `#6D3228` | `#F2B8AC` | `NOT_PREQUALIFIED`, and nothing else |
| clay | `#8A4F33` | `#EDBB9C` | `REFER`; `human_active`; C4 "To define" |
| amber | `#7A5D12` | `#E9D08A` | `NEEDS_INFO`; C4 "Partial" |
| slate | `#34506B` | `#9FBCD8` | `ai_active`; C4 research refs |
| ink | `#1C1F2A` | `#FFFFFF` | `ended`; errors |

Errors use ink, not stop. On an Alba screen, the stop tone means one thing: the policy or the agent said no.

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
| display | 48 / 52 (36 / 40 on phones) | 300 | -0.025em | Home greeting, login title |
| title | 28 / 34 | 400 | -0.015em | Screen titles, certificate product |
| heading | 20 / 26 | 500 | -0.01em | Card titles, dialog titles |
| body | 16 / 24 | 400 | 0 | Messages, paragraphs |
| label | 14 / 20 | 500 | 0 | Buttons, rows, key-value keys |
| caption | 13 / 18 | 400 | 0 | Meta lines, footers, author names on bubbles |
| kicker | 12 / 16 | 500 | 0.12em, uppercase | Section labels inside records and the hero only |
| amount | 36 / 40 | 300 | -0.02em | Balances. Decimals and code at 0.55em, weight 400 |

- Uppercase kickers are rare: section labels inside a record or the hero. Author names, meta lines, and navigation are sentence case.
- Weight 300 only at 28px and above.
- Nothing below 12px, including code, which is `max(12px, 0.9em)`.
- `font-variant-numeric: tabular-nums` on amounts, tables, codes, and timers.
- One number format everywhere, as the contract and the mock write it: comma thousands, dot decimals, two decimals on money, the code after a space (`306,753.45 MXN`). Scores are integers. Dates are written out in Spanish (`17 de junio de 2026`).

## Space, shape, elevation

- Spacing steps: 4, 8, 12, 16, 20, 24, 32, 40, 56, 72 px. Side gutter: 16px on phones, 32px on desktop.
- Radii:

| Token | Value | Use |
|---|---|---|
| `--r-sheet` | 28px | Sheets, dialogs, the hero, glass panels |
| `--r-card` | 22px | Cards, bubbles, C4 panes |
| `--r-row` | 14px | List rows, C4 boxes |
| `--r-field` | 12px | Inputs |
| `--r-pill` | 999px | Buttons, tags, the composer, the app bar controls |

- A bubble has `--r-card` corners except a 6px corner on the author's side, at the bottom.
- **Glass floats; solid sits.** Glass gets the blur, `--glass-edge`, and the large `--glass-shadow`. Solid white gets the tight `--solid-shadow` and no border. The hero gets the glass shadow, because it is the moment the screen exists for.

## Layout

Screens fill the browser like the real app. There is no device frame.

- **Customer** (`/login`, `/`, `/case/:id`): the aurora, a glass app bar across the top (the orb and "Alba" on the left; the customer's first name and "Salir" on the right), and one centered column. The column is 720px for chat and 1040px for the login and home grids. On `/case/:id` the composer floats at the bottom of the viewport, 680px wide, and the thread scrolls under it.
- **Agent** (`/agent`, `/agent/case/:id`, `/agent/case/:id/trace`): the aurora, a 248px glass sidebar (the brand, "Casos en revisión" with its count, the agent's name and specialty at the bottom), and a main area up to 1200px. `/agent/case/:id` has two columns, thread 1.1fr and packet 0.9fr, with the packet sticky on the right. Below 1024px the sidebar becomes a glass top bar and the columns stack with the packet first, because the packet is what the agent decides on.
- **C4 page**: keeps its layout (canvas plus a 350px side panel, one column below 1180px) and takes its tokens from this file.

## Components

### App bar and sidebar

- Customer app bar: glass, 64px, sticky. The orb (24px) and "Alba" in label weight 600 on the left. On the right, the first name in a glass pill and a text button "Salir". The login shows the brand only, plus the "Demo" button when `DEMO_LOGIN=1` (see Login).
- Agent sidebar: glass, full height. The brand at the top; one nav item, "Casos en revisión", with an ink count badge; the agent's name, specialty, and employee id at the bottom.

### Composer (`/case/:id`)

- A glass pill, 60px tall, 1px `--field-edge-glass` outline, a text field, and a 44px circular send button in `--green` with a white arrow.
- No attach, microphone, or camera button: Alba has none of those inputs.
- A soft lilac-to-ice glow sits under the pill; it strengthens while the pill has focus.
- States: empty (send disabled); ready; sending (spinner in the button, field read-only until the API accepts); error (one line above the pill, the text kept, a retry).
- Enter sends. Shift+Enter adds a line.
- In `human_active` the composer stays, because the customer may still write and the message is stored (`ARCHITECTURE.md`, "Process"). A white banner above it reads "Este caso lo ve una persona." No typing indicator shows, because nobody writes in the thread.
- In `ended` the certificate sits in the thread above the composer. A new message opens a new case (`ARCHITECTURE.md`, "Process").

### Messages (`/case/:id`; read-only on `/agent/case/:id`)

The surface follows `messages.author`:

| `author` | Side | Surface | Name above |
|---|---|---|---|
| `customer` | Right | Glass with `--tint` | The customer's first name |
| `assistant` | Left | Glass | Alba, with the orb |
| `template` | Left | White, `--solid-shadow` | Alba, with the orb |

- Bubbles are 520px wide at most. The author name is a caption above the bubble, sentence case.
- The thread carries `lang="pt"` when the process `language` is `pt`.
- A new message fades in and rises 8px over `--t-enter`. The thread is a polite live region.
- The screen renders `messages` rows only. A turn whose `reply_ok` is false never reaches it (`ARCHITECTURE.md`, "Events").

### Typing indicator (`/case/:id`)

- Shown while the client waits for the API after a customer send, and only in `ai_active` (`ARCHITECTURE.md`, "UI wait state"). In `human_active` nobody writes in the thread, so it does not show.
- It lasts exactly as long as the wait. No minimum display time and no added delay: the contract forbids a fixed sleep.
- Look: a glass capsule with the 20px Alba orb (hue turning once every `--t-orb`) and the contract's text, "escribiendo…", in `--muted`. It sits in the thread where the next Alba message will appear.
- Never shown with it: reasoning text, a list of steps, a percentage, streamed tokens, or a stop button. Alba cannot cancel a command, so a stop button would lie.

### Product rows (`/`, and `/case/:id` while the thread is empty)

- A glass sheet with two rows, one per product key: `credit_card` "Tarjeta de crédito", `personal_loan` "Préstamo personal". Each row has a 40px glass icon tile, the label, and a chevron.
- Choosing a row sends a customer message through the same endpoint as typing ("Quiero una tarjeta de crédito"). It does not set `product` on the process: the classified turn does.
- Consent is a template message, `confirm_prequalify`, that the customer answers in the thread ("sí", "no, gracias"). It is not a button or a sheet.
- After `which_product` or `confirm_prequalify`, reply rows would need a typed field the API does not return yet. Until then the customer types the answer. See **Open**.

### Certificate (`/case/:id`)

A certificate exists only for `PREQUALIFIED` and `NOT_PREQUALIFIED` (from the policy, or from the agent close). It is the hero: the full column width, `--r-sheet`, a 4px bar in the outcome's hero tone along the top. From top to bottom:

1. The outcome tag: "Precalifica · simulado" or "No precalifica · simulado".
2. The product, in title size.
3. The template paragraph, exactly as the API returns it.
4. "Hechos usados": key-value rows from `facts`. Income shows the local amount, the USD equivalent, and the exchange-rate date beside it (`ARCHITECTURE.md`, "Auth and screens").
5. "Regla que decide": the `deciding_rule` row.
6. A caption footer with `policy_version` and the dates of the facts, the way Wirely states that details are kept as of creation. When `decided_by` is `agent`, the footer adds "Revisado por una persona."

There is no slot for a credit limit, a rate for the new product, or a risk label. The Gen UI "Low risk" badge has no counterpart here: the risk estimate is the `credit_score` fact (`ARCHITECTURE.md`, "Risk estimate"), shown as a fact row, never as a label. The panel enters once over `--t-sheet`, with the same motion for both outcomes.

### Tags

A pill, 12/16 weight 500, with a 1px border and text in the tone and a white fill (on the hero: the light variant and no fill). A 6px dot in the tone leads the label. The label is always present.

### Buttons

| Kind | Look | Use |
|---|---|---|
| Primary | `--green` fill, white text, pill | "Enviar código", "Abrir sesión", "Volver a entrar" |
| Decisive | `--ink` fill, white text, pill | "Confirmar" in the agent confirm dialog |
| Secondary | White fill, 1px `--field-edge`, ink text, pill | "Pedir otro código", "Elegir al azar", "Volver" |
| Text | No fill, ink text, pill | "Salir", "Cerrar", "Cambiar documento" |
| Demo | White fill, dashed 1px `--field-edge`, ink text, pill | "Demo" in the login app bar, only with `DEMO_LOGIN=1` |
| Secondary on hero | No fill, 1px `--hero-edge`, white text, pill | "Precalificar", "No precalificar" |
| Send | 44px circle, `--green`, white icon | Composer |

- Every target on product screens, and every header control on the C4 page, is at least 44 by 44 px. The C4 tree rows and chips are denser and keep at least 24px (the WCAG 2.2 AA minimum).
- Focus: 2px outline, offset 2px, `--green`; white on the hero.
- Press: scale 0.98 over `--t-press`. Disabled: 45% opacity, not clickable.

### Fields

- White fill, 1px `--field-edge`, `--r-field`, 16px text (smaller text makes iOS zoom), label above in caption and `--muted`.
- The code field is one input: `inputmode="numeric"`, `autocomplete="one-time-code"`, tabular figures, 0.3em letter spacing.

### Login (`/login`)

- Two columns: the display title and its one-line lede on the left, one glass panel with the two steps (document number, then code) on the right, so each step's buttons stay in view without scrolling. The block is vertically centered in the space under the app bar, so the code step grows evenly up and down and the title does not move. Stacked on phones, title first (`ARCHITECTURE.md`, "Auth and screens").
- Under the lede, on both steps, a white notice reads "Si tu documento está registrado y tiene un correo asociado, te enviaremos un código. Si no te llega, acércate a una sucursal para registrar tu correo." It never changes with the answer, including for a registered document with no email: the screen never names the email or the customer, and never says whether the document is on file.
- Step 1: the document field and "Enviar código" (primary).
- Step 2: the document shown above, a caption "Revisa tu correo y escribe el código." ("Pedimos otro código. Revisa tu correo." after a resend), the code field with focus, a caption with the validity from `expires_in_seconds` (ten minutes), then the actions stacked: "Abrir sesión" (primary, full width), "Pedir otro código" (secondary, the same width), and "Cambiar documento" (text button, centered). Any failed code shows one line, "El código no es válido o venció."
- The page itself shows nothing of the demo. With `DEMO_LOGIN=1` (read from `GET /config`) the app bar on `/login` carries a "Demo" button: a white pill with a dashed 1px `--field-edge` border, so nobody reads it as a bank feature. Pressing it opens the test-customer search right below it as a popover, not a modal: white, the same dashed border, `--r-card`, with the heading "Usuarios de prueba", a search field that takes focus, white result rows (full name, country, document masked to its last 4 digits; three rows show at a time and the rest scroll inside the list), "Elegir al azar", and "Cerrar". Choosing a row fills the document field and closes it; it never skips the code. Escape, a click outside, or "Cerrar" closes it too.
- In the local demo the code arrives in Mailpit (http://localhost:8025). The screen never shows it.
- Agents do not log in here. They have their own page, `/agent/login` (email and employee code, then the emailed code), decided Sep 30 and not built yet (`ARCHITECTURE.md`, "Auth and screens").

### Home (`/`)

- A greeting in display size with the customer's first name, then the product cards in a two-column grid, in the order the API returns them.
- A product card is white. Top line: product type and masked number ("Cuenta de ahorro · ••••5725"). Then the amount in amount size with its code, then a meta line (status, rate, days past due).
- A masked number reads to screen readers as "terminada en 5725".
- The product rows follow the cards.

### Session ended, loading, errors

- An expired session (401) replaces the screen with a white card: "Tu sesión terminó", a caption, and "Volver a entrar". Nothing renews it silently (`ARCHITECTURE.md`, "Auth and screens").
- Every fetch has loading, error, and success (`AGENTS.md`).
- Loading: blocks in the target surface with a 1.2s opacity pulse, static under reduced motion.
- Error: a white card in ink, the API's reason when it sends one, and "Reintentar".

### Agent queue (`/agent`)

- Title "Casos en revisión" with the count badge.
- One white card holding the cases as table rows: customer (name and city), product, rule and reason (mono), a clay "En revisión" tag, a chevron. The whole row is the link to the case.
- Empty state: "No hay casos en revisión."

### Agent case (`/agent/case/:id`)

- Left: the thread, read-only, in a glass panel with the heading "Conversación". There is no composer, no reply box, and no text field (`ARCHITECTURE.md`, "Agent close").
- Right: the packet as the hero, sticky, section label "Paquete". Key-value rows from `analysis.completed` (`specs/08-agent-close.feature`): Pedido, Score, Ingreso mensual, Regla, Política.
- Under the rows, two hero secondary buttons of the same size: "Precalificar", then "No precalificar". Neither takes focus on load and neither is tinted by outcome, so the layout does not lean toward an answer.
- Choosing one opens a confirm dialog, the review step Wirely shows before a payment. It names the outcome, says the customer gets a message and the case closes, and offers "Volver" (secondary, focused first) and "Confirmar" (decisive).
- On success the case leaves the queue. A second close is rejected by the API (`agent_close:{process_id}`) and the screen shows that as an error.
- This confirm step is the agent's. The customer's consent (`PLAN.md` D8) is the `confirm_prequalify` template, answered in the thread.

### Trace (`/agent/case/:id/trace`)

- Title "Registro del caso". One white card per event, in the order the API returns them: a numbered glass marker, the event name in mono, the time, and the fields the rules match on. State changes show the state tag.
- A dashed 1.4px `--arrow` connector joins a card to the card named by its `caused_by_event_id`, the way the thinking-mode shot joins cards. No id, no line (`AGENTS.md`, "Events, rules, commands").

### C4 page

A record surface with a cool palette: `#E9EDF4` page, white panes and boxes, `#F5F6FA` raised rows, `--line`, `--field-edge`, `--ink`, `--muted`, the tones above, the sans stack, nothing under 12px, panes at `--r-card`, pill controls with a `--field-edge` border. Box kinds: person `#1C1F2A`, system `#1E3D32`, external `#5D6474`, highlighted link `#8A4F33`.

The dark set is cool as well: page `#0F1218`, raised `#151922`, card `#1A1E28`, ink `#E8EAF0`, muted `#A3A9B8`, line `#2C3240`, field edge `#737A8D`, person `#E8EAF0`, external `#3A4050`, arrow `#8C93A6`, with the light tone variants.

### Mock

`mocks/index.html` follows this file and the flows in `specs/`. Each screen fills the browser. The walkthrough chrome is dark, so it never reads as part of the bank:

- A 44px bar at the top: "Recorrido", previous and next, and the current screen with its number, which opens a menu of every screen grouped as Cliente and Agente. Left and right arrow keys step through the screens.
- "Nota" opens a drawer on the right with that screen's walkthrough note. Raw identifiers such as `ai_active` appear only in the notes and on agent screens. Escape closes it.
- Template sentences that are not written yet show as a dashed placeholder naming the `template_id`.

Walkthrough tokens: background `rgba(22, 25, 34, 0.88)` with blur, text `#F2F4F8`, muted `#A3A9B8`, control edges `rgba(255, 255, 255, 0.4)`.

## Motion

| Token | Value | Use |
|---|---|---|
| `--t-press` | 120ms | Button press |
| `--t-enter` | 200ms | Messages, rows, view changes |
| `--t-sheet` | 320ms | Sheets, dialogs, drawers, the demo popover, the certificate |
| `--t-orb` | 4s, linear, loop | The orb |
| `--ease` | `cubic-bezier(0.2, 0, 0, 1)` | Everything that is not a loop |

- Movement is 8px or less, except sheets and drawers.
- Only the orb and the loading pulse loop. The aurora does not move. No confetti or celebration on `PREQUALIFIED`.
- Under `prefers-reduced-motion: reduce`: fades only, 120ms at most, and the orb stands still.
- Under `prefers-reduced-transparency: reduce`, or without `backdrop-filter` support, glass becomes `rgba(255, 255, 255, 0.92)` with the same edge.

## Accessibility

Contrast, WCAG 2.x formula, computed Sep 29, 2026 for the values in this file. Glass is measured composited over the darkest aurora pixel measured in the mock at 1440px (`#8F9ABD`), its worst case.

| Foreground | Background | Ratio | Needs |
|---|---|---|---|
| `--ink` | Glass at the worst case / customer bubble there | 10.87 / 9.14 | 4.5 |
| `--muted` | Glass at the worst case | 5.23 | 4.5 |
| `--ink` | Bare aurora at the worst case | 5.88 | 4.5 |
| `--muted` | Bare aurora at the worst case | 2.83 | Not allowed (see Aurora) |
| `--ink` / `--muted` | `--surface` | 16.42 / 7.91 | 4.5 |
| white | `--green` | 11.87 | 4.5 |
| white / `--hero-muted` | `--hero`, lighter end `#374772` | 9.10 / 5.28 | 4.5 |
| Hero tones: green, stop, clay, amber | `#374772` | 5.92, 5.30, 5.28, 6.01 | 4.5 |
| Tones: green, stop, clay, amber, slate | `--surface` | 11.87, 9.83, 6.47, 6.17, 8.38 | 4.5 |
| `--field-edge` | `--surface` / C4 page | 3.63 / 3.09 | 3 |
| `--field-edge-glass` | Glass at the worst case | 3.18 | 3 |
| `--hero-edge` | `#374772` | 4.02 | 3 |
| C4 dark field edge `#737A8D` | Dark card `#1A1E28` | 3.89 | 3 |
| Walkthrough text / muted | Walkthrough bar over the aurora | 11.46 / 5.36 | 4.5 |
| `--line` | `--surface` | 1.32 | Decorative only |

- Tones always carry a text label.
- Focus is always visible (see Buttons).
- New messages and the typing indicator are announced through a polite live region.
- The document is `lang="es"`. A Portuguese thread carries `lang="pt"`.

## Icons and imagery

- Inline SVG in a 20px box, 1.5px stroke, round caps, `currentColor`: send arrow, chevron, check, close, back, clock, card, loan. No icon font and no icon package.
- The Alba mark is the orb next to the word "Alba".
- No photographs, avatars, or illustrations. The dataset has no images, so a face or a skyline would be made up. The aurora is the only decoration.

## Interface copy

Interface labels are Spanish. They are the ones this file names; a screen not built yet takes its labels from `mocks/index.html`. The login labels in `web/src/pages/Login.tsx` follow the Login section above. The typing indicator's "escribiendo…" comes from the contract. Template sentences (`confirm_prequalify`, `which_product`, `needs_income`, `refer_notice`, the agent-close message) are not in this file: they live in `api/domain/policy/templates.py`, and `ARCHITECTURE.md` says they are not written yet.

## Open

Each item needs a contract change before it is built. None is worked around in the meantime.

1. **Reply rows after `which_product` or `confirm_prequalify`.** The screen needs a typed field saying which template was sent last. A `messages` row has `author` and `body`, and no `template_id`.
2. **City, segment, and document type on the demo search rows.** The mock shows them; `CustomerSearchHit` carries the name, country, and document number only.
3. **Portuguese interface labels.** The contract localizes templates, not interface labels.
4. **How uncertainty shows on the certificate.** `PLAN.md` §2 marks it "Partial". This file gives the certificate no slot for it until that is decided.

## Before a screen is called done

- Surface follows the source: glass for typed or drafted text, solid white for decided or recorded facts, the hero for the one record the screen exists for.
- No cream, beige, or warm paper.
- Colors, radii, and durations come from tokens. No raw hex in a component.
- Every fetch renders loading, error, and success.
- No raw state or event names on customer screens.
- Every tone has a text label. Every control has a visible focus ring and a 44px target.
- The screen is checked with reduced motion and reduced transparency on.
- No slot for a limit, a new-product rate, or a risk label.
