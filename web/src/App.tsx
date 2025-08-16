import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { MagicCard } from "./components/MagicCard";
import { ShinyButton } from "./components/ShinyButton";
import { countWordsInToken, endPunctuationMultiplier, complexityMultiplier } from "./lib/textUtils";
import { PDFOrTextViewer } from "./components/PDFOrTextViewer";
import { Sidebar } from "./components/Sidebar";
import { Toast } from "./components/Toast";

type UploadResponse = { document_id: string; status: string };
type StatusResponse = { status: string; word_count: number };

// Define a URL base da API. Se não houver VITE_API_BASE, usa o host atual com porta 8000.
const DEFAULT_API_BASE = `http://${window.location.hostname}:8000`;
const API_BASE = import.meta.env.VITE_API_BASE ?? DEFAULT_API_BASE;

export function App() {
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [words, setWords] = useState<string[]>([]);
  const [wpm, setWpm] = useState<number>(300);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentIndex, setCurrentIndex] = useState<number>(0);
  const [displayTokens, setDisplayTokens] = useState<string[]>([]);
  const [tokenPages, setTokenPages] = useState<number[]>([]);
  const [pageCount, setPageCount] = useState<number>(0);
  const [startPage, setStartPage] = useState<number>(1);
  const [showNextPreview, setShowNextPreview] = useState<boolean>(true);
  const [tokenWeights, setTokenWeights] = useState<number[]>([]);
  const [groupSize, setGroupSize] = useState<number>(1); // 1, 2 ou 3 tokens por tela
  const timerRef = useRef<number | null>(null);
  const [lastReadPage, setLastReadPage] = useState<number>(1);
  const [suppressProgressSync, setSuppressProgressSync] = useState<boolean>(false);
  const [toast, setToast] = useState<string | null>(null);
  const [currentMime, setCurrentMime] = useState<string | null>(null);
  const [lastTokenIndex, setLastTokenIndex] = useState<number>(0);
  const [startPageDirty, setStartPageDirty] = useState<boolean>(false);

  // Intervalo por palavra em ms
  // Duração base por palavra em ms
  const msPerWord = useMemo(() => Math.max(60_000 / Math.max(1, wpm), 50), [wpm]);

  // Regra: ponto final (.) deve encerrar a janela atual, independente do groupSize
  const isTerminalPeriod = useCallback((token: string | undefined): boolean => {
    if (!token) return false;
    const t = (token || "").trim();
    // Considera apenas ponto final simples "." (evita reticências "...")
    if (/\.\.\.$/.test(t)) return false;
    return /\.$/.test(t);
  }, []);

  // Determina quantos tokens devem ser exibidos a partir de startIndex
  const computeWindowSize = useCallback((startIndex: number): number => {
    if (startIndex < 0 || startIndex >= displayTokens.length) return 0;
    const maxWindow = Math.min(groupSize, displayTokens.length - startIndex);
    for (let offset = 0; offset < maxWindow; offset++) {
      const token = displayTokens[startIndex + offset];
      if (isTerminalPeriod(token)) return offset + 1;
    }
    return maxWindow;
  }, [displayTokens, groupSize, isTerminalPeriod]);

  // Determina o início da janela anterior ao currentIndex
  const computePreviousStartIndex = useCallback((index: number): number => {
    if (index <= 0) return 0;
    let countBack = 0;
    for (let i = index - 1; i >= 0 && countBack < groupSize; i--) {
      countBack += 1;
      if (isTerminalPeriod(displayTokens[i])) break;
    }
    return Math.max(0, index - countBack);
  }, [displayTokens, groupSize, isTerminalPeriod]);

  // Controle do player
  const tick = useCallback(() => {
    setCurrentIndex((idx) => {
      const step = computeWindowSize(idx);
      const nextIndex = idx + step;
      if (nextIndex >= displayTokens.length) {
        setIsPlaying(false);
        return idx;
      }
      return nextIndex;
    });
  }, [displayTokens.length, computeWindowSize]);

  useEffect(() => {
    if (!isPlaying || displayTokens.length === 0) {
      if (timerRef.current) window.clearTimeout(timerRef.current);
      return;
    }
    // Soma das durações dos tokens na janela atual considerando ponto final
    const windowSize = computeWindowSize(currentIndex);
    let duration = 0;
    for (let offset = 0; offset < windowSize; offset++) {
      const token = displayTokens[currentIndex + offset];
      if (!token) break;
      const weight = tokenWeights[currentIndex + offset] ?? countWordsInToken(token);
      duration += msPerWord * Math.max(1, weight) * endPunctuationMultiplier(token) * complexityMultiplier(token);
    }
    if (timerRef.current) window.clearTimeout(timerRef.current);
    timerRef.current = window.setTimeout(tick, duration);
    return () => {
      if (timerRef.current) window.clearTimeout(timerRef.current);
    };
  }, [isPlaying, msPerWord, tick, displayTokens, tokenWeights, currentIndex, computeWindowSize]);

  const onUpload = async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/documents`, { method: "POST", body: form });
    if (!res.ok) throw new Error("Falha ao enviar PDF");
    const data: UploadResponse = await res.json();
    setDocumentId(data.document_id);
    setStatus({ status: data.status, word_count: 0 });
    setCurrentMime(file.type || null);
    setWords([]);
    setDisplayTokens([]);
    setCurrentIndex(0);
    setStartPage(1);
    setLastReadPage(1);
    setSuppressProgressSync(false);
  };

  // Polling do status e fetch das palavras
  useEffect(() => {
    if (!documentId) return;
    let stop = false;
    const iv = setInterval(async () => {
      try {
        const sres = await fetch(`${API_BASE}/documents/${documentId}/status`);
        if (!sres.ok) return;
        const sdata: StatusResponse = await sres.json();
        setStatus(sdata);
        if (sdata.status === "completed") {
          const wres = await fetch(`${API_BASE}/documents/${documentId}/words`);
          if (wres.ok) {
            const wdata: { words: string[] } = await wres.json();
            if (!stop) setWords(wdata.words);
          }
          clearInterval(iv);
        }
      } catch {}
    }, 1000);
    return () => {
      stop = true;
      clearInterval(iv);
    };
  }, [documentId]);

  // Após completed, buscar tokens do backend
  useEffect(() => {
    if (!documentId || status?.status !== "completed") return;
    let cancelled = false;
    // Evita sincronizar progresso enquanto inicializa novo documento
    setSuppressProgressSync(true);
    (async () => {
      try {
        const tres = await fetch(`${API_BASE}/documents/${documentId}/tokens`);
        if (tres.ok) {
          const tdata: { tokens: string[]; pages?: number[]; page_count?: number; weights?: number[] } = await tres.json();
          if (!cancelled) {
            setDisplayTokens(tdata.tokens);
            setTokenPages(tdata.pages ?? []);
            setPageCount(tdata.page_count ?? 0);
            setTokenWeights(tdata.weights ?? Array(tdata.tokens.length).fill(1));
            // prioridade: token salvo > startPage > início
            if (lastTokenIndex > 0 && lastTokenIndex < (tdata.tokens?.length ?? 0)) {
              setCurrentIndex(lastTokenIndex);
            } else if (startPage > 1 && (tdata.pages?.length ?? 0) > 0) {
              const idx = (tdata.pages ?? []).findIndex((p) => p >= startPage);
              setCurrentIndex(Math.max(0, idx));
            } else {
              setCurrentIndex(0);
            }
            // Libera sincronização após um micro delay para garantir currentIndex aplicado
            setTimeout(() => setSuppressProgressSync(false), 0);
            setToast("Documento carregado");
          }
        } else {
          setToast("Carregando do cache/arquivo...");
        }
      } catch {}
    })();
    return () => {
      cancelled = true;
    };
  }, [documentId, status?.status, startPage, lastTokenIndex]);

  // Salto para página inicial selecionada
  useEffect(() => {
    if (!tokenPages.length) return;
    if (lastTokenIndex > 0 && !startPageDirty) return;
    const idx = tokenPages.findIndex((p) => p >= startPage);
    if (idx >= 0) {
      setCurrentIndex(idx);
      if (documentId && startPageDirty) {
        const ctrl = new AbortController();
        fetch(`${API_BASE}/documents/${documentId}/progress?page=${tokenPages[idx]}&token_index=${idx}`,
          { method: "POST", signal: ctrl.signal }).catch(() => {});
        setStartPageDirty(false);
        setLastTokenIndex(0);
      }
    }
  }, [startPage, tokenPages, lastTokenIndex, startPageDirty, documentId]);

  // Atualiza progresso de página lida
  useEffect(() => {
    const currentPage = tokenPages[currentIndex] ?? 1;
    setLastReadPage(currentPage);
    if (!documentId) return;
    if (suppressProgressSync) return;
    const ctrl = new AbortController();
    const timeout = setTimeout(() => {
      fetch(`${API_BASE}/documents/${documentId}/progress?page=${currentPage}&token_index=${currentIndex}`, { method: "POST", signal: ctrl.signal }).catch(() => {});
    }, 300);
    return () => { clearTimeout(timeout); ctrl.abort(); };
  }, [currentIndex, tokenPages, documentId, suppressProgressSync]);

  const currentWord = useMemo(() => {
    const size = computeWindowSize(currentIndex);
    const windowTokens = displayTokens.slice(currentIndex, currentIndex + size);
    return windowTokens.join(" ");
  }, [displayTokens, currentIndex, computeWindowSize]);

  return (
    <div className="container mx-auto px-4 py-6 sm:py-8">
      {toast && <Toast message={toast} onClose={() => setToast(null)} />}
      <header className="mb-8">
        <h1 className="text-2xl font-semibold">Leitor Rápido</h1>
        <p className="text-zinc-400">Envie um PDF e reproduza as palavras no ritmo desejado (PPM).</p>
      </header>

      <div className="grid gap-6 sm:grid-cols-[1fr] lg:grid-cols-[18rem_1fr]">
        <div className="order-2 lg:order-1">
          <Sidebar
            apiBase={API_BASE}
            activeId={documentId}
            onSelect={(doc) => {
              setDocumentId(doc.id);
              setStartPage(Math.max(1, (doc as any).last_read_page || 1));
              setCurrentMime((doc as any).mime_type ?? null);
              setLastTokenIndex((doc as any).last_token_index ?? 0);
            }}
            onDeleted={(docId) => {
              if (documentId === docId) {
                setDocumentId(null);
                setStatus(null);
                setWords([]);
                setDisplayTokens([]);
                setTokenPages([]);
                setPageCount(0);
                setCurrentIndex(0);
                setStartPage(1);
                setCurrentMime(null);
              }
            }}
          />
        </div>
        <div className="order-1 lg:order-2">
      <div className="grid gap-6">
        <MagicCard className="p-6">
          <div className="flex items-center gap-4">
            <input
              id="file"
              type="file"
              accept="application/pdf,text/plain,text/markdown,application/epub+zip,.txt,.md,.epub"
              className="block w-full text-sm text-zinc-300 file:mr-4 file:rounded-md file:border-0 file:bg-zinc-800 file:px-4 file:py-2 file:text-zinc-100 hover:file:bg-zinc-700"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) onUpload(f).catch(() => alert("Falha no upload"));
              }}
            />
          </div>
          <div className="mt-4 text-sm text-zinc-400">
            {documentId && (
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-3 sm:items-center">
                <span className="break-all">ID: {documentId}</span>
                <span>Status: {status?.status ?? "-"}</span>
                <span>Palavras: {status?.word_count ?? 0}</span>
              </div>
            )}
          </div>
        </MagicCard>

        <MagicCard className="p-6">
          <div className="flex flex-col items-center gap-4">
            <div className="text-3xl sm:text-5xl font-bold min-h-[3.5rem] sm:min-h-[5rem] flex items-center justify-center text-center break-words px-2">
              {currentWord || "—"}
            </div>
            {showNextPreview && (
              <div className="text-sm text-zinc-500 mt-1 px-2 text-center break-words">
                {(() => {
                  const currentSize = computeWindowSize(currentIndex);
                  const nextStart = currentIndex + currentSize;
                  const nextSize = computeWindowSize(nextStart);
                  const nextTokens = displayTokens.slice(nextStart, nextStart + nextSize);
                  const nextText = nextTokens.length ? nextTokens.join(" ") : "—";
                  return <>Próxima: {nextText}</>;
                })()}
              </div>
            )}
            <div className="grid w-full gap-3 sm:gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-1 sm:gap-2">
                <label htmlFor="wpm" className="text-sm text-zinc-400">PPM</label>
                <input
                  id="wpm"
                  type="number"
                  min={60}
                  max={1200}
                  step={10}
                  value={wpm}
                  onChange={(e) => setWpm(Number(e.target.value))}
                  className="w-full sm:w-28 rounded-md bg-zinc-800 px-3 py-2 text-zinc-100 outline-none ring-1 ring-inset ring-zinc-700 focus:ring-2"
                />
              </div>
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-1 sm:gap-2">
                <label htmlFor="groupSize" className="text-sm text-zinc-400">Palavras por tela</label>
                <select
                  id="groupSize"
                  value={groupSize}
                  onChange={(e) => setGroupSize(Number(e.target.value))}
                  className="w-full sm:w-auto rounded-md bg-zinc-800 px-3 py-2 text-zinc-100 outline-none ring-1 ring-inset ring-zinc-700 focus:ring-2"
                >
                  <option value={1}>1</option>
                  <option value={2}>2</option>
                  <option value={3}>3</option>
                </select>
              </div>
              <div className="flex items-center gap-2">
                <label htmlFor="preview" className="text-sm text-zinc-400">Preview</label>
                <input
                  id="preview"
                  type="checkbox"
                  checked={showNextPreview}
                  onChange={(e) => setShowNextPreview(e.target.checked)}
                  className="h-4 w-4"
                />
              </div>
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-1 sm:gap-2">
                <label htmlFor="startPage" className="text-sm text-zinc-400">Página inicial</label>
                <input
                  id="startPage"
                  type="number"
                  min={1}
                  max={Math.max(1, pageCount)}
                  value={startPage}
                  onChange={(e) => { setStartPage(Number(e.target.value)); setStartPageDirty(true); setLastTokenIndex(0); }}
                  className="w-full sm:w-28 rounded-md bg-zinc-800 px-3 py-2 text-zinc-100 outline-none ring-1 ring-inset ring-zinc-700 focus:ring-2"
                />
              </div>
              <div className="flex items-center gap-2 sm:col-span-2 lg:col-span-3 justify-center sm:justify-start">
                <ShinyButton onClick={() => setIsPlaying((p) => !p)}>
                  {isPlaying ? "Pausar" : "Reproduzir"}
                </ShinyButton>
                <ShinyButton variant="secondary" onClick={() => setCurrentIndex((i) => computePreviousStartIndex(i))}>
                  « Anterior
                </ShinyButton>
                <ShinyButton variant="secondary" onClick={() => setCurrentIndex((i) => {
                  const step = computeWindowSize(i);
                  return Math.min(displayTokens.length - 1, i + step);
                })}>
                  Próxima »
                </ShinyButton>
                <ShinyButton variant="secondary" onClick={() => { setCurrentIndex(0); setIsPlaying(false); }}>
                  Reiniciar
                </ShinyButton>
              </div>
            </div>
            <div className="w-full text-sm text-zinc-400">
              Posição: {displayTokens.length ? `${currentIndex + 1} / ${displayTokens.length}` : "-"}
            </div>
          </div>
        </MagicCard>

        {documentId && (
          <MagicCard className="p-2">
            <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-2 text-sm text-zinc-400">
              <div>Página atual: {tokenPages[currentIndex] ?? 1} / {pageCount || "?"}</div>
              <div>Visualização</div>
            </div>
            <PDFOrTextViewer
              type={currentMime ?? undefined}
              url={`${API_BASE}/documents/${documentId}/file`}
              page={tokenPages[currentIndex] ?? 1}
            />
          </MagicCard>
        )}
      </div>
        </div>
      </div>
    </div>
  );
}


