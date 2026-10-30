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
    <div className="p-8 max-w-4xl mx-auto space-y-6 animate-fade-in">
      <div className="border-b border-border/80 pb-5">
        <div className="flex items-center gap-2 text-accent mb-2">
          <FlaskConical className="h-5 w-5" />
          <span className="text-xs font-mono uppercase tracking-wider font-semibold">
            Ready-to-Run Testbeds
          </span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-text-primary">Demo Projects</h1>
        <p className="text-sm text-text-secondary mt-1">
          Pre-packaged broken software repositories designed to demonstrate PatchPilot&apos;s autonomous diagnosis and patch verification.
        </p>
      </div>

      {loading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-28 rounded-lg bg-surface-1/70 border border-border/80 animate-pulse" />
          ))}
        </div>
      )}

      {!loading && demos.length === 0 && (
        <div className="rounded-lg border border-dashed border-border/80 bg-surface-1/40 p-10 text-center space-y-2">
          <FlaskConical className="h-10 w-10 text-text-muted mx-auto mb-2 opacity-60" />
          <p className="text-sm font-medium text-text-secondary">No demo projects found.</p>
          <p className="text-xs text-text-muted">
            Check that demo_projects/ is mounted correctly.
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {demos.map((demo) => (
          <div
            key={demo.id}
            className="group rounded-lg border border-border/80 bg-surface-1/90 p-5 flex flex-col justify-between hover:border-accent/40 hover:shadow-glow-sm transition-all duration-200"
          >
            <div>
              <div className="flex items-center justify-between gap-2 mb-2">
                <h2 className="text-sm font-semibold text-text-primary group-hover:text-accent transition-colors">
                  {demo.name}
                </h2>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-accent/10 border border-accent/25 text-accent">
                  {demo.id.split("_")[0]}
                </span>
              </div>
              {demo.description && (
                <p className="text-xs text-text-secondary leading-relaxed line-clamp-3 mb-4">
                  {demo.description}
                </p>
              )}
            </div>
            <div className="pt-2 flex justify-end border-t border-border/40">
              <Button asChild size="sm" className="gap-1.5 font-medium">
                <Link href={`/jobs/new?demo=${demo.id}`}>
                  Investigate Defect
                  <ArrowRight className="h-3.5 w-3.5 group-hover:translate-x-0.5 transition-transform" />
                </Link>
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
