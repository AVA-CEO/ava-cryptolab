export default function Loading() {
  return (
    <div
      className="page-content"
      aria-busy="true"
      aria-label="Loading dashboard"
    >
      <div className="skeleton h-16 w-2/3" />
      <div className="metric-grid mt-8">
        {[1, 2, 3, 4].map((n) => (
          <div key={n} className="skeleton h-32" />
        ))}
      </div>
      <div className="skeleton mt-6 h-96" />
    </div>
  );
}
