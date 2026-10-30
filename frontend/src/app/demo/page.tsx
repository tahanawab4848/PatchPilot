"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, FlaskConical } from "lucide-react";
import { repositoriesApi } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import type { DemoProject } from "@/types/api";

export default function DemoPage() {
  const [demos, setDemos] = useState<DemoProject[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    repositoriesApi
      .listDemos()
      .then((d) => setDemos(d.demos))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8 max-w-2xl">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-text-primary">Demo projects</h1>
        <p className="text-sm text-text-secondary mt-0.5">
          Bundled broken repositories ready for PatchPilot to fix.
        </p>
      </div>

      {loading && (
        <div className="h-24 rounded-md bg-surface-1 border border-border animate-pulse" />
      )}

      {!loading && demos.length === 0 && (
        <div className="rounded-md border border-border bg-surface-1 p-6 text-center">
          <FlaskConical className="h-8 w-8 text-text-muted mx-auto mb-2" />
          <p className="text-sm text-text-secondary">No demo projects found.</p>
          <p className="text-xs text-text-muted mt-1">
            Check that demo_projects/ is mounted correctly.
          </p>
        </div>
      )}

      <div className="space-y-3">
        {demos.map((demo) => (
          <div
            key={demo.id}
            className="rounded-md border border-border bg-surface-1 p-4"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-sm font-semibold text-text-primary mb-1">
                  {demo.name}
                </h2>
                {demo.description && (
                  <p className="text-xs text-text-secondary leading-relaxed line-clamp-3">
                    {demo.description}
                  </p>
                )}
              </div>
              <Button asChild size="sm" className="shrink-0">
                <Link href={`/jobs/new?demo=${demo.id}`}>
                  Investigate
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
