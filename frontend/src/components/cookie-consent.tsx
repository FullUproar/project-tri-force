"use client";

import { useState, useEffect } from "react";

const STORAGE_KEY = "cortaloom-cookie-consent";

export function CookieConsent() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const dismissed = localStorage.getItem(STORAGE_KEY);
    if (!dismissed) {
      setVisible(true);
    }
  }, []);

  const handleDismiss = () => {
    localStorage.setItem(STORAGE_KEY, "true");
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 border-t border-[var(--border)] bg-[var(--background)] px-6 py-3">
      <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
        <p className="text-xs text-[var(--muted-foreground)]">
          We use essential cookies for authentication and security. No tracking cookies are used.
        </p>
        <button
          onClick={handleDismiss}
          className="shrink-0 px-4 py-1.5 bg-[var(--primary)] text-[var(--primary-foreground)] rounded-md text-xs font-semibold hover:opacity-90"
        >
          Got it
        </button>
      </div>
    </div>
  );
}
