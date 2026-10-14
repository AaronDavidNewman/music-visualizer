# Specification Quality Checklist: Generative Circles

> **Amended 2026-10-13 (look and size of the circles).** After this feature was delivered the user asked for three changes: (1) the background is the **middle color of the colormap** (row 128 of its 256-entry table) instead of black; (2) each circle is drawn with an **opacity that falls with its age** (newest opaque, opacity (m - age) / m in a memory of m circles, so the oldest is barely visible just before it is dropped); (3) a new fourth circle setting, the **circle size** (the circumference in pixels, a whole number from 25 to 50, default 25, radius size / (2 pi)), replaces "the radius is one unit" (the unit is now only the length of a step). Where this document still says black, "radius of one unit" or "three settings", the amended spec (`spec.md`, Clarifications) governs.

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-13
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

- Clarification session 2026-10-13 (re-validated, now 16 of 16): Question 1 (how many units an octave gives; the request's rule and its examples disagreed) was answered by the user with option C, the literal rule, saying the examples were wrong: the distance is **1 + |octave - 4| units**. F5 and F3 therefore move 2 units (150 and 210 degrees), not 1. FR-005, the scenarios, SC-002, the Edge Cases and the story text were updated; the marker is gone.
- The pasted request is one sentence per idea and several of them conflict or are open. Defaults chosen without a marker, documented in the Assumptions: (1) **note names and octaves are real ones** (C = 0 … B = 11, scientific octave), not the application's grid cells, whose first column is A (55 Hz): the request's F5 → column 5, 150 degrees only works that way; the grid cell of F5 is column 8, row 3; (2) 0 degrees points right and angles grow counter-clockwise; (3) below octave 4 the angle is mirrored (F3: 210, as the request's example says), which is not the exact opposite (330 degrees); (4) a circle's radius is one unit; (5) a black background; (6) the picture wraps around at its edges; (7) defaults: unit 4, memory 300, 8 circles per frame; (8) the notes are chosen **per frame** (the Notes setting of feature 017 chooses over the whole file), because the request relates a frame's strongest note to the previous frame's; (9) a note with no energy puts no circle down.
- The request says the Interpolate function "can be disabled" for this type. The spec also disables Resolution, Notes, Threshold and Blend width for circles, because they describe a grid of tiles and have no meaning there; the request does not say so. Worth confirming in `/speckit-clarify`.
- Also worth confirming in `/speckit-clarify`: whether the Threshold should apply to circles (hide notes below a share of the loudest) instead of "no energy, no circle"; whether circles should fade with age instead of keeping their color; whether circles should have a size that depends on the strength; what happens at the edges of the picture (wrap, stop or bounce); the angle convention.
- The request names no implementation, so the spec has none.
