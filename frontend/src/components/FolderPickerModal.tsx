"use client";

import { useEffect, useState } from "react";
import { ChevronRight, Folder, Loader2, X, ArrowLeft } from "lucide-react";
import api from "@/lib/api";

interface DriveFolder {
  id: string;
  name: string;
}

interface BreadcrumbItem {
  id: string;
  name: string;
}

interface FolderPickerModalProps {
  open: boolean;
  onClose: () => void;
  onSelect: (folderId: string | null, folderName: string) => void;
}

export default function FolderPickerModal({
  open,
  onClose,
  onSelect,
}: FolderPickerModalProps) {
  const [folders, setFolders] = useState<DriveFolder[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [breadcrumbs, setBreadcrumbs] = useState<BreadcrumbItem[]>([
    { id: "root", name: "My Drive" },
  ]);

  const currentFolderId = breadcrumbs[breadcrumbs.length - 1].id;

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setError("");
    api
      .get(`/api/presentations/drive/folders?parent_id=${currentFolderId}`)
      .then(({ data }) => setFolders(data))
      .catch(() => setError("Failed to load folders."))
      .finally(() => setLoading(false));
  }, [open, currentFolderId]);

  if (!open) return null;

  const navigateInto = (folder: DriveFolder) => {
    setBreadcrumbs((prev) => [...prev, { id: folder.id, name: folder.name }]);
  };

  const navigateTo = (index: number) => {
    setBreadcrumbs((prev) => prev.slice(0, index + 1));
  };

  const handleSelectHere = () => {
    const current = breadcrumbs[breadcrumbs.length - 1];
    onSelect(current.id === "root" ? null : current.id, current.name);
  };

  const handleClose = () => {
    setBreadcrumbs([{ id: "root", name: "My Drive" }]);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-md rounded-xl border border-gray-700 bg-gray-900 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-700 px-5 py-4">
          <h2 className="text-base font-semibold text-white">
            Choose a folder
          </h2>
          <button
            onClick={handleClose}
            className="rounded-lg p-1 text-gray-400 transition hover:bg-gray-800 hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Breadcrumbs */}
        <div className="flex items-center gap-1 border-b border-gray-800 px-5 py-2 text-sm">
          {breadcrumbs.map((crumb, i) => (
            <span key={crumb.id} className="flex items-center gap-1">
              {i > 0 && <ChevronRight className="h-3 w-3 text-gray-500" />}
              <button
                onClick={() => navigateTo(i)}
                className={`rounded px-1 py-0.5 transition hover:bg-gray-800 ${
                  i === breadcrumbs.length - 1
                    ? "font-medium text-white"
                    : "text-gray-400"
                }`}
              >
                {crumb.name}
              </button>
            </span>
          ))}
        </div>

        {/* Folder list */}
        <div className="h-64 overflow-y-auto px-2 py-2">
          {loading ? (
            <div className="flex h-full items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
            </div>
          ) : error ? (
            <p className="p-3 text-center text-sm text-red-400">{error}</p>
          ) : folders.length === 0 ? (
            <p className="p-3 text-center text-sm text-gray-500">
              No subfolders here
            </p>
          ) : (
            folders.map((folder) => (
              <button
                key={folder.id}
                onClick={() => navigateInto(folder)}
                className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm text-gray-200 transition hover:bg-gray-800"
              >
                <Folder className="h-4 w-4 shrink-0 text-blue-400" />
                <span className="truncate">{folder.name}</span>
                <ChevronRight className="ml-auto h-4 w-4 shrink-0 text-gray-600" />
              </button>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-gray-700 px-5 py-3">
          {breadcrumbs.length > 1 ? (
            <button
              onClick={() => navigateTo(breadcrumbs.length - 2)}
              className="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm text-gray-400 transition hover:bg-gray-800 hover:text-white"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </button>
          ) : (
            <div />
          )}
          <button
            onClick={handleSelectHere}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700"
          >
            Select this folder
          </button>
        </div>
      </div>
    </div>
  );
}
