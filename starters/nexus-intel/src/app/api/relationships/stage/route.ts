import { NextResponse } from "next/server";
import { updatePersonStage } from "@/lib/db";

const VALID_STAGES = new Set([
  "stranger",
  "aware",
  "interested",
  "engaged",
  "conversing",
  "warm",
  "client",
]);

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const personId = Number(body?.personId);
    const stage = String(body?.stage ?? "");

    if (!Number.isFinite(personId) || personId <= 0) {
      return NextResponse.json({ error: "invalid personId" }, { status: 400 });
    }
    if (!VALID_STAGES.has(stage)) {
      return NextResponse.json({ error: "invalid stage" }, { status: 400 });
    }

    updatePersonStage(personId, stage);
    return NextResponse.json({ ok: true, personId, stage });
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "update failed" },
      { status: 500 },
    );
  }
}
