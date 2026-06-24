import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Graphite — Network Operations Copilot",
  description:
    "AI-powered network digital twin for topology reasoning, fault simulation, and blast-radius analysis.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="font-sans">{children}</body>
    </html>
  );
}
