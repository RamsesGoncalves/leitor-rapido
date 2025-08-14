import { PDFViewer } from "./PDFViewer";

type Props = {
  type: string | null | undefined;
  url: string;
  page: number;
};

export function PDFOrTextViewer({ type, url, page }: Props) {
  if (type === "application/pdf" || type === undefined || type === null) {
    return <PDFViewer url={url} page={page} className="w-full h-auto" />;
  }
  // Placeholder para tipos não-PDF
  return (
    <div className="p-4 text-sm text-zinc-400">
      Visualização não disponível para este tipo. A leitura sequencial está habilitada acima.
    </div>
  );
}


