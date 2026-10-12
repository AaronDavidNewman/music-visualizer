# Specification Quality Checklist: Contour Image Type

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-11
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Validated in one pass; no iterations needed.
- The request itself names matplotlib's `contourf`, `np.linspace`, `set_axis_off` and `pyplot.savefig`; the spec keeps those names because they are the user's stated method, and describes the visible behavior around them. Like earlier specs, it mentions "server" and "request" at the level of the existing product vocabulary.
- The request left several points open. Each has a documented default in the spec's Assumptions instead of a clarification marker: the same 252 × 168 picture size as the other types; an orientation like the tiles picture (lowest octave at the top); notes hidden by the Threshold become 0 in the grid; a silent file is one uniform picture of the colormap's first color; the Blend width does not apply to Contour; an Agg (windowless) matplotlib backend.
- Most worth confirming in `/speckit-clarify`: (1) ~~the number of contour levels~~ (settled 2026-10-11: matplotlib chooses them, nothing hard-coded); (2) whether a hidden note should be 0 in the contour or the Threshold should not apply to Contour at all; (3) the orientation (like the tiles, or matplotlib's default with the first row at the bottom); (4) the time target for a contour job (one minute for 300 frames), which depends on how fast matplotlib draws each frame.
- Observed while preparing this spec (not part of it): the colormap list in `colormaps.py` and in the frontend also has `viridis`, `Greys` and `hsv`. This spec does not depend on the list.
- Clarification session 2026-10-11 (re-validated, still 16 of 16): (a) the contour levels are chosen by matplotlib, not hard-coded (FR-004a; the 10-band assumption was replaced, the color scale stays fixed 0 to the file's largest value); (b) the colormap names were corrected by the user (`Greys`); the list can be changed by hand, so FR-014 requires that nothing in the feature or its tests depends on particular names, only on each being a valid matplotlib colormap and on the server's and the page's lists matching; (c) a frame in which every value is 0 is a uniform first-color picture (FR-008, SC-006), since matplotlib has no contour to draw there. The tests of the earlier colormap feature were made list-tolerant in the same session, which also found and fixed a real defect: the 256-row table sampled a colormap by integer index, so a colormap with a different number of entries (such as `twilight`, 510) lost part of its scale; it is now sampled at 256 evenly spaced positions.
