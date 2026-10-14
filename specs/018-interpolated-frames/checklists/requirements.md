# Specification Quality Checklist: Interpolated Frames

> **Amendment 2026-10-13**: the interpolation function was removed after the user saw the rendered frames ("The others don't really work"). Only `blend` is made: there is no function dropdown, no `interpolate_function` field and no response key for it, and no `soft_light`, `hard_light`, `overlay`, `screen` or `subtract` code. A request that still sends `interpolate_function` is accepted and the field is ignored. [spec.md](spec.md), [data-model.md](data-model.md) and [contracts/interpolate-api.md](contracts/interpolate-api.md) describe the result; this document is kept as it was written, so the passages about the five other functions, option B and the function dropdown describe the first version.

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-12
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

- Clarification session 2026-10-12 (re-validated, now 16 of 16): Question 1 (how the five functions without a weight use the position between the two drawn frames) was answered by the user with option B: an in-between frame at position k of n is `f(earlier, blend(earlier, later, k / n))`. FR-005, Story 3 scenario 1, SC-007, the Edge Cases and the Assumptions were updated; the marker is gone.
- Found while planning (a prototype, see research.md): making an in-between frame with Pillow costs about 0.6 to 0.9 ms, drawing a Tiles or Blended frame about 0.55 ms and a contour frame about 9 ms. So interpolation saves time only for the contour; Story 3 scenario 6 and SC-005 were reworded so that the spec does not promise a gain for the tile pictures (still 16 of 16).
- The request itself names the Pillow library and its functions (`blend`, `soft_light`, `hard_light`, `overlay`, `screen`, `subtract`); FR-004 to FR-006 keep those names because they are the user's stated method, and describe the visible behavior around them (as the contour spec did for matplotlib). Like earlier specs, it mentions "server" and "request" at the level of the existing product vocabulary.
- Checked against the installed Pillow 12.3.0: all six functions exist (`Image.blend`, and `ImageChops.soft_light`, `hard_light`, `overlay`, `screen`, `subtract`). Only `blend` takes a weight (`alpha`); the five `ImageChops` functions take two pictures and nothing else (`subtract` also takes an optional scale and offset). That is why Question 1 existed: applied literally to the two drawn frames next to a gap, those five functions would give **the same picture for every frame of the gap**; option B makes the frames differ.
- Defaults chosen without a marker, documented in the Assumptions: the drawn frames are the frames that would have been made anyway (analysis and smoothing run for every frame, only the drawing is skipped); counting from 1 as in the request (positions 1, n + 1, 2n + 1); the last frame of the file is always drawn; in-between frames are true-color pictures; the field names are `interpolate` and `interpolate_function`.
- Also worth confirming in `/speckit-clarify`: (1) whether the Interpolation function dropdown should be disabled at Interpolate 1 (the spec's default) or stay enabled; (2) whether the last frame should be drawn when the number of frames does not fit the pattern (the spec's default) or the last drawn frame should simply be held; (3) the time target (a contour job at interpolate 5 in at most half the time of interpolate 1).
