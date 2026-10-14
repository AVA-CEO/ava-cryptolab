"use client";
import { ThemeProvider, useTheme } from "next-themes";
import { MotionConfig } from "motion/react";
import { Toaster } from "sonner";
export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
      <MotionConfig reducedMotion="user">
        {children}
        <Notifications />
      </MotionConfig>
    </ThemeProvider>
  );
}

function Notifications() {
  const { resolvedTheme } = useTheme();
  return (
    <Toaster
      theme={resolvedTheme === "light" ? "light" : "dark"}
      position="bottom-right"
      richColors
    />
  );
}
