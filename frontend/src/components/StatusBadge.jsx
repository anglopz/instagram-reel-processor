const STATUS_STYLES = {
  pending: "bg-yellow-500/10 text-yellow-500 border border-yellow-500/20",
  processing: "bg-blue-500/10 text-blue-400 border border-blue-500/20",
  completed: "bg-green-500/10 text-green-500 border border-green-500/20",
  failed: "bg-red-500/10 text-red-400 border border-red-500/20",
  cancelled: "bg-zinc-500/10 text-zinc-500 border border-zinc-500/20",
};

export default function StatusBadge({ status }) {
  const style = STATUS_STYLES[status] || "bg-zinc-500/10 text-zinc-500 border border-zinc-500/20";
  const isProcessing = status === "processing";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium font-mono uppercase tracking-wider ${style}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full bg-current ${isProcessing ? "animate-pulse" : ""}`} />
      {status}
    </span>
  );
}
