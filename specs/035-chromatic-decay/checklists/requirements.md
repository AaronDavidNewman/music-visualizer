# Specification Quality Checklist: Chromatic Decay

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-11-09
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

- The two markers were answered by the user on 2026-11-09: the layout is a ring in circle-of-fifths order (C at the top, clockwise), the full radius letting neighbouring full circles just touch; and each receiver gets the same amount that each neighbour got in Decay Exp, so a circle gives a quarter of the total. Validated again, no failing item.
- Revised 2026-11-09 during implementation: the lossless reading of "the same amount to each receiver" never fades on a closed ring; the user chose Decay Exp's edge rule (the same total given away, one eighth to each of the two receivers, six eighths lost). Spec, research, data model and contract updated.
- Readings taken by assumption (none blocking): the 12 letters counted from A; the five loudest letters gain the amounts of Decay Exp; the taper rule is kept unchanged although it was set for 84 circles (it will practically never fall); "a note decays to itself" is the round trip through the receivers; `decay_rate` keeps its field and is validated per image type.
