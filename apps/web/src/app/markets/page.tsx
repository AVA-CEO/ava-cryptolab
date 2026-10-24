import dynamic from "next/dynamic";
const Markets = dynamic(() =>
  import("@/features/markets/workspace").then((m) => m.MarketsWorkspace),
);
export default function Page() {
  return <Markets />;
}
