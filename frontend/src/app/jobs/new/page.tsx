import { Suspense } from "react";
import { NewJobForm } from "@/features/jobs/NewJobForm";

export const metadata = {
  title: "New Investigation — PatchPilot",
};

export default function NewJobPage() {
  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-text-primary">
          New Investigation
        </h1>
        <p className="text-sm text-text-secondary mt-0.5">
          Upload a repository and describe the bug to start an autonomous diagnosis.
        </p>
      </div>
      <Suspense fallback={<div className="h-40 rounded-md bg-surface-1 border border-border animate-pulse" />}>
        <NewJobForm />
      </Suspense>
    </div>
  );
}
