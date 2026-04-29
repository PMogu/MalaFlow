import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MalaFlow",
  description: "Campus pilot workspace for AI assistant restaurant orders near Unimelb"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
