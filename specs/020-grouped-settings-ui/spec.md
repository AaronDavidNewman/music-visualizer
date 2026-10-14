# Feature Specification: Grouped, Collapsible Settings

**Feature Branch**: `020-grouped-settings-ui` (no git branch created; spec directory name only)

**Created**: 2026-10-14

**Status**: Draft

**Input**: User description: "clean up the UI. Use flex rows/columns to group UI elements into logical groups.  Each group should have its own section that can be individually collapsed.   2 parameters per row, and if a group has an odd number, the last group can take up the full row.  Window/frame rate/spacing should be in the top group.  Colormap is its own group.  Image type should be in its own group, since it determines what is shown after.  After image type would be image-type specific parameters:  Threshold, notes in a 'Tiles' group following the tiles image type.  Tiles and contour have the same parameters.  Threshold, notes, and blend width in the Blended Tiles group.   Movement (currently called Unit), Radius (currently called Size), Resize by Volume, Memory, Notes (currently called 'Circles Per Frame') in the Circles group.  Smoothing window, smoothing parameter, threshold, and blend width  in a 'data smoothing' group.  'Oversampling' (currently called Resolution) and interpolate in an 'image smoothing' group."

## Clarifications

### Session 2026-10-14

- Q: The description lists Threshold and Blend width both in the type groups (Tiles, Blended Tiles) and in the Data smoothing group. Where do they go? -> A: **Option A: each stays in its type group.** Threshold is in the Tiles / Contour group and in the Blended Tiles group, and Blend width is in the Blended Tiles group only; the **Data smoothing group holds only Smoothing window and Smoothing**. Every setting appears once.
- Q: "Radius (currently called Size)": should the control become a real radius? -> A: **Option A: yes, a real radius in whole pixels, 4 to 8** (default 4). The circle sizes that can be chosen are the same as today's 25 to 50 pixels of circumference (a radius of 3.98 to 7.96), now as 5 whole-pixel steps; the circle size that Resize by volume starts from is this radius (so with the resize on a circle goes from 1 to 3 times the radius). The setting's name and its values change in the request to the server as well, with a refusal message that says "The circle radius must be a whole number from 4 to 8."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The settings are arranged in labelled groups that can be collapsed (Priority: P1)

Today the settings are one long column of controls in no particular order: the colormap sits between the timing settings and the smoothing, the image type is near the bottom, and the controls that only matter for one image type are scattered among the others. The user wants the settings **cleaned up into logical groups**. Every group is its own **section with a title**, and each section can be **collapsed and expanded on its own**, so the user can fold away what they are not changing. Inside a section the controls are laid out **two to a row**; when a section has an odd number of controls, the last one takes the **whole row**.

The sections that are always there, from the top of the form:

1. **The top group** (timing): Window size, Frame rate and Window spacing. Three controls, so Window size and Frame rate share the first row and Window spacing has the second row to itself.
2. **Colormap**: a group of its own, with the one control.
3. **Image type**: a group of its own, with the one control, because it decides which groups come next.

(The groups that follow the image type are in Story 2, and the two smoothing groups are in Story 3.)

**Why this priority**: This is the whole point of the request: an ordered form of titled, collapsible groups with a regular two-column layout. Stories 2 and 3 fill in the other groups.

**Independent Test**: Open the page. See the sections "top group", "Colormap" and "Image type" in that order, each with a title and a way to collapse it. Collapse "Colormap": its control disappears and the other sections do not move apart or change. Expand it: the control is back with the value it had. In the top group see Window size and Frame rate side by side and Window spacing alone below, as wide as the two above it together.

**Acceptance Scenarios**:

1. **Given** the page is opened, **When** the settings are shown, **Then** they are in titled sections, top to bottom: the top group, Colormap, Image type, then the groups of the chosen image type and the smoothing groups (Stories 2 and 3).
2. **Given** any section, **When** the user activates its title (or its collapse control), **Then** that section's controls are hidden and the title stays; activating it again shows them again. Other sections are not affected.
3. **Given** a section is collapsed and expanded again, **When** the user looks at its controls, **Then** they have the values they had before (collapsing never resets or discards a value), and a value that was changed while the section was open is the one used when frames are created, whether the section is open or collapsed.
4. **Given** a section with two or more controls, **When** it is shown, **Then** the controls are in rows of two; **Given** a section with an odd number of controls, **When** it is shown, **Then** the last row has one control that takes the full width of the row (the top group: Window size and Frame rate, then Window spacing alone).
5. **Given** a section with a single control (Colormap, Image type), **When** it is shown, **Then** that control takes the full width of the row.
6. **Given** every section is collapsed, **When** the user looks at the form, **Then** only the section titles (and the Create frames button) are shown and they are all visible together without scrolling on a normal laptop screen.
7. **Given** a control has a value that is not allowed, **When** its section is collapsed, **Then** the title of that section shows that something in it needs attention, and Create frames stays disabled as it is today.
8. **Given** a job is running, **When** the settings are shown, **Then** the controls are disabled as they are today; the sections can still be collapsed and expanded.

---

### User Story 2 - The groups after the image type depend on the type that is chosen (Priority: P2)

The image type decides which settings mean anything, so the groups that follow the Image type section are the ones for the chosen type, and they change when the type changes. A control that has no meaning for the chosen type is not shown (today those controls are shown but greyed out).

| Image type chosen | Group shown after Image type | Its controls, two to a row |
|-------------------|------------------------------|-----------------------------|
| Tiles | **Tiles** | Threshold, Notes |
| Contour | **Contour** (the same controls as Tiles; the user: "Tiles and contour have the same parameters") | Threshold, Notes |
| Blended tiles | **Blended Tiles** | Threshold, Notes, Blend width (Blend width alone on the second row) |
| Circles | **Circles** | Movement, Radius, Resize by volume, Memory, Notes (Notes alone on the third row) |

Threshold and Blend width are in the type groups only (see the Clarifications): the Data smoothing group does not repeat them.

**Why this priority**: It is the second half of the layout and what makes the form shorter and clearer: only the groups that apply are shown. It depends on the sections of Story 1.

**Independent Test**: Choose Tiles: the Tiles group follows the Image type section, with Threshold and Notes. Choose Blended tiles: the group becomes Blended Tiles with Threshold, Notes and Blend width. Choose Contour: the same two controls as Tiles. Choose Circles: the Circles group with its five controls, and the controls that only make sense for a grid of tiles are gone. Switch back: the values entered for each type are still there.

**Acceptance Scenarios**:

1. **Given** the image type Tiles, **When** the settings are shown, **Then** a group titled Tiles follows the Image type section.
2. **Given** the image type Contour, **When** the settings are shown, **Then** a group with the same controls as Tiles follows the Image type section (its title may name Contour).
3. **Given** the image type Blended tiles, **When** the settings are shown, **Then** a group titled Blended Tiles follows the Image type section with the controls of the table.
4. **Given** the image type Circles, **When** the settings are shown, **Then** a group titled Circles follows the Image type section with Movement, Radius, Resize by volume, Memory and Notes.
5. **Given** the user changes the image type, **When** the settings are shown again, **Then** only the group for the new type is shown, and the values that the user entered earlier for any type are kept for when that type is chosen again.
6. **Given** any image type, **When** frames are created, **Then** the settings that the chosen type uses are the ones sent, with the values shown (a setting that is not shown has its default or the value it had).
7. **Given** the image type Circles, **When** the settings are shown, **Then** no control for Threshold, the Tiles Notes (12 to 84), Blend width, Oversampling or Interpolate is shown, because circles do not use them.

---

### User Story 3 - Two smoothing groups, and clearer names (Priority: P3)

The settings that smooth things out are gathered into two groups after the image-type group:

- **Data smoothing**: Smoothing window and Smoothing, on one row. They act on the note values and apply to every image type.
- **Image smoothing**: **Oversampling** and **Interpolate**, which act on the picture. They apply to the grid image types (Tiles, Contour and Blended tiles) and not to Circles, so this group is not shown for Circles.

Some controls get **clearer names**, wherever they appear (the form, the explanation texts opened by the info buttons, and the result summary shown after frames are created):

| Now called | New name |
|------------|----------|
| Unit | **Movement** |
| Size | **Radius** (now a real radius in whole pixels, 4 to 8; see the Clarifications) |
| Circles per frame | **Notes** (inside the Circles group) |
| Resolution | **Oversampling** |

**Radius** is a real radius: a whole number of pixels from 4 to 8, default 4. Before, the control (called Size) was the circle's circumference, 25 to 50 pixels, which is a radius of 3.98 to 7.96; the sizes that can be chosen are the same, as five whole-pixel steps.

**Why this priority**: These are the finishing touches: where the smoothing settings go and the new names. The form is usable without them (Stories 1 and 2), but the request asks for them.

**Independent Test**: Open the page with each image type and check that Data smoothing is always shown, Image smoothing is shown for Tiles, Contour and Blended tiles and is gone for Circles, the four renamed controls have their new names in the form, in the info texts and in the result summary, and no control still says Unit, Size, Circles per frame or Resolution.

**Acceptance Scenarios**:

1. **Given** any image type, **When** the settings are shown, **Then** a Data smoothing group is shown with Smoothing window and Smoothing on one row, after the group of the image type.
1a. **Given** the image type Circles, **When** the user sets the Radius, **Then** it is a whole number of pixels from 4 to 8 (default 4) and the circles are drawn with that radius (with Resize by volume on, from 1 to 3 times it); a value that is not a whole number from 4 to 8 is refused with the message "The circle radius must be a whole number from 4 to 8."
2. **Given** the image type Tiles, Contour or Blended tiles, **When** the settings are shown, **Then** an Image smoothing group with Oversampling and Interpolate follows Data smoothing (two controls on one row).
3. **Given** the image type Circles, **When** the settings are shown, **Then** no Image smoothing group is shown.
4. **Given** the form, the info texts and the result summary, **When** the user reads them, **Then** they say Movement, Radius, Notes (for the circles) and Oversampling where they said Unit, Size, Circles per frame and Resolution, and use no old name.
5. **Given** frames have been created, **When** the result summary is shown, **Then** it lists the settings that were used under the new names, and only those that apply to the image type.

---

### Edge Cases

- **Narrow screens**: the two-per-row layout applies at the width of the settings column on a normal screen; on a very narrow screen the controls may drop to one per row so that none is cut off or overlaps.
- **Wide controls**: the sliders with their readouts (for example "300 circles") must fit in a half-width cell without being cut off or overlapping their labels, error messages or info buttons.
- **Error messages and notices** (for example the note that a spacing is raised to the minimum) are shown under their control, inside the same cell.
- **Collapsed group with an invalid value**: the title shows that it needs attention (see Story 1, scenario 7); the value still counts, so Create frames stays disabled until it is fixed.
- **Changing the image type while a group is collapsed**: the collapsed or expanded state belongs to the group, so a group for a type that is chosen again is as the user left it; a group that is shown for the first time starts expanded.
- **Keyboard and assistive use**: the collapse control of a group can be reached and used with the keyboard, and says whether the group is expanded.
- **Frames made before or after this feature** from the same settings are identical: this feature changes how the settings are arranged and named, not what they do.
- **Results shown on the page** (the player, the summary) and the file chooser are not rearranged.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The settings MUST be arranged in titled groups, each a section of its own that the user can collapse and expand without affecting any other section.
- **FR-002**: Inside a group the controls MUST be laid out two to a row; when a group has an odd number of controls the last control MUST take the full width of its row; a group with one control MUST show it at full width.
- **FR-003**: The groups MUST appear in this order: the top group (Window size, Frame rate, Window spacing), Colormap, Image type, the group of the chosen image type (FR-005 to FR-008), Data smoothing, Image smoothing (when it applies).
- **FR-004**: Colormap and Image type MUST each be a group of their own with their one control.
- **FR-005**: For the image types Tiles and Contour a group MUST follow the Image type group with the controls Threshold and Notes (the same controls for both types).
- **FR-006**: For the image type Blended tiles a group titled Blended Tiles MUST follow the Image type group with the controls Threshold, Notes and Blend width.
- **FR-007**: For the image type Circles a group titled Circles MUST follow the Image type group with the controls Movement, Radius, Resize by volume, Memory and Notes.
- **FR-008**: A control that has no meaning for the chosen image type MUST NOT be shown (Threshold, the 12 to 84 Notes, Blend width, Oversampling and Interpolate for Circles; Blend width for Tiles and Contour; the circle controls for the grid types).
- **FR-009**: A Data smoothing group MUST be shown for every image type with Smoothing window and Smoothing; an Image smoothing group with Oversampling and Interpolate MUST be shown for Tiles, Contour and Blended tiles and MUST NOT be shown for Circles. Threshold and Blend width are NOT in the Data smoothing group (they are in the type groups, FR-005 and FR-006).
- **FR-010**: The controls MUST be renamed, in the form, in the info texts and in the result summary: Unit to **Movement**, Size to **Radius** (a real radius, FR-017), Circles per frame to **Notes** and Resolution to **Oversampling**; no old name may remain.
- **FR-011**: Collapsing a group MUST NOT change or discard any value; every value, shown or not, MUST keep being used when frames are created, with the same checks and messages as before.
- **FR-012**: A collapsed group that contains a value that is not allowed MUST show on its title that it needs attention.
- **FR-013**: The settings' defaults, ranges, validation messages and info buttons MUST be unchanged except for the renamed controls, and every setting MUST appear exactly once in the form.
- **FR-014**: Frames created from the same settings MUST be identical, file for file, to those made before this feature for every image type and setting except the circles' Radius, which is the one setting whose meaning changes (FR-017); this feature otherwise does not change how frames are made.
- **FR-015**: A group's collapse control MUST be usable with the keyboard and MUST say whether the group is expanded or collapsed to assistive technology.
- **FR-017**: The circles' size control MUST be a **radius** in whole pixels from **4 to 8**, default 4, in the form and in the request to the server (replacing the circumference of 25 to 50 pixels); a value that is not a whole number from 4 to 8 MUST be refused before a job is created with a message that says what is allowed, and the circle that is drawn MUST have that radius (with Resize by volume on, from 1 to 3 times it).
- **FR-016**: The documentation's description of the settings page MUST be updated for the groups and the new names.

### Key Entities *(include if feature involves data)*

- **Settings group**: A titled, collapsible section of the settings form with an ordered list of controls, shown in rows of two, and a condition on the image type for when it is shown (always, or only for some types).
- **Setting (control)**: One adjustable value with its name, explanation and limits; it belongs to exactly one group.
- **Image type**: The choice that decides which type-specific group is shown and which controls apply.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every image type, 100% of the settings that apply appear in exactly one group, and none that does not apply is shown.
- **SC-002**: In every group no row has more than two controls, and a group with an odd number of controls has exactly one full-width control, on the last row.
- **SC-003**: Each group can be collapsed and expanded on its own: collapsing one group changes no other group and no value, in 100% of the groups and image types.
- **SC-004**: With all groups collapsed, all group titles and the Create frames button are visible together on a 1366 × 768 screen without scrolling.
- **SC-005**: A user can find and change any setting of the chosen image type by looking at the group titles only (without scrolling past unrelated controls), checked by naming the group for each of the settings.
- **SC-006**: Frames created from the same settings and file before and after this feature are identical, file for file, for every image type and setting except the circles' Radius, and a circle's radius in the picture equals the Radius that was set (4 to 8 pixels) to within a quarter of a pixel.
- **SC-007**: None of the four old names (Unit, Size, Circles per frame, Resolution) appears anywhere in the form, the info texts or the result summary.

## Assumptions

- **Only the arrangement and the names change**, with one exception: the circles' Radius (Clarifications). What the other settings do, their defaults, ranges, checks and messages, and the way the server is asked for frames are unchanged.
- **Groups start expanded.** The request does not say which groups start collapsed; every group is expanded when the page is first opened, and whether a group is open is not remembered between visits.
- **The top group has no special name in the request** ("the top group"); it is titled by what it holds (timing of the analysis: Window size, Frame rate and Window spacing).
- **"Tiles and contour have the same parameters"** is read as: the group after Image type has the same controls (Threshold and Notes) for Tiles and for Contour; its title follows the chosen type (Tiles, or Contour).
- **Controls that do not apply are hidden, not greyed out**, because the request says the image type "determines what is shown after". Today they are shown disabled.
- **The two smoothing groups** keep the existing control names (Smoothing window, Smoothing, Interpolate); "smoothing parameter" is the control called Smoothing now. Threshold and Blend width are not in them (Clarifications).
- **Notes** is one name for two different settings, each shown only for its own image type: the 12 to 84 strongest notes of the whole file for the grid types, and the 5 to 12 strongest notes of each frame for Circles. The info texts keep telling them apart.
- **Two to a row** is the layout on the normal width of the settings column; on a narrow screen controls may wrap to one per row (see the Edge Cases).
- **The two-per-row layout puts the controls in the order the request lists them**, left to right then top to bottom.
- **The Radius default is 4 pixels**, the whole-pixel radius closest to the circumference of 25 that was the default before (a radius of 3.98); circles drawn at the default are therefore about the same size as before but not byte-identical to the old frames. Previous results shown on the page are not changed.
- This feature is about the settings form (and the circles' size setting that the Radius question changes). The file chooser, the player, the result summary's content (apart from the new names), the analysis and every image type's pictures are unchanged.
