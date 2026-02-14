import "./globals.css";
import { ReactNode } from "react";

export const metadata = {
  title: "COMMAND_CENTER",
  description: "Advanced Developer UI",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-black text-white antialiased h-screen overflow-hidden selection:bg-gray-700 selection:text-white">
        {children}
      </body>
    </html>
  );
}