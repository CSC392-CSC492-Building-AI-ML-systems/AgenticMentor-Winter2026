import "./globals.css";
import { ReactNode } from "react";
import AuthRedirectHandler from "@/components/auth/AuthRedirectHandler";
import ThemeProvider from "@/components/layout/ThemeProvider";

export const metadata = {
  title: "COMMAND_CENTER",
  description: "Advanced Developer UI",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Blocking script — runs before paint to avoid flash of wrong theme */}
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){var t=localStorage.getItem('theme');if(t==='dark'){document.documentElement.classList.add('dark');}else{document.documentElement.classList.remove('dark');}})();`,
          }}
        />
      </head>
      <body suppressHydrationWarning className="bg-white dark:bg-black text-black dark:text-white antialiased h-screen overflow-hidden selection:bg-gray-300 dark:selection:bg-gray-700 selection:text-black dark:selection:text-white">
        <ThemeProvider />
        <AuthRedirectHandler />
        {children}
      </body>
    </html>
  );
}