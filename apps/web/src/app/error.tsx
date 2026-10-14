"use client";
import { Button } from "@/components/ui/button";
export default function ErrorPage({ retry }: { retry: () => void }) {
  return (
    <div className="page-content">
      <section className="panel empty-panel">
        <h1>Something interrupted your workspace.</h1>
        <p>Please try loading it again.</p>
        <Button onClick={retry}>Try again</Button>
      </section>
    </div>
  );
}
