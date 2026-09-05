import React, { useCallback, useRef, useState } from 'react';

export type GlassRounding = 'sm' | 'md' | 'lg';
export type GlassVariant = 'default' | 'strong';

interface GlassSurfaceProps<T extends React.ElementType = 'div'> {
  as?: T;
  variant?: GlassVariant;
  rounding?: GlassRounding;
  interactive?: boolean;
  className?: string;
  style?: React.CSSProperties;
  children?: React.ReactNode;
  onMouseEnter?: React.MouseEventHandler<HTMLElement>;
  onMouseLeave?: React.MouseEventHandler<HTMLElement>;
  onClick?: React.MouseEventHandler<HTMLElement>;
  onPointerMove?: React.PointerEventHandler<HTMLElement>;
}

export function GlassSurface<T extends React.ElementType = 'div'>({
  as,
  variant = 'default',
  rounding = 'md',
  interactive = false,
  className = '',
  style,
  children,
  onMouseEnter,
  onMouseLeave,
  onClick,
  onPointerMove,
  ...rest
}: GlassSurfaceProps<T>) {
  const Tag = (as ?? 'div') as React.ElementType;
  const elRef = useRef<HTMLElement | null>(null);
  const [lightPos, setLightPos] = useState({ x: 50, y: 15 });

  const handlePointerMove = useCallback((e: React.PointerEvent<HTMLElement>) => {
    if (!elRef.current) return;
    const rect = elRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    setLightPos({ x, y });
    onPointerMove?.(e);
  }, [onPointerMove]);

  const classes = [
    'aur-glass',
    variant === 'strong' ? 'aur-glass--strong' : '',
    interactive ? 'aur-glass--interactive' : '',
    `aur-glass--${rounding}`,
    className,
  ].filter(Boolean).join(' ');

  return (
    <Tag
      ref={elRef}
      className={classes}
      style={{
        '--glass-light-x': `${lightPos.x}%`,
        '--glass-light-y': `${lightPos.y}%`,
        ...style,
      } as React.CSSProperties}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      onClick={onClick}
      onPointerMove={handlePointerMove}
      {...rest}
    >
      {children}
    </Tag>
  );
}
