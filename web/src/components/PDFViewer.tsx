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

  useEffect(() => {
    let cancelled = false;
    let pdfDoc: any = null;

    (async () => {
      try {
        pdfDoc = await getDocument({ url }).promise;
        if (cancelled) return;
        const safePage = Math.min(Math.max(page, 1), pdfDoc.numPages);
        const pdfPage = await pdfDoc.getPage(safePage);
        if (cancelled) return;
        const viewport = pdfPage.getViewport({ scale: 1.5 });
        const canvas = canvasRef.current;
        if (!canvas) return;
        const context = canvas.getContext("2d");
        if (!context) return;
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        await pdfPage.render({ canvasContext: context as any, viewport }).promise;
      } catch (e) {
        // noop
      }
    })();

    return () => {
      cancelled = true;
      if ((pdfDoc as any)?.destroy) {
        try {
          (pdfDoc as any).destroy();
        } catch {}
      }
    };
  }, [url, page]);

  return <canvas ref={canvasRef} className={className} />;
}


