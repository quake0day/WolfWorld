import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "WolfWorld · Video to 3D Worlds",
  description: "Reconstruct 3D scenes from phone videos and explore them freely in your browser.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
