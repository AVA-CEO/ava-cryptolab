import { Dashboard } from "@/features/dashboard/dashboard";
import { getDashboard } from "@/lib/api";
export default async function Page() {
  return <Dashboard result={await getDashboard()} />;
}
