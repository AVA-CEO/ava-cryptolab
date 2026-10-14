import Link from "next/link";
export default function NotFound() {
  return (
    <div className="page-content">
      <h1>Page not found</h1>
      <p className="text-muted-foreground">
        This page isn’t part of your workspace.
      </p>
      <Link className="text-primary" href="/">
        Return to Command Center →
      </Link>
    </div>
  );
}
