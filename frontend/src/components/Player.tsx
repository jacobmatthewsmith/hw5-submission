import type { PlayerLook } from "../roster";

/** A cartoon basketball player drawn in SVG. Fictional; not based on any real person. */
export function PlayerSprite({ look }: { look: PlayerLook }) {
  const { skin, hair, hairColor, jersey, trim, number } = look;
  return (
    <svg viewBox="0 0 120 200" className="sprite" aria-hidden>
      {/* shadow */}
      <ellipse cx="60" cy="194" rx="30" ry="5" fill="rgba(0,0,0,.28)" />

      {/* ponytail sits behind the head */}
      {hair === "high-ponytail" && (
        <path className="ponytail" d="M74 26 C 96 18, 100 46, 90 62 C 88 50, 84 38, 74 34 Z" fill={hairColor} />
      )}
      {hair === "gray-afro" && <circle cx="60" cy="36" r="29" fill={hairColor} />}

      {/* legs + sneakers */}
      <rect x="44" y="148" width="11" height="36" rx="4" fill={skin} />
      <rect x="65" y="148" width="11" height="36" rx="4" fill={skin} />
      <rect x="40" y="180" width="19" height="9" rx="4" fill="#fafafa" stroke="#222" strokeWidth="1.5" />
      <rect x="62" y="180" width="19" height="9" rx="4" fill="#fafafa" stroke="#222" strokeWidth="1.5" />
      <rect x="40" y="185" width="19" height="3" fill={trim} />
      <rect x="62" y="185" width="19" height="3" fill={trim} />

      {/* shorts */}
      <path d="M38 122 H82 L84 156 H63 L60 140 L57 156 H36 Z" fill={jersey} stroke="#111" strokeWidth="1.5" />
      <rect x="38" y="122" width="44" height="5" fill={trim} />

      {/* left arm (resting) */}
      <path d="M36 82 C 26 96, 24 112, 28 128" stroke={skin} strokeWidth="10" strokeLinecap="round" fill="none" />
      {/* right arm (raises when shooting) */}
      <g className="shoot-arm">
        <path d="M84 82 C 94 94, 98 108, 96 122" stroke={skin} strokeWidth="10" strokeLinecap="round" fill="none" />
      </g>

      {/* tank top */}
      <path d="M40 72 Q60 84 80 72 L86 124 H34 Z" fill={jersey} stroke="#111" strokeWidth="1.5" />
      <path d="M44 72 Q60 86 76 72" fill="none" stroke={trim} strokeWidth="3" />
      <text x="60" y="112" textAnchor="middle" className="jersey-num" fill={trim}>
        {number}
      </text>

      {/* neck + head */}
      <rect x="54" y="60" width="12" height="14" rx="4" fill={skin} />
      <circle cx="60" cy="44" r="21" fill={skin} stroke="#111" strokeWidth="1.2" />
      <circle cx="39.5" cy="46" r="4" fill={skin} stroke="#111" strokeWidth="1" />
      <circle cx="80.5" cy="46" r="4" fill={skin} stroke="#111" strokeWidth="1" />

      {/* hair styles */}
      {hair === "gray-afro" && <path d="M38 40 C 38 18, 82 18, 82 40 C 76 30, 44 30, 38 40 Z" fill={hairColor} />}
      {hair === "short-fade" && (
        <>
          <path d="M39 40 C 39 18, 81 18, 81 40 C 78 30, 42 30, 39 40 Z" fill={hairColor} />
          {look.headband && <rect x="39" y="33" width="42" height="6" rx="3" fill={look.headband} />}
        </>
      )}
      {hair === "bun-glasses" && (
        <>
          <circle cx="60" cy="18" r="9" fill={hairColor} />
          <path d="M39 44 C 37 20, 83 20, 81 44 C 78 32, 42 32, 39 44 Z" fill={hairColor} />
        </>
      )}
      {hair === "bald-beard" && (
        <>
          <path d="M40 44 C 40 36, 44 32, 46 34 L45 46 Z" fill={hairColor} />
          <path d="M80 44 C 80 36, 76 32, 74 34 L75 46 Z" fill={hairColor} />
          <path d="M42 50 C 44 70, 76 70, 78 50 C 72 60, 48 60, 42 50 Z" fill={look.beard} />
        </>
      )}
      {hair === "high-ponytail" && (
        <>
          <path d="M39 42 C 38 20, 82 20, 81 42 C 76 30, 44 30, 39 42 Z" fill={hairColor} />
          <circle cx="76" cy="26" r="4" fill="#ff5d73" />
        </>
      )}

      {/* face */}
      <circle cx="52" cy="45" r="2.6" fill="#111" />
      <circle cx="68" cy="45" r="2.6" fill="#111" />
      {look.glasses && (
        <g fill="none" stroke="#111" strokeWidth="1.6">
          <circle cx="52" cy="45" r="6" />
          <circle cx="68" cy="45" r="6" />
          <path d="M58 45 H62" />
        </g>
      )}
      {hair === "gray-afro" && (
        <path d="M46 40 L56 41 M64 41 L74 40" stroke="#555" strokeWidth="1.5" strokeLinecap="round" />
      )}
      <path
        d={hair === "bald-beard" ? "M53 55 Q60 59 67 55" : "M52 54 Q60 61 68 54"}
        fill="none"
        stroke="#111"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <circle cx="47" cy="52" r="3" fill="rgba(255,120,120,.35)" />
      <circle cx="73" cy="52" r="3" fill="rgba(255,120,120,.35)" />
    </svg>
  );
}
