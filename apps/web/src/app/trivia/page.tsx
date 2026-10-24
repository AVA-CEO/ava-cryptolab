import { publicLearning } from "@/lib/education";
import { LearningWorkspace } from "@/features/learning/workspace";
export default function Page() {
  return <LearningWorkspace mode="trivia" catalog={publicLearning()} />;
}
