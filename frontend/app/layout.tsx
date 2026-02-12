import "./globals.css"
import { ReactNode } from "react"

export const metadata = {
  title: "Agentic Project Mentor",
  description: "Multi-Agent Project Planning Platform",
}

export default function RootLayout({
  children,
}: {
  children: ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900">
        {children}
      </body>
    </html>
  )
}
