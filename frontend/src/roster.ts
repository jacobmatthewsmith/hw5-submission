import type { AgentName } from "./types";

/** Fictional cartoon players, one per agent. Not based on real people. */
export interface PlayerLook {
  skin: string;
  hair: "gray-afro" | "short-fade" | "bun-glasses" | "bald-beard" | "high-ponytail";
  hairColor: string;
  jersey: string;
  trim: string;
  number: number;
  glasses?: boolean;
  beard?: string;
  headband?: string;
}

export interface RosterEntry {
  agent: AgentName;
  nickname: string;
  role: string;
  blurb: string;
  look: PlayerLook;
  /** Spot on the court, in % of the court box (feet position). */
  spot: { x: number; y: number };
  /** Which side the speech bubble opens to. */
  bubble: "left" | "right";
}

export const ROSTER: RosterEntry[] = [
  {
    agent: "boss",
    nickname: "Coach Gloria",
    role: "Boss",
    blurb: "Reads the ticket, routes it, makes the final call",
    look: { skin: "#7a4a2a", hair: "gray-afro", hairColor: "#d9d9d9", jersey: "#00356b", trim: "#ffd23f", number: 1 },
    spot: { x: 50, y: 58 },
    bubble: "right",
  },
  {
    agent: "inventory",
    nickname: "Kenji",
    role: "Inventory",
    blurb: "Stock by SKU and size, shortfalls, restock vendors",
    look: { skin: "#f1c9a0", hair: "short-fade", hairColor: "#1b1b1b", jersey: "#286dc0", trim: "#ffffff", number: 23, headband: "#ff5d73" },
    spot: { x: 22, y: 40 },
    bubble: "right",
  },
  {
    agent: "accounting",
    nickname: "Priya",
    role: "Accounting",
    blurb: "Cash, invoices, margins; files payments for approval",
    look: { skin: "#a8673f", hair: "bun-glasses", hairColor: "#2b1a12", jersey: "#3a9d5d", trim: "#ffffff", number: 8, glasses: true },
    spot: { x: 30, y: 82 },
    bubble: "right",
  },
  {
    agent: "facilities",
    nickname: "Walt",
    role: "Facilities",
    blurb: "Lease and rent for the Chapel Street shop",
    look: { skin: "#f6d3bd", hair: "bald-beard", hairColor: "#bdbdbd", jersey: "#e07a1f", trim: "#ffffff", number: 44, beard: "#c9c9c9" },
    spot: { x: 8, y: 66 },
    bubble: "right",
  },
  {
    agent: "customer_service",
    nickname: "Luz",
    role: "Customer Service",
    blurb: "Writes customer drafts (never sent)",
    look: { skin: "#c68a5c", hair: "high-ponytail", hairColor: "#4a2a17", jersey: "#9b4dca", trim: "#ffd23f", number: 11 },
    spot: { x: 68, y: 84 },
    bubble: "left",
  },
];

export const BY_AGENT = Object.fromEntries(ROSTER.map((r) => [r.agent, r])) as Record<AgentName, RosterEntry>;

/** Hoop position (rim center) in % of the court box. */
export const HOOP = { x: 88, y: 30 };

export const TICKET_TYPE_LABEL: Record<string, string> = {
  customer_order: "Customer order",
  rent_notice: "Rent notice",
  price_override: "Price override",
};

export const NEED_LABEL: Record<string, string> = {
  route: "routes the ticket",
  stock_or_vendor_check: "stock / vendor check",
  payment_or_po_request: "payment / PO request",
  margin_or_cash_review: "margin / cash review",
  lease_or_rent_check: "lease / rent check",
  customer_draft: "customer draft",
};

export const money = (n: number) =>
  n.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });
