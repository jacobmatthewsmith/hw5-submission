import { useState } from "react";
import { money } from "../roster";
import type { Approval } from "../types";

const KIND: Record<Approval["kind"], { label: string; icon: string }> = {
  invoice_payment: { label: "Invoice payment", icon: "💵" },
  rent_payment: { label: "Rent payment", icon: "🏠" },
  purchase_order: { label: "Purchase order", icon: "📦" },
};

interface Props {
  pending: Approval[];
  approver: string;
  onApprover: (name: string) => void;
  onDecide: (a: Approval, decision: "approve" | "reject") => Promise<void>;
}

export function ApprovalDesk({ pending, approver, onApprover, onDecide }: Props) {
  const [busy, setBusy] = useState<number | null>(null);
  const ready = approver.trim().length > 0;

  const decide = async (a: Approval, d: "approve" | "reject") => {
    setBusy(a.id);
    try {
      await onDecide(a, d);
    } finally {
      setBusy(null);
    }
  };

  return (
    <section className="panel approvals">
      <h3 className="panel-title">Human Approval Desk</h3>
      <p className="panel-note">
        Agents only <em>request</em> payments and orders. Money moves only when a person clicks Approve.
      </p>
      <label className="approver">
        Your name
        <input value={approver} onChange={(e) => onApprover(e.target.value)} placeholder="e.g. Jacob" maxLength={60} />
      </label>
      {pending.length === 0 && <p className="empty">Nothing waiting for approval.</p>}
      <ul className="approval-list">
        {pending.map((a) => {
          const k = KIND[a.kind];
          return (
            <li key={a.id} className="approval">
              <div className="approval-head">
                <span className="approval-kind">
                  {k.icon} {k.label}
                </span>
                <span className="approval-amt">{money(a.amount)}</span>
              </div>
              <div className="approval-meta">
                Request #{a.id} · ticket #{a.ticket_id} · from {a.requested_by}
                {a.kind === "invoice_payment" && a.ref_id && <> · invoice #{a.ref_id}</>}
                {a.kind === "rent_payment" && a.ref_id && <> · lease {a.ref_id}</>}
                {a.kind === "purchase_order" && (
                  <>
                    {" "}· {a.qty} × {a.sku} {a.size} from vendor {a.vendor_id}
                  </>
                )}
              </div>
              {a.reason && <p className="approval-reason">{a.reason}</p>}
              {a.result_note && <p className="approval-refused">{a.result_note}</p>}
              <div className="approval-actions">
                <button className="btn approve" disabled={!ready || busy !== null} onClick={() => decide(a, "approve")}>
                  {busy === a.id ? "…" : a.kind === "purchase_order" ? "Approve order" : "Approve & pay"}
                </button>
                <button className="btn reject" disabled={!ready || busy !== null} onClick={() => decide(a, "reject")}>
                  Reject
                </button>
              </div>
            </li>
          );
        })}
      </ul>
      {!ready && pending.length > 0 && <p className="hint">Type your name to enable the buttons.</p>}
    </section>
  );
}
