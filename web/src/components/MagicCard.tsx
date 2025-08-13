import { motion } from "framer-motion";
import { PropsWithChildren } from "react";

type MagicCardProps = PropsWithChildren<{
  className?: string;
}>;

export function MagicCard({ children, className }: MagicCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className={`rounded-xl border border-zinc-800 bg-zinc-900/60 shadow-xl backdrop-blur ${className ?? ""}`}
    >
      {children}
    </motion.div>
  );
}


