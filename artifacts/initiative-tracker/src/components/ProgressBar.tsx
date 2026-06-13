import { cn } from "@/lib/utils";

function getColor(progress: number, status: string) {
  if (status === "completed") return "bg-blue-500";
  if (status === "delayed") return "bg-red-500";
  if (status === "at_risk") return "bg-amber-500";
  if (progress >= 70) return "bg-emerald-500";
  return "bg-primary";
}

export default function ProgressBar({
  progress,
  status,
  showLabel = true,
  className,
}: {
  progress: number;
  status?: string;
  showLabel?: boolean;
  className?: string;
}) {
  const color = getColor(progress, status ?? "");
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all", color)}
          style={{ width: `${progress}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-xs font-mono text-muted-foreground w-8 text-right shrink-0">
          {progress}%
        </span>
      )}
    </div>
  );
}
