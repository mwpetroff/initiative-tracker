import { cn } from "@/lib/utils";

type Status = "on_track" | "at_risk" | "delayed" | "completed" | "not_started";

const config: Record<Status, { label: string; className: string }> = {
  on_track:    { label: "On Track",    className: "bg-emerald-100 text-emerald-800 border-emerald-200" },
  at_risk:     { label: "At Risk",     className: "bg-amber-100 text-amber-800 border-amber-200" },
  delayed:     { label: "Delayed",     className: "bg-red-100 text-red-800 border-red-200" },
  completed:   { label: "Completed",   className: "bg-blue-100 text-blue-800 border-blue-200" },
  not_started: { label: "Not Started", className: "bg-slate-100 text-slate-600 border-slate-200" },
};

export default function StatusBadge({ status, size = "sm" }: { status: string; size?: "xs" | "sm" }) {
  const s = (config[status as Status] ?? { label: status, className: "bg-slate-100 text-slate-600 border-slate-200" });
  return (
    <span
      className={cn(
        "inline-flex items-center border font-medium rounded",
        size === "xs" ? "px-1.5 py-0.5 text-xs" : "px-2 py-0.5 text-xs",
        s.className
      )}
    >
      {s.label}
    </span>
  );
}

const dotColor: Record<Status, string> = {
  on_track:    "bg-emerald-500",
  at_risk:     "bg-amber-500",
  delayed:     "bg-red-500",
  completed:   "bg-blue-500",
  not_started: "bg-slate-400",
};

export function StatusDot({ status }: { status: string }) {
  const color = dotColor[status as Status] ?? "bg-slate-400";
  return <span className={cn("inline-block w-2 h-2 rounded-full shrink-0", color)} />;
}
