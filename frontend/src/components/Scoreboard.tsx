import { useEffect, useRef, useState } from "react";
import { money } from "../roster";
import type { Cash } from "../types";

export function Scoreboard({ cash }: { cash: Cash | null }) {
  const prev = useRef<number | null>(null);
  const [delta, setDelta] = useState<{ amount: number; key: number } | null>(null);

  useEffect(() => {
    if (!cash) return;
    if (prev.current !== null && cash.balance !== prev.current) {
      setDelta({ amount: cash.balance - prev.current, key: Date.now() });
    }
    prev.current = cash.balance;
  }, [cash]);

  return (
    <div className="scoreboard" aria-live="polite">
      <div className="sb-label">CHECKING</div>
      <div className="sb-digits">{cash ? money(cash.balance) : "----"}</div>
      {delta && (
        <div key={delta.key} className={`sb-delta ${delta.amount < 0 ? "down" : "up"}`}>
          {delta.amount < 0 ? "−" : "+"}
          {money(Math.abs(delta.amount))}
        </div>
      )}
      {cash && (
        <div className="sb-sub">
          <span>Pending {money(cash.pending_payment_requests)}</span>
          <span>Left if approved {money(cash.available_after_pending)}</span>
          <span>Shop date {cash.shop_today}</span>
        </div>
      )}
    </div>
  );
}
