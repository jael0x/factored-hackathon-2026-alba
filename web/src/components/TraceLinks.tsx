import { useLayoutEffect, useState, type RefObject } from "react";

import type { TraceLink } from "../trace";

const LANE_WIDTH = 10;
const GUTTER_EDGE = 8;

export type Anchors = RefObject<(HTMLElement | null)[]>;

export function linksGutter(links: readonly TraceLink[]): number {
  const lanes = links.reduce((most, link) => Math.max(most, link.lane + 1), 0);
  return lanes === 0 ? 0 : GUTTER_EDGE + lanes * LANE_WIDTH;
}

function anchorCenters(list: HTMLElement, anchors: (HTMLElement | null)[], count: number): number[] | null {
  const top = list.getBoundingClientRect().top;
  const centers = anchors.flatMap((anchor) => {
    if (anchor === null) {
      return [];
    }
    const box = anchor.getBoundingClientRect();
    return [box.top - top + box.height / 2];
  });
  return centers.length === count ? centers : null;
}

// Card heights depend on the text and the width, so the centers are measured again whenever the list resizes.
function useAnchorCenters(list: RefObject<HTMLElement | null>, anchors: Anchors, count: number): number[] | null {
  const [centers, setCenters] = useState<number[] | null>(null);
  useLayoutEffect(() => {
    const element = list.current;
    if (element === null) {
      return;
    }
    const measure = () => setCenters(anchorCenters(element, anchors.current.slice(0, count), count));
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [list, anchors, count]);
  return centers;
}

type TraceLinksProps = { links: readonly TraceLink[]; list: RefObject<HTMLElement | null>; anchors: Anchors; count: number };

// The connectors repeat what each card says in text ("Causado por el evento n"), so they are hidden from readers.
export function TraceLinks({ links, list, anchors, count }: TraceLinksProps) {
  const centers = useAnchorCenters(list, anchors, count);
  const width = linksGutter(links);
  if (width === 0 || centers === null) {
    return null;
  }
  return (
    <svg className="trace-links" width={width} aria-hidden="true" focusable="false">
      {links.map((link) => {
        const x = width - GUTTER_EDGE - link.lane * LANE_WIDTH - LANE_WIDTH / 2;
        return (
          <path
            key={`${link.from}-${link.to}`}
            d={`M ${width} ${centers[link.from]} H ${x} V ${centers[link.to]} H ${width}`}
          />
        );
      })}
    </svg>
  );
}
