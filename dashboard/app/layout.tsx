export const metadata = {
  title: "HSCL Capstone Dashboard",
  description: "Live monitoring for the Multi-Agent Research Team",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ background: "#0a0a0a", color: "#e6edf3", margin: 0 }}>
        {/* global CSS to prevent overflow */}
        <style>{`
          *, *::before, *::after { box-sizing: border-box; }
          input, select, textarea { width: 100%; max-width: 100%; }
        `}</style>
        {children}
      </body>
    </html>
  );
}
