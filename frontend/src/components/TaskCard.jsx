import StatusBadge from "./StatusBadge";
import api from "../services/api";

function timeAgo(dateStr) {
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function truncateUrl(url, maxLen = 45) {
  return url.length > maxLen ? url.slice(0, maxLen) + "..." : url;
}

export default function TaskCard({ task, onSelect, onRefresh }) {
  const canCancel = ["pending", "processing"].includes(task.status);

  const handleCancel = async (e) => {
    e.stopPropagation();
    try {
      await api.post(`/tasks/${task.id}/cancel`);
      onRefresh();
    } catch {
      // ignore — task may already be terminal
    }
  };

  return (
    <div
      onClick={() => onSelect(task)}
      className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-gray-900 truncate">
            {truncateUrl(task.reel_url)}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            {timeAgo(task.created_at)}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <StatusBadge status={task.status} />
          {canCancel && (
            <button
              onClick={handleCancel}
              className="text-xs text-red-500 hover:text-red-700 cursor-pointer"
            >
              Cancel
            </button>
          )}
        </div>
      </div>
      {task.status === "failed" && task.error_message && (
        <p className="mt-2 text-xs text-red-600 truncate">
          {task.error_message}
        </p>
      )}
    </div>
  );
}
