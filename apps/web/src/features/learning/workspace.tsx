"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { BookOpen, CheckCircle2, Trophy } from "lucide-react";
import { Button } from "@/components/ui/button";
import "@/features/product.css";
type Lesson = {
  id: string;
  title: string;
  topic: string;
  minutes: number;
  objective: string;
  paragraphs: readonly string[];
  example: string;
};
type Question = {
  id: string;
  lesson: string;
  prompt: string;
  choices: readonly string[];
};
type Catalog = { lessons: readonly Lesson[]; questions: readonly Question[] };
const KEY = "ava-learning-v1";
const SCORE_KEY = "ava-quiz-progress-v1";
export function LearningWorkspace({
  catalog,
  mode,
}: {
  catalog: Catalog;
  mode: "academy" | "trivia";
}) {
  const [active, setActive] = useState(catalog.lessons[0].id);
  const [complete, setComplete] = useState<string[]>([]);
  const [storageReady, setStorageReady] = useState(false);
  const [topic, setTopic] = useState("all");
  const [index, setIndex] = useState(0);
  const [answer, setAnswer] = useState<{
    correct: boolean;
    correct_choice: number;
    explanation: string;
  } | null>(null);
  const [choice, setChoice] = useState<number | null>(null);
  const [scores, setScores] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    const timer = window.setTimeout(() => {
      try {
        const saved = JSON.parse(localStorage.getItem(KEY) ?? "[]");
        if (Array.isArray(saved))
          setComplete(
            saved.filter(
              (x) =>
                typeof x === "string" &&
                catalog.lessons.some((l) => l.id === x),
            ),
          );
        const savedScores = JSON.parse(localStorage.getItem(SCORE_KEY) ?? "{}");
        if (
          savedScores &&
          typeof savedScores === "object" &&
          !Array.isArray(savedScores)
        )
          setScores(
            Object.fromEntries(
              Object.entries(savedScores).filter(
                (entry): entry is [string, boolean] =>
                  typeof entry[1] === "boolean" &&
                  catalog.questions.some((q) => q.id === entry[0]),
              ),
            ),
          );
      } catch {
        /* Optional browser storage: learning still works. */
      }
      setStorageReady(true);
    }, 0);
    return () => window.clearTimeout(timer);
  }, [catalog]);
  function markComplete() {
    const next = [...new Set([...complete, active])];
    setComplete(next);
    try {
      localStorage.setItem(KEY, JSON.stringify(next));
    } catch {
      setError("Progress works this session; browser storage is unavailable.");
    }
  }
  const lesson = catalog.lessons.find((l) => l.id === active)!;
  const pool = catalog.questions.filter(
    (q) => topic === "all" || q.lesson === topic,
  );
  const question = pool[index % pool.length];
  async function submit() {
    if (choice === null) return;
    setBusy(true);
    setError("");
    try {
      const r = await fetch("/api/learning", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question_id: question.id, choice }),
      });
      const value = await r.json();
      if (!r.ok) throw new Error(value.detail);
      setAnswer(value);
      const nextScores =
        question.id in scores
          ? scores
          : { ...scores, [question.id]: value.correct === true };
      setScores(nextScores);
      try {
        localStorage.setItem(SCORE_KEY, JSON.stringify(nextScores));
      } catch {
        setError(
          "Score lasts this session only; browser storage is unavailable.",
        );
      }
    } catch {
      setError("The answer could not be checked. Please try again.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="page-content product-page">
      <p className="eyebrow">AVA KNOWLEDGE LAB</p>
      <h1>
        {mode === "academy"
          ? "Learn the market. Understand yourself."
          : "Trivia Arena"}
      </h1>
      <p className="page-subtitle">
        Clear explanations. Practical examples. Knowledge before exposure.
      </p>
      <div className="product-notice">
        {mode === "academy"
          ? `${storageReady ? complete.length : 0} / ${catalog.lessons.length} lessons marked complete`
          : `${Object.values(scores).filter(Boolean).length} correct / ${Object.keys(scores).length} answered · first attempts in this browser`}{" "}
        · Personal browser progress, not a verified achievement or account
        record.
      </div>
      <div className="product-tabs">
        <Button asChild variant={mode === "academy" ? "default" : "outline"}>
          <Link href="/academy">
            <BookOpen size={16} /> Academy
          </Link>
        </Button>
        <Button asChild variant={mode === "trivia" ? "default" : "outline"}>
          <Link href="/trivia">
            <Trophy size={16} /> Trivia
          </Link>
        </Button>
      </div>
      {error && (
        <p role="alert" className="product-error">
          {error}
        </p>
      )}
      {mode === "academy" ? (
        <div className="product-columns">
          <section className="panel product-card" aria-label="Learning path">
            <h2>Your learning path</h2>
            {catalog.lessons.map((l) => (
              <button
                key={l.id}
                className="product-choice"
                aria-pressed={active === l.id}
                onClick={() => setActive(l.id)}
              >
                <strong>
                  {complete.includes(l.id) ? "✓ " : ""}
                  {l.title}
                </strong>
                <br />
                <small>
                  {l.topic} · {l.minutes} min
                </small>
              </button>
            ))}
          </section>
          <article className="panel product-card">
            <span className="badge">{lesson.topic}</span>
            <h2>{lesson.title}</h2>
            <p>
              <strong>Your goal:</strong> {lesson.objective}
            </p>
            {lesson.paragraphs.map((p) => (
              <p key={p}>{p}</p>
            ))}
            <div className="product-outcome">
              <h3>Make it concrete</h3>
              <p>{lesson.example}</p>
            </div>
            <Button onClick={markComplete}>
              <CheckCircle2 size={16} />{" "}
              {complete.includes(active) ? "Completed" : "Mark lesson complete"}
            </Button>
            <Link className="product-link" href="/trivia">
              Check your understanding →
            </Link>
          </article>
        </div>
      ) : (
        <section className="panel product-card" style={{ maxWidth: 800 }}>
          <label>
            Practice topic
            <select
              disabled={busy}
              value={topic}
              onChange={(e) => {
                setTopic(e.target.value);
                setIndex(0);
                setChoice(null);
                setAnswer(null);
              }}
            >
              {[
                <option value="all" key="all">
                  All topics
                </option>,
                ...catalog.lessons.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.title}
                  </option>
                )),
              ]}
            </select>
          </label>
          <p>
            Question {(index % pool.length) + 1} of {pool.length}
          </p>
          <h2>{question.prompt}</h2>
          {question.choices.map((c, i) => (
            <button
              className="product-choice"
              aria-pressed={choice === i}
              key={c}
              disabled={!!answer || busy}
              onClick={() => setChoice(i)}
            >
              {String.fromCharCode(65 + i)} · {c}
            </button>
          ))}
          {!answer ? (
            <Button disabled={choice === null || busy} onClick={submit}>
              {busy ? "Checking…" : "Check answer"}
            </Button>
          ) : (
            <>
              <div role="status" className="product-outcome">
                <h3 className={answer.correct ? "positive" : "negative"}>
                  {answer.correct
                    ? "Correct — well reasoned."
                    : `Keep learning · Correct answer: ${String.fromCharCode(65 + answer.correct_choice)}`}
                </h3>
                <p>{answer.explanation}</p>
              </div>
              <Button
                onClick={() => {
                  setIndex((i) => i + 1);
                  setChoice(null);
                  setAnswer(null);
                }}
              >
                Next question
              </Button>
            </>
          )}
        </section>
      )}
      <p className="product-muted">
        Educational content, not personalized investment advice. Examples use
        declared hypothetical conditions. No profits or future market outcomes
        are promised.
      </p>
    </div>
  );
}
