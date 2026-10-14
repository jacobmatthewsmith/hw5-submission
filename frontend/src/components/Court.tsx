import { forwardRef, useImperativeHandle, useRef, useState } from "react";
import { BY_AGENT, HOOP, ROSTER } from "../roster";
import type { AgentName } from "../types";
import { PlayerSprite } from "./Player";

export function Basketball({ label, className }: { label?: string | number; className?: string }) {
  return (
    <svg viewBox="0 0 100 100" className={className} aria-hidden>
      <circle cx="50" cy="50" r="47" fill="#f28c28" stroke="#5a2a00" strokeWidth="4" />
      <path d="M3 50 H97 M50 3 V97" stroke="#5a2a00" strokeWidth="3.5" fill="none" />
      <path d="M17 15 C 38 35, 38 65, 17 85 M83 15 C 62 35, 62 65, 83 85" stroke="#5a2a00" strokeWidth="3.5" fill="none" />
      {label !== undefined && (
        <>
          <circle cx="50" cy="50" r="22" fill="#fff6e8" stroke="#5a2a00" strokeWidth="3" />
          <text x="50" y="58" textAnchor="middle" className="ball-label">
            {label}
          </text>
        </>
      )}
    </svg>
  );
}

export interface Bubble {
  kind: "said" | "thinking" | "tool" | "result" | "handoff" | "done" | "error";
  text: string;
}

export interface CourtHandle {
  enter: (ticketId: number, holder: AgentName) => Promise<void>;
  pass: (from: AgentName, to: AgentName) => Promise<void>;
  shoot: (agent: AgentName) => Promise<void>;
  dropOut: () => Promise<void>;
  place: (ticketId: number, holder: AgentName) => void;
  clear: () => void;
}

interface Props {
  active: Set<AgentName>;
  done: Set<AgentName>;
  bubbles: Partial<Record<AgentName, Bubble>>;
}

type Pt = { x: number; y: number };
const hand = (a: AgentName): Pt => ({ x: BY_AGENT[a].spot.x + 2.7, y: BY_AGENT[a].spot.y - 12.5 });
const RIM_IN: Pt = { x: HOOP.x, y: HOOP.y - 1.5 };
const RIM_OUT: Pt = { x: HOOP.x, y: HOOP.y + 7 };
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function arc(a: Pt, b: Pt, lift: number, n = 14): Keyframe[] {
  const top = Math.min(a.y, b.y) - lift;
  return Array.from({ length: n + 1 }, (_, i) => {
    const t = i / n;
    // quadratic Bezier through a control point that peaks at `top`
    const cy = 2 * top - (a.y + b.y) / 2;
    const x = a.x + (b.x - a.x) * t;
    const y = (1 - t) ** 2 * a.y + 2 * (1 - t) * t * cy + t ** 2 * b.y;
    return { left: `${x}%`, top: `${y}%`, transform: `translate(-50%,-50%) rotate(${t * 540}deg)` };
  });
}

export const Court = forwardRef<CourtHandle, Props>(function Court({ active, done, bubbles }, ref) {
  const ballRef = useRef<HTMLDivElement>(null);
  const [ball, setBall] = useState<{ ticketId: number; at: Pt } | null>(null);
  const [shooter, setShooter] = useState<AgentName | null>(null);
  const [swishKey, setSwishKey] = useState(0);

  const run = async (frames: Keyframe[], ms: number, easing = "linear") => {
    const el = ballRef.current;
    if (!el) return;
    const anim = el.animate(frames, { duration: ms, easing, fill: "forwards" });
    await anim.finished.catch(() => undefined);
    const last = frames[frames.length - 1];
    el.style.left = String(last.left);
    el.style.top = String(last.top);
    anim.cancel();
  };

  useImperativeHandle(ref, () => ({
    place(ticketId, holder) {
      setBall({ ticketId, at: hand(holder) });
    },
    clear() {
      setBall(null);
    },
    async enter(ticketId, holder) {
      setBall({ ticketId, at: { x: 50, y: -12 } });
      await sleep(30);
      await run(arc({ x: 50, y: -12 }, hand(holder), 6), 900, "ease-in");
    },
    async pass(from, to) {
      await run(arc(hand(from), hand(to), 10), 750);
    },
    async shoot(agent) {
      setShooter(agent);
      await sleep(220);
      await run(arc(hand(agent), RIM_IN, 24, 18), 1100, "ease-in-out");
      setSwishKey((k) => k + 1);
      await run(
        [
          { left: `${RIM_IN.x}%`, top: `${RIM_IN.y}%`, transform: "translate(-50%,-50%) scale(.92)" },
          { left: `${RIM_OUT.x}%`, top: `${RIM_OUT.y}%`, transform: "translate(-50%,-50%) scale(.92)" },
        ],
        260,
      );
      setShooter(null);
    },
    async dropOut() {
      const floor = 93;
      await run(
        [
          { left: `${RIM_OUT.x}%`, top: `${RIM_OUT.y}%` },
          { left: `${RIM_OUT.x - 2}%`, top: `${floor}%`, offset: 0.45 },
          { left: `${RIM_OUT.x - 4}%`, top: `${floor - 12}%`, offset: 0.62 },
          { left: `${RIM_OUT.x - 6}%`, top: `${floor}%`, offset: 0.78 },
          { left: `${RIM_OUT.x - 7}%`, top: `${floor - 4}%`, offset: 0.88 },
          { left: `${RIM_OUT.x - 8}%`, top: `${floor}%`, offset: 1 },
        ].map((f) => ({ ...f, transform: "translate(-50%,-50%)" })),
        1300,
        "ease-in",
      );
      await sleep(250);
      setBall(null);
    },
  }));

  return (
    <div className="court">
      <CourtScene />

      {/* hoop drawn as HTML so the net can swish above the scene */}
      <div className="hoop" style={{ left: `${HOOP.x}%`, top: `${HOOP.y}%` }}>
        <div className="backboard" />
        <div className="rim" />
        <svg key={swishKey} viewBox="0 0 60 50" className={`net ${swishKey ? "swish" : ""}`} aria-hidden>
          {[0, 10, 20, 30, 40, 50, 60].map((x) => (
            <path key={x} d={`M${x} 0 L${30 + (x - 30) * 0.55} 46`} stroke="#fff" strokeWidth="2" fill="none" />
          ))}
          {[12, 24, 36].map((y) => (
            <path key={y} d={`M${(y / 46) * 13.5} ${y} H${60 - (y / 46) * 13.5}`} stroke="#fff" strokeWidth="2" />
          ))}
        </svg>
        {swishKey > 0 && (
          <div key={`s${swishKey}`} className="swish-text">
            SWISH!
          </div>
        )}
      </div>

      {ROSTER.map((r) => {
        const isActive = active.has(r.agent);
        const isDone = done.has(r.agent);
        const b = bubbles[r.agent];
        return (
          <div
            key={r.agent}
            className={`player ${isActive ? "active" : ""} ${isDone ? "done" : ""} ${shooter === r.agent ? "shooting" : ""}`}
            style={{ left: `${r.spot.x}%`, top: `${r.spot.y}%`, zIndex: Math.round(r.spot.y) }}
            title={`${r.nickname}: ${r.role}. ${r.blurb}`}
          >
            {b && (
              <div className={`bubble bubble-${r.bubble} bubble-${b.kind}`}>
                <span>{b.text}</span>
              </div>
            )}
            <PlayerSprite look={r.look} />
            <div className="nameplate">
              <span className={`light ${isActive ? "on" : isDone ? "done" : ""}`} />
              <strong>{r.role}</strong>
              <em>{r.nickname} #{r.look.number}</em>
            </div>
          </div>
        );
      })}

      {ball && (
        <div
          ref={ballRef}
          className="court-ball"
          style={{ left: `${ball.at.x}%`, top: `${ball.at.y}%`, transform: "translate(-50%,-50%)" }}
        >
          <Basketball label={ball.ticketId} />
        </div>
      )}
    </div>
  );
});

/** Outdoor court: sky, New Haven-ish skyline, trees, chain-link fence, asphalt court. */
function CourtScene() {
  return (
    <svg className="scene" viewBox="0 0 1000 520" preserveAspectRatio="none" aria-hidden>
      <defs>
        <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#5ec8ff" />
          <stop offset="1" stopColor="#bfeaff" />
        </linearGradient>
        <linearGradient id="asphalt" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#24456e" />
          <stop offset="1" stopColor="#163052" />
        </linearGradient>
        <pattern id="fence" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <path d="M0 0 V14 M0 0 H14" stroke="rgba(255,255,255,.35)" strokeWidth="1.4" />
        </pattern>
      </defs>
      <rect width="1000" height="200" fill="url(#sky)" />
      <circle cx="120" cy="58" r="30" fill="#fff3a6" />
      {/* pixel clouds */}
      <g fill="#fff">
        <rect x="300" y="40" width="80" height="16" />
        <rect x="316" y="28" width="44" height="14" />
        <rect x="640" y="62" width="96" height="16" />
        <rect x="660" y="50" width="52" height="14" />
      </g>
      {/* skyline: gothic tower + campus buildings (stylised, not a real map) */}
      <g fill="#3d5a80">
        <rect x="40" y="120" width="90" height="80" />
        <rect x="150" y="100" width="60" height="100" />
        <rect x="236" y="70" width="34" height="130" />
        <polygon points="236,70 253,36 270,70" />
        <rect x="246" y="56" width="14" height="14" fill="#5b7aa3" />
        <rect x="290" y="112" width="110" height="88" />
        <rect x="430" y="96" width="70" height="104" />
        <rect x="530" y="126" width="120" height="74" />
        <rect x="690" y="104" width="64" height="96" />
        <rect x="780" y="122" width="150" height="78" />
      </g>
      <g fill="#8fb3d9">
        {Array.from({ length: 26 }, (_, i) => (
          <rect key={i} x={52 + i * 34} y={140 + (i % 3) * 14} width="8" height="10" />
        ))}
      </g>
      {/* trees */}
      <g fill="#2e8b57">
        {[20, 200, 420, 610, 760, 960].map((x) => (
          <g key={x}>
            <rect x={x - 5} y="170" width="10" height="30" fill="#6b4226" />
            <rect x={x - 26} y="134" width="52" height="40" rx="6" />
            <rect x={x - 18} y="118" width="36" height="22" rx="6" />
          </g>
        ))}
      </g>
      {/* fence */}
      <rect x="0" y="150" width="1000" height="56" fill="url(#fence)" />
      <rect x="0" y="148" width="1000" height="4" fill="#9aa6b2" />
      {/* court */}
      <rect x="0" y="200" width="1000" height="320" fill="url(#asphalt)" />
      <g stroke="#f5f5f5" strokeWidth="4" fill="none" opacity=".9">
        <rect x="30" y="222" width="940" height="282" />
        <rect x="770" y="300" width="200" height="130" fill="rgba(255,210,63,.22)" />
        <circle cx="770" cy="365" r="60" />
        <path d="M970 236 C 600 250, 600 480, 970 492" />
        <path d="M30 300 A 70 70 0 0 1 30 430" />
      </g>
      <text x="380" y="380" className="court-text" fill="rgba(255,255,255,.14)">
        CAMPUS CUSTOMS
      </text>
      {/* hoop pole (backboard/rim/net are HTML overlays) */}
      <rect x="912" y="150" width="10" height="230" fill="#9aa6b2" />
      <rect x="896" y="376" width="42" height="10" fill="#6c7782" />
    </svg>
  );
}
