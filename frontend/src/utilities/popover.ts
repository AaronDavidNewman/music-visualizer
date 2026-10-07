export interface AnchorRect {
  left: number;
  top: number;
  bottom: number;
}
export interface Size {
  width: number;
  height: number;
}

/** Keeps `value` within [min, max]; when the range is empty (the box is larger than the space) `min` wins. */
function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(value, max));
}

/**
 * Where to put a popover, in viewport coordinates. It goes below the anchor, aligned to the anchor's left
 * edge; if it would run past the bottom and there is more room above, it goes above instead. It is then
 * moved so it lies inside the viewport, keeping `margin` from every edge.
 */
export function popoverPosition(
  anchor: AnchorRect,
  popover: Size,
  viewport: Size,
  margin = 8,
): { left: number; top: number } {
  const roomBelow = viewport.height - anchor.bottom;
  const roomAbove = anchor.top;
  const fitsBelow = popover.height + margin * 2 <= roomBelow;
  const top = fitsBelow || roomBelow >= roomAbove ? anchor.bottom + margin : anchor.top - margin - popover.height;
  return {
    left: clamp(anchor.left, margin, viewport.width - popover.width - margin),
    top: clamp(top, margin, viewport.height - popover.height - margin),
  };
}
