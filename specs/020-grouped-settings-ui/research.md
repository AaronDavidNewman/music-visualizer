# Research: Grouped, Collapsible Settings

No `[NEEDS CLARIFICATION]` remains in the spec (both questions were answered on 2026-10-14). The decisions below settle how to build it. Facts about the current code were read from the repository.

## What exists today

- `SettingsForm.vue` (557 lines): about 20 controls in a single column; the first row is a CSS grid `repeat(auto-fit, minmax(8.5rem, 1fr))` with Window size, Frame rate and Window spacing; then Colormap, Smoothing window, Smoothing, Threshold, Notes, Image type, Blend width, the five circle controls (inside `v-if="imageType === 'circles'"`), Resolution, Interpolate, and the submit button. Controls that do not apply are `disabled` (`gridSettingsApply`, `blendWidthApplies`).
- Sliders sit in `.slider-row` (the range input plus an `<output>` with `min-width: 9rem` for the wide readouts such as "300 circles" or "1 (every frame drawn)").
- The settings column is 30 rem wide on a page of at least 60 rem, the page width otherwise (`App.vue`).
- Tests: vitest in node (no DOM library); the form is tested by `renderToString` (the starting image type only) and by reading the source with `?raw`.
- `App.vue`'s summary prints "Circle unit", "Circle size", "Circle memory", "Circles per frame", "Resolution".
- The circle size is a circumference (25 to 50 px), converted by `circle_radius(size) = size / (2 pi)` in `circles.py`; the discs are drawn on a 4 times larger canvas, then averaged down.

## Decision 1: Collapsing with the browser's own `<details>` / `<summary>`

- **Decision**: Each group is a `<details>` element with a `<summary>` title. The open state is bound with `:open` and updated from the `toggle` event into one in-memory map keyed by the group id (default: open).
- **Rationale**: It is a real disclosure widget: keyboard operable (Enter/Space on the summary), announced to assistive technology as expanded or collapsed (FR-015), no script needed to hide the body, and a hidden body stays in the document, so every value is kept (FR-011). It renders in server-side rendering (the project's test method) as a plain `<details open>`.
- **Alternatives considered**: a `<button aria-expanded>` with `v-show` (more code to get the same accessibility, and the same SSR result); `v-if` on the body (would discard values: rejected by FR-011).

## Decision 2: Two to a row with a wrapping flex body

- **Decision**: The body of a group is `display: flex; flex-wrap: wrap; gap`. Every control cell has `flex: 1 1 calc(50% - gap/2)` with `min-width: 0`, and `.cell:last-child:nth-child(odd) { flex-basis: 100% }` makes an odd last control full width. Below a narrow breakpoint (about 26 rem of viewport) every cell is `flex-basis: 100%`.
- **Rationale**: This is what the request asks for ("flex rows/columns"), needs no knowledge of how many controls a group has, and works when a type-specific group has 2, 3 or 5 controls. Because a hidden control is not in the document (`v-if`), "last child" and "odd" are always computed over what is shown.
- **Alternatives considered**: CSS grid with two columns and `grid-column: 1 / -1` on the last odd child (the same effect, but the request says flex); explicit row wrappers in the template (every row written by hand, and it breaks when a control is hidden).

## Decision 3: Hide the controls that do not apply (v-if), keep their values

- **Decision**: The group of the chosen type, and the Image smoothing group, are rendered with `v-if`; a control that does not apply is simply not in the form. Values live in the form's refs, so changing the type back restores what the user had entered, and the hidden values are still sent as before (the server ignores what a type does not use).
- **Rationale**: The spec (FR-008, assumption) says the image type "determines what is shown after"; greyed-out controls were the old behaviour.
- **Alternatives considered**: keep them disabled (clutter, rejected by the request).

## Decision 4: A pure group model that the form and the tests share

- **Decision**: `utilities/groups.ts` holds `GROUPS` (id, title, ordered control ids) and functions: `groupsFor(imageType)` (the ordered list of groups shown), `groupTitle(id, imageType)`, `controlsIn(groupId, imageType)`, `isOpen(state, id)` / `toggle(state, id)`, and `groupOf(controlId)`. The template uses `groupsFor` for what to render and `controlsIn` for `v-if` on the individual controls, so the single source of truth for "which control is in which group" is testable without a browser.
- **Rationale**: The project has no DOM test environment and adding one is a new dependency; with a pure model the tests can prove FR-003 to FR-009 (every control exactly once, the groups of each type, the order, rows of two) directly, and SSR rendering checks that the template agrees with it.
- **Alternatives considered**: add jsdom or happy-dom (a new dev dependency; the project has avoided them); test only by source guards (weak: they would not notice a control in the wrong group).

## Decision 5: The row arithmetic in the model, the layout in CSS

- **Decision**: The model also gives `rowsOf(count)` (an array of row sizes: `[2, 2, 1]` for 5), used by the tests to state the layout the CSS must produce, and a source guard checks that the CSS has the two-per-row basis and the odd-last rule.
- **Rationale**: The visual result cannot be rendered here; stating the intended rows in code and guarding the rule in the stylesheet is the best verification available, and the quickstart adds a manual look.

## Decision 6: Slider readouts in the label row

- **Decision**: In a half-width cell (about 14 rem at the 30 rem column) the readout of a slider moves into the label row, right-aligned, and the slider takes the full cell width under it; the `min-width: 9rem` of the old readout goes.
- **Rationale**: A readout of 9 rem next to a slider would leave about 4 rem for the slider; two controls per row would look cramped and the wide readouts ("1 (every frame drawn)") would be cut off or wrap badly. The label row also holds the info button, so the long labels ("Window spacing (× window size)") need to wrap; the label is allowed to wrap and the readout does not shrink.
- **Alternatives considered**: shortening the readouts (changes the existing readouts and their tests); a wider column (the layout is fixed at 30 rem).

## Decision 7: "Needs attention" on a collapsed group

- **Decision**: Each group's component receives a `problem` flag (any of its controls' validation errors); the summary shows a visible "needs attention" mark (text, not only a colour) and `aria-invalid`-style wording; Create frames stays disabled by the existing rule.
- **Rationale**: FR-012. The errors already exist as computed values in the form; only grouping them is new.

## Decision 8: Open state, defaults and per-type groups

- **Decision**: All groups start open; the state is a `reactive` map in the form, not stored anywhere. The group of the type has the id of the image type (`tiles`, `contour`, `blended`, `circles`), so each type's group remembers its own open state while the form lives, and a group shown for the first time is open.
- **Rationale**: The spec's assumption. Persisting to local storage is a possible later step and would need its own spec.

## Decision 9: Renames and the messages

- **Decision**: Labels, help texts and the result summary use Movement, Radius, Notes (circles) and Oversampling. The **client messages and the server messages** for these settings follow the new names so that they agree (the frontend tests state that they equal the server's): `The circle movement must be a whole number from 1 to 10.`, `The circle radius must be a whole number from 4 to 8.`, `The oversampling must be a whole number from 1 to 5.`; the circle notes message (`The number of circle notes must be a whole number from 5 to 12.`) already names no old label. The request **field names** do not change except the radius (`circle_unit`, `circle_notes`, `resolution`, `note_count` stay), because the spec is about what the user sees.
- **Rationale**: "no old name may remain" (FR-010, SC-007) applies to everything the user reads; a message shown under a control that says "resolution" would break it.
- **Alternatives considered**: rename all API fields (a larger breaking change that the request does not ask for); leave the server messages (they would disagree with the client's and with the labels).

## Decision 10: The Radius in the backend

- **Decision**: `circle_size` (circumference, 25 to 50) is replaced by `circle_radius`: a whole number of pixels from 4 to 8, default 4. The disc is drawn with exactly that radius (the 4 times larger canvas keeps the sub-pixel placement and edges); with Resize by volume on, the radius is multiplied by 1 to 3 as before. The router parses `circle_radius` like the other whole-number fields (not sent: default; sent: refused unless a whole number 4 to 8, before the file is read), and the response reports `circle_radius` (no `circle_size`). A request that still sends `circle_size` is ignored (unknown form fields already are).
- **Rationale**: The clarification (option A). The sizes that can be chosen equal the old range (radius 3.98 to 7.96), as five whole-pixel steps, and the default (4) is within 0.02 px of the old default (25 / 2 pi = 3.98), so a default circle looks the same but the files are not byte-identical (stated in the spec).
- **Alternatives considered**: keep both fields (two ways to say one thing); half-pixel steps (option B, not chosen).

## Decision 11: What stays byte-identical

- **Decision**: The four reference hashes (tiles, blended, Blues/smoothing/threshold, contour) must be unchanged: nothing in the backend changes for them. For circles, new tests check that the disc drawn for radius `r` has exactly that radius (times the resize factor) and that the placement, colors, opacities and edge smoothing are unchanged (the existing tests of those, adapted to the radius).

## Decision 12: Documentation

- **Decision**: README's page description and circles paragraph are updated for the groups and names (the Resolution paragraph keeps the feature number and says the control is now called Oversampling); the 016 and 019 documents that name the old controls get an amendment note rather than a rewrite, as for earlier amendments.

## Open items

None. Things that cannot be verified here and are left to the quickstart's manual step: how the form looks in a real browser (the half-width sliders, the wrapped labels, the 1366 × 768 fit of SC-004).
