import { useEffect, useId, useRef, useState } from "react";

import { DemoSearch, type DemoSource } from "./DemoSearch";

type DemoSearchPopoverProps<Hit> = {
  source: DemoSource<Hit>;
  isSelected: (hit: Hit) => boolean;
  onPick: (hit: Hit) => void;
};

export function DemoSearchPopover<Hit>({ source, isSelected, onPick }: DemoSearchPopoverProps<Hit>) {
  const panelId = useId();
  const titleId = useId();
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    const closeOnOutsidePointer = (event: PointerEvent) => {
      if (event.target instanceof Node && !wrapRef.current?.contains(event.target)) {
        setOpen(false);
      }
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener("pointerdown", closeOnOutsidePointer);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsidePointer);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  const close = () => {
    setOpen(false);
    triggerRef.current?.focus();
  };

  const pick = (hit: Hit) => {
    onPick(hit);
    setOpen(false);
  };

  return (
    <div className="popover-anchor" ref={wrapRef}>
      <button
        ref={triggerRef}
        type="button"
        className="btn demo-trigger"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((value) => !value)}
      >
        Demo
        <svg className="i" viewBox="0 0 24 24" aria-hidden="true">
          <path d={open ? "M6 15l6-6 6 6" : "M6 9l6 6 6-6"} />
        </svg>
      </button>
      <div id={panelId} className="popover" role="dialog" aria-labelledby={titleId} hidden={!open}>
        {open && (
          <DemoSearch titleId={titleId} source={source} isSelected={isSelected} onPick={pick} onClose={close} />
        )}
      </div>
    </div>
  );
}
