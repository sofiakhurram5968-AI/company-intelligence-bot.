import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Company Intelligence",
  description: "Analyze any company's public website for structured business data.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
