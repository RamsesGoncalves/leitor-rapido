import { motion } from "framer-motion";
import { ButtonHTMLAttributes } from "react";

type ShinyButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary";
};

export function ShinyButton({ variant = "primary", className, ...props }: ShinyButtonProps) {
  const base =
    "px-4 py-2 rounded-lg font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-zinc-900";
  const variants = {
    primary:
      "bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 text-white hover:opacity-95",
    secondary:
      "bg-zinc-800 text-zinc-100 hover:bg-zinc-700 border border-zinc-700",
  } as const;
  return (
    <motion.button whileTap={{ scale: 0.98 }} className={`${base} ${variants[variant]} ${className ?? ""}`} {...props} />
  );
}


