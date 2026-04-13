import { clsx } from "clsx";

export function Card({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={clsx("bg-zinc-900 border border-zinc-800 rounded-lg p-4", className)}>
      {children}
    </div>
  );
}

export function StatCard({
  label,
  value,
  unit,
  accent,
}: {
  label: string;
  value: string | number;
  unit?: string;
  accent?: boolean;
}) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
      <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1">{label}</p>
      <p className={clsx("text-2xl font-semibold tabular-nums", accent ? "text-sky-400" : "text-zinc-100")}>
        {value}
        {unit && <span className="text-sm text-zinc-500 ml-1">{unit}</span>}
      </p>
    </div>
  );
}
