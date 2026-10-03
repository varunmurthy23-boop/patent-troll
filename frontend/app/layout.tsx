import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Patent Troll",
  description: "Software invention intake, prior art search, and patentability analysis"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
