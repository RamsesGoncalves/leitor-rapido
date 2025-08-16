import { useEffect, useState } from "react";

type ToastProps = {
  message: string;
  duration?: number;
  onClose?: () => void;
};

export function Toast({ message, duration = 2000, onClose }: ToastProps) {
  const [visible, setVisible] = useState(true);
  useEffect(() => {
    const t = setTimeout(() => { setVisible(false); onClose?.(); }, duration);
    return () => clearTimeout(t);
  }, [duration, onClose]);
  if (!visible) return null;
  return <div className="toast">{message}</div>;
}


