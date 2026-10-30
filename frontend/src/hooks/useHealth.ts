"use client";

import { useEffect, useState } from "react";
import { healthApi } from "@/lib/api-client";
import type { HealthResponse } from "@/types/api";

export function useHealth() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    healthApi
      .readiness()
      .then(setHealth)
      .catch(() => setHealth(null))
      .finally(() => setLoading(false));
  }, []);

  return { health, loading };
}
