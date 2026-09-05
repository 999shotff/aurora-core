import { useCallback, useEffect, useRef, useState } from 'react';

export type SheetEdge = 'left' | 'right';

interface UsePhysicsSheetOptions {
  edge: SheetEdge;
  /** width in px used before the element has mounted/measured */
  fallbackSize?: number;
}

/**
 * Spring + momentum + rubber-band drawer physics, driven by Pointer Events
 * so mouse/touch/pen share one code path. Returns a transform (px) to apply
 * to the panel element, plus drag handlers and imperative open/close.
 */
export function usePhysicsSheet({ edge, fallbackSize = 320 }: UsePhysicsSheetOptions) {
  const elRef = useRef<HTMLDivElement | null>(null);
  const initialClosed = edge === 'left' ? -fallbackSize : fallbackSize;
  const [pos, setPos] = useState(initialClosed);
  const [isOpen, setIsOpen] = useState(false);
  const posRef = useRef(initialClosed);
  const draggingRef = useRef(false);
  const startPointerRef = useRef(0);
  const startPosRef = useRef(0);
  const lastPointerPosRef = useRef(0);
  const lastPointerTRef = useRef(0);
  const velRef = useRef(0);
  const rafRef = useRef<number | null>(null);
  const reducedRef = useRef(false);

  useEffect(() => {
    reducedRef.current = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }, []);

  const size = useCallback(() => elRef.current?.offsetWidth || fallbackSize, [fallbackSize]);
  const closedPos = useCallback(() => (edge === 'left' ? -size() : size()), [edge, size]);

  const applyPos = useCallback((p: number) => {
    posRef.current = p;
    setPos(p);
  }, []);

  useEffect(() => {
    // keep closed panels pinned off-screen correctly on resize
    const onResize = () => { if (!isOpen) applyPos(closedPos()); };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [isOpen, closedPos, applyPos]);

  // Initial position is set via lazy useState above (edge/fallbackSize based);
  // once the element mounts, the resize-effect below corrects it to the real
  // measured width if it differs — no synchronous setState-on-mount needed.

  const animateTo = useCallback((target: number, initialVelocity = 0) => {
    const opening = target === 0;
    setIsOpen(opening);
    if (reducedRef.current) { applyPos(target); return; }

    const stiffness = 260, damping = 28, mass = 1;
    let velocity = initialVelocity;
    let p = posRef.current;
    let lastT = performance.now();

    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    const step = (t: number) => {
      const dt = Math.min((t - lastT) / 1000, 0.032);
      lastT = t;
      const force = -stiffness * (p - target) - damping * velocity;
      velocity += (force / mass) * dt;
      p += velocity * dt;
      applyPos(p);
      if (Math.abs(p - target) < 0.4 && Math.abs(velocity) < 12) {
        applyPos(target);
        rafRef.current = null;
        return;
      }
      rafRef.current = requestAnimationFrame(step);
    };
    rafRef.current = requestAnimationFrame(step);
  }, [applyPos]);

  const open = useCallback(() => animateTo(0, 0), [animateTo]);
  const close = useCallback(() => animateTo(closedPos(), 0), [animateTo, closedPos]);

  const onPointerDown = useCallback((e: React.PointerEvent) => {
    draggingRef.current = true;
    startPointerRef.current = e.clientX;
    startPosRef.current = posRef.current;
    lastPointerPosRef.current = e.clientX;
    lastPointerTRef.current = performance.now();
    velRef.current = 0;
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
  }, []);

  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      if (!draggingRef.current) return;
      const p = e.clientX;
      const delta = p - startPointerRef.current;
      let newPos = startPosRef.current + delta;

      const closed = closedPos();
      const min = Math.min(0, closed);
      const max = Math.max(0, closed);
      if (newPos < min) newPos = min - Math.sqrt(min - newPos) * 3;
      if (newPos > max) newPos = max + Math.sqrt(newPos - max) * 3;

      const now = performance.now();
      const dt = (now - lastPointerTRef.current) / 1000;
      if (dt > 0.001) velRef.current = (p - lastPointerPosRef.current) / dt;
      lastPointerPosRef.current = p;
      lastPointerTRef.current = now;
      applyPos(newPos);
    };
    const onUp = () => {
      if (!draggingRef.current) return;
      draggingRef.current = false;

      const closed = closedPos();
      const closedSign = Math.sign(closed) || (edge === 'left' ? -1 : 1);
      const flingThreshold = 380;
      const openingFling = velRef.current * closedSign < -flingThreshold;
      const closingFling = velRef.current * closedSign > flingThreshold;

      let target: number;
      if (openingFling) target = 0;
      else if (closingFling) target = closed;
      else target = Math.abs(posRef.current) < Math.abs(closed) / 2 ? 0 : closed;

      animateTo(target, velRef.current);
    };
    window.addEventListener('pointermove', onMove, { passive: true });
    window.addEventListener('pointerup', onUp);
    window.addEventListener('pointercancel', onUp);
    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      window.removeEventListener('pointercancel', onUp);
    };
  }, [closedPos, edge, animateTo, applyPos]);

  return { elRef, pos, isOpen, open, close, onPointerDown };
}
