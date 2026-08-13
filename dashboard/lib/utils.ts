import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Junta classes do Tailwind resolvendo conflitos -- utilitario padrao do shadcn. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
