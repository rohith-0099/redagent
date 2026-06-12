// Cohesive line-icon set for the console. Stroke-based, currentColor, 24px grid
// so every glyph inherits the surrounding text color + size (className).
// Hand-rolled (no runtime dep) -> build-safe. Geometric, technical, hairline.
import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

function Svg({ children, ...p }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="1em"
      height="1em"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...p}
    >
      {children}
    </svg>
  );
}

/* status / verdict */
export const Check = (p: IconProps) => (
  <Svg {...p}><path d="M20 6 9 17l-5-5" /></Svg>
);
export const X = (p: IconProps) => (
  <Svg {...p}><path d="M18 6 6 18M6 6l12 12" /></Svg>
);
export const ShieldCheck = (p: IconProps) => (
  <Svg {...p}>
    <path d="M12 3 5 6v5.5c0 4.2 2.9 7.6 7 8.5 4.1-.9 7-4.3 7-8.5V6l-7-3Z" />
    <path d="m9.2 11.8 1.9 1.9 3.7-3.8" />
  </Svg>
);
export const ShieldAlert = (p: IconProps) => (
  <Svg {...p}>
    <path d="M12 3 5 6v5.5c0 4.2 2.9 7.6 7 8.5 4.1-.9 7-4.3 7-8.5V6l-7-3Z" />
    <path d="M12 8.5v3.5" />
    <path d="M12 15.2h.01" />
  </Svg>
);
export const AlertTriangle = (p: IconProps) => (
  <Svg {...p}>
    <path d="M10.3 4.3 2.6 18a1.5 1.5 0 0 0 1.3 2.2h16.2a1.5 1.5 0 0 0 1.3-2.2L13.7 4.3a1.6 1.6 0 0 0-2.8 0Z" />
    <path d="M12 9.5v4" />
    <path d="M12 17h.01" />
  </Svg>
);

/* chevrons / arrows */
export const ChevronDown = (p: IconProps) => (
  <Svg {...p}><path d="m6 9 6 6 6-6" /></Svg>
);
export const ChevronRight = (p: IconProps) => (
  <Svg {...p}><path d="m9 6 6 6-6 6" /></Svg>
);
export const ArrowRight = (p: IconProps) => (
  <Svg {...p}><path d="M5 12h14" /><path d="m13 6 6 6-6 6" /></Svg>
);
export const ArrowLeft = (p: IconProps) => (
  <Svg {...p}><path d="M19 12H5" /><path d="m11 18-6-6 6-6" /></Svg>
);
export const CornerDownRight = (p: IconProps) => (
  <Svg {...p}><path d="M5 5v6a3 3 0 0 0 3 3h11" /><path d="m15 10 4 4-4 4" /></Svg>
);

/* actions */
export const Play = (p: IconProps) => (
  <Svg {...p}><path d="M7 4.5v15a1 1 0 0 0 1.5.87l12-7.5a1 1 0 0 0 0-1.74l-12-7.5A1 1 0 0 0 7 4.5Z" /></Svg>
);
export const Zap = (p: IconProps) => (
  <Svg {...p}><path d="M13 2 4.5 13.5H11l-1 8.5L19.5 10H13l0-8Z" /></Svg>
);
export const Download = (p: IconProps) => (
  <Svg {...p}><path d="M12 3v12" /><path d="m7.5 10.5 4.5 4.5 4.5-4.5" /><path d="M4.5 20.5h15" /></Svg>
);
export const Refresh = (p: IconProps) => (
  <Svg {...p}>
    <path d="M20 11a8 8 0 0 0-14-4.5L4 8.5" />
    <path d="M4 4v4.5h4.5" />
    <path d="M4 13a8 8 0 0 0 14 4.5l2-2.5" />
    <path d="M20 20v-4.5h-4.5" />
  </Svg>
);
export const Close = (p: IconProps) => (
  <Svg {...p}><path d="M18 6 6 18M6 6l12 12" /></Svg>
);

/* panel headers */
export const Sliders = (p: IconProps) => (
  <Svg {...p}>
    <path d="M5 7h7M16 7h3" />
    <path d="M5 17h3M12 17h7" />
    <circle cx="14" cy="7" r="2" />
    <circle cx="10" cy="17" r="2" />
  </Svg>
);
export const Radar = (p: IconProps) => (
  <Svg {...p}>
    <path d="M19.07 4.93A10 10 0 1 0 21 12" />
    <path d="M15.5 8.5A6 6 0 1 0 18 12" />
    <path d="M12 12 19 5" />
    <circle cx="12" cy="12" r="1.1" fill="currentColor" stroke="none" />
  </Svg>
);
export const Layers = (p: IconProps) => (
  <Svg {...p}><path d="m12 3 9 5-9 5-9-5 9-5Z" /><path d="m3 13 9 5 9-5" /></Svg>
);
export const Crosshair = (p: IconProps) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="7" />
    <path d="M12 2v4M12 18v4M2 12h4M18 12h4" />
    <circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none" />
  </Svg>
);
export const FileBug = (p: IconProps) => (
  <Svg {...p}><rect x="5" y="3" width="14" height="18" rx="1.5" /><path d="M9 8h6M9 12h6M9 16h4" /></Svg>
);
export const Terminal = (p: IconProps) => (
  <Svg {...p}><path d="m6 8 4 4-4 4" /><path d="M13 16h5" /></Svg>
);
export const Dot = (p: IconProps) => (
  <Svg {...p}><circle cx="12" cy="12" r="5" fill="currentColor" stroke="none" /></Svg>
);
