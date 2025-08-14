import { useEffect, useState } from "react";
import { MagicCard } from "./MagicCard";

type DocItem = {
  id: string;
  filename: string;
  status: string;
  page_count: number;
  last_read_page: number;
  uploaded_at: string;
};

type SidebarProps = {
  apiBase: string;
  activeId?: string | null;
  onSelect: (doc: DocItem) => void;
};

export function Sidebar({ apiBase, activeId, onSelect }: SidebarProps) {
  const [docs, setDocs] = useState<DocItem[]>([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${apiBase}/documents`);
      if (!res.ok) return;
      const data: DocItem[] = await res.json();
      setDocs(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const iv = setInterval(load, 3000);
    return () => clearInterval(iv);
  }, []);

  return (
    <aside className="w-full sm:w-72 shrink-0">
      <MagicCard className="p-3 sm:p-4 h-full">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold">Seus PDFs</h2>
          <button
            onClick={load}
            className="text-xs px-2 py-1 rounded-md bg-zinc-800 hover:bg-zinc-700 border border-zinc-700"
          >
            Atualizar
          </button>
        </div>
        <div className="space-y-2 max-h-[50vh] sm:max-h-[70vh] overflow-auto pr-1">
          {loading && docs.length === 0 && (
            <div className="text-sm text-zinc-500">Carregando…</div>
          )}
          {docs.map((d) => {
            const isActive = d.id === activeId;
            return (
              <button
                key={d.id}
                onClick={() => onSelect(d)}
                className={`w-full text-left p-3 rounded-lg border transition-colors ${
                  isActive
                    ? "border-indigo-500/60 bg-indigo-500/10"
                    : "border-zinc-800 bg-zinc-900/40 hover:bg-zinc-900/70"
                }`}
              >
                <div className="text-sm font-medium break-all">{d.filename}</div>
                <div className="mt-1 text-xs text-zinc-400 flex items-center justify-between">
                  <span>Status: {d.status}</span>
                  <span>{d.last_read_page} / {d.page_count || "?"}</span>
                </div>
                <div className="mt-1 h-1.5 w-full bg-zinc-800 rounded">
                  {d.page_count > 0 && (
                    <div
                      className="h-1.5 bg-indigo-500 rounded"
                      style={{ width: `${Math.min(100, Math.max(0, Math.round((d.last_read_page / d.page_count) * 100)))}%` }}
                    />
                  )}
                </div>
              </button>
            );
          })}
          {docs.length === 0 && !loading && (
            <div className="text-sm text-zinc-500">Nenhum PDF enviado ainda.</div>
          )}
        </div>
      </MagicCard>
    </aside>
  );
}


