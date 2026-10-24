import { publicLearning, questions } from "@/lib/education";
import { limitedBody } from "@/lib/limited-body";
export function GET() {
  return Response.json(publicLearning(), {
    headers: { "Cache-Control": "no-store" },
  });
}
export async function POST(request: Request) {
  if (
    request.headers.get("origin") &&
    request.headers.get("origin") !==
      `${new URL(request.url).protocol}//${request.headers.get("host")}`
  )
    return Response.json({ detail: "Untrusted origin." }, { status: 403 });
  try {
    const text = new TextDecoder().decode(await limitedBody(request, 4096));
    if (text.length > 4096)
      return Response.json({ detail: "Answer too large." }, { status: 413 });
    const body = JSON.parse(text);
    if (
      Object.keys(body).some(
        (key) => !["question_id", "choice"].includes(key),
      ) ||
      !Number.isInteger(body.choice) ||
      body.choice < 0 ||
      body.choice > 3
    )
      throw new Error();
    const question = questions.find((q) => q.id === body.question_id);
    if (!question) throw new Error();
    return Response.json(
      {
        correct: body.choice === question.answer,
        correct_choice: question.answer,
        explanation: question.explanation,
      },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch (error) {
    return Response.json(
      { detail: "Supply a known question and one choice from 0 to 3." },
      { status: error instanceof RangeError ? 413 : 422 },
    );
  }
}
