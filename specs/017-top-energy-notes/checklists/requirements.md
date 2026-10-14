# Specification Quality Checklist: Top-Energy Notes

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

- Validated in one pass; no iterations needed.
- FR-003 keeps the names `np.linspace` and `np.interp` because the user named them for the interpolation in the request (and in the Resolution feature); the visible behavior is described around them. Like earlier specs, it mentions "server" and "request" at the level of the existing product vocabulary.
- The request is short and has several readings that change the result. No clarification marker was used because each has a reasonable default, documented in the spec's Assumptions: (1) **energy over the whole file** (sum of smoothed values), so the same n notes are used in every frame; (2) **the other notes are dropped**, and the n values are interpolated over the whole grid, not set to 0 in place; (3) the spread is **one-dimensional, in order of pitch, to the 84 values of the original grid**, which the Resolution setting then makes finer, so that 84 notes gives exactly today's picture; (4) the file's loudest value over all 88 notes stays the scale and the Threshold reference.
- Most worth confirming in `/speckit-clarify`: (1) whole-file energy against energy in each frame (a per-frame choice follows the music more closely but makes the choice flip from frame to frame, which the request wants less of); (2) whether the chosen notes should be spread in a line from the lowest to the highest pitch (the spec's default) or laid out on a smaller grid (for example 12 columns by n / 12 rows) before the Resolution step; (3) whether the scale should follow the loudest chosen note instead of the loudest note of the file; (4) the measure of energy (sum of values, or sum of squares).
- With fewer than 84 notes a position in the picture no longer stands for one fixed note; the spec says so under Edge Cases.
- Found while planning (a prototype on synthetic files, see research.md): the request's hope for a less jittery picture holds only in some cases. The average frame-to-frame change of the raw values grows as notes are dropped, because each remaining note covers more of the picture; in color space it is lower with 12 notes than with 84 only for sustained notes with strong noise (about 23% lower at the highest noise measured). SC-007 and the Edge Cases were reworded so that the spec does not promise more than that; still 16 of 16.
