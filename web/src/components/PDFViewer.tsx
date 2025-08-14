import { useEffect, useRef } from "react";
import { getDocument, GlobalWorkerOptions } from "pdfjs-dist";
import workerSrc from "pdfjs-dist/build/pdf.worker.min.mjs?url";

// Configura worker (ESM)
// @ts-ignore
GlobalWorkerOptions.workerSrc = workerSrc;

type PDFViewerProps = {
  url: string;
  page: number; // 1-based
  className?: string;
};

export function PDFViewer({ url, page, className }: PDFViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    let pdfDoc: any = null;
    let currentRenderTask: any = null;

    const render = async () => {
      try {
        if (!pdfDoc) {
          pdfDoc = await getDocument({ url }).promise;
        }
        if (cancelled) return;
        const safePage = Math.min(Math.max(page, 1), pdfDoc.numPages);
        const pdfPage = await pdfDoc.getPage(safePage);
        if (cancelled) return;

        const canvas = canvasRef.current;
        const container = containerRef.current;
        if (!canvas || !container) return;
        const context = canvas.getContext("2d");
        if (!context) return;

        const dpr = Math.max(1, window.devicePixelRatio || 1);
        const containerWidth = container.clientWidth || 0;
        // Base viewport to compute scale-to-fit-width
        const baseViewport = pdfPage.getViewport({ scale: 1 });
        const cssScale = containerWidth > 0 ? containerWidth / baseViewport.width : 1.5;
        const viewport = pdfPage.getViewport({ scale: cssScale * dpr });

        // Set internal pixel size for crisp rendering on retina
        canvas.width = Math.floor(viewport.width);
        canvas.height = Math.floor(viewport.height);
        // Set CSS size (display size in CSS pixels)
        canvas.style.width = `${Math.floor(viewport.width / dpr)}px`;
        canvas.style.height = `${Math.floor(viewport.height / dpr)}px`;

        if (currentRenderTask && currentRenderTask.cancel) {
          try { currentRenderTask.cancel(); } catch {}
        }
        currentRenderTask = pdfPage.render({ canvasContext: context as any, viewport });
        await currentRenderTask.promise;
      } catch (e) {
        // noop
      }
    };

    const ResizeObserverImpl = (window as any).ResizeObserver as
      | (new (...args: any[]) => { observe: (el: Element) => void; unobserve: (el: Element) => void; disconnect?: () => void })
      | undefined;
    const ro = ResizeObserverImpl ? new ResizeObserverImpl(() => { render(); }) : null;

    (async () => {
      await render();
      if (containerRef.current && ro) ro.observe(containerRef.current);
      // Fallback ou complemento para mudanças de viewport
      window.addEventListener("resize", render);
    })();

    return () => {
      cancelled = true;
      if (ro && containerRef.current) {
        try { ro.unobserve(containerRef.current); } catch {}
      }
      try { window.removeEventListener("resize", render); } catch {}
      if (currentRenderTask && currentRenderTask.cancel) {
        try { currentRenderTask.cancel(); } catch {}
      }
      if ((pdfDoc as any)?.destroy) {
        try {
          (pdfDoc as any).destroy();
        } catch {}
      }
    };
  }, [url, page]);

  return (
    <div ref={containerRef} className={className}>
      <canvas ref={canvasRef} className="w-full h-auto" />
    </div>
  );
}


