import { useEffect, useState } from "react";
import StatusBadge from "./StatusBadge";
import api from "../services/api";

export default function TaskDetailModal({ task, onClose }) {
  const [transcript, setTranscript] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (task.status !== "completed") return;
    setLoading(true);
    api
      .get(`/tasks/${task.id}/transcript`)
      .then(({ data }) => setTranscript(data))
      .catch(() => setTranscript(null))
      .finally(() => setLoading(false));
  }, [task.id, task.status]);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 p-6 max-h-[80vh] overflow-y-auto">
        <div className="flex items-start justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Task Detail</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none cursor-pointer"
          >
            &times;
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-xs font-medium text-gray-500 uppercase">
              URL
            </label>
            <p className="text-sm text-gray-900 break-all">{task.reel_url}</p>
          </div>

          <div>
            <label className="text-xs font-medium text-gray-500 uppercase">
              Status
            </label>
            <div className="mt-1">
              <StatusBadge status={task.status} />
            </div>
          </div>

          {task.status === "failed" && task.error_message && (
            <div>
              <label className="text-xs font-medium text-gray-500 uppercase">
                Error
              </label>
              <p className="text-sm text-red-600 mt-1">{task.error_message}</p>
            </div>
          )}

          {task.status === "completed" && (
            <>
              {loading ? (
                <p className="text-sm text-gray-500">Loading transcript...</p>
              ) : transcript ? (
                <>
                  <div>
                    <label className="text-xs font-medium text-gray-500 uppercase">
                      Language
                    </label>
                    <div className="mt-1">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
                        {transcript.language || "unknown"}
                      </span>
                    </div>
                  </div>

                  {transcript.topics && transcript.topics.length > 0 && (
                    <div>
                      <label className="text-xs font-medium text-gray-500 uppercase">
                        Topics
                      </label>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {transcript.topics.map((topic) => (
                          <span
                            key={topic}
                            className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700"
                          >
                            {topic}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  <div>
                    <label className="text-xs font-medium text-gray-500 uppercase">
                      Transcript
                    </label>
                    <div className="mt-1 p-3 bg-gray-50 rounded-md text-sm text-gray-800 whitespace-pre-wrap max-h-60 overflow-y-auto">
                      {transcript.transcript}
                    </div>
                  </div>
                </>
              ) : (
                <p className="text-sm text-gray-500">
                  Transcript unavailable.
                </p>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
