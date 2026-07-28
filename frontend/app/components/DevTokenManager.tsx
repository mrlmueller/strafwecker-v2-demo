"use client";

import { useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";

export function DevTokenManager() {
  const searchParams = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    const devToken = searchParams.get("devToken");
    
    if (devToken) {
      // If devToken is in URL, store it in localStorage for future use
      localStorage.setItem("devToken", devToken);
      
      // Remove the devToken from URL without triggering a page reload
      const url = new URL(window.location.href);
      url.searchParams.delete("devToken");
      window.history.replaceState({}, "", url.toString());
    }
  }, [searchParams]);

  return null;
}