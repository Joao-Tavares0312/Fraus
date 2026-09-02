"use client";

/**
 * O reveal por rolagem da LP — o mesmo gesto da entrada de sistemas da
 * dashboard (whileInView + once, 8px, 200ms), reaproveitando o vocabulário de
 * lib/movimento. A LP é vitrine e tem licença para usá-lo em cada seção; o
 * `MotionConfig reducedMotion="user"` do layout raiz desliga tudo para quem
 * pediu menos movimento.
 */

import { motion } from "motion/react";
import type { ReactNode } from "react";
import { entradaDeSistema } from "@/lib/movimento";

export function Revelar({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <motion.div
      className={className}
      variants={entradaDeSistema}
      initial="oculto"
      whileInView="presente"
      viewport={{ once: true, margin: "-60px" }}
    >
      {children}
    </motion.div>
  );
}
