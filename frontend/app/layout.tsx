import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Card Creator — Mundial 2026",
  description:
    "Genera tu tarjeta de jugador personalizada: tu rostro, tus datos, el uniforme de tu selección.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
