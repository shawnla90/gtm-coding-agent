// Copy to app/api/cron/poll/route.js.
// Vercel Cron sends Authorization: Bearer <CRON_SECRET>.
// GET /api/v2/emails is limited to about 20 requests a minute. One page per wake.

export function cronStatus(authorization, expected) {
  if (!expected || authorization !== `Bearer ${expected}`) return 401;
  return 200;
}

export function cronResponse(request, expectedSecret) {
  const status = cronStatus(request.headers.get("authorization"), expectedSecret);
  if (status === 401) return { status, body: { ok: false } };
  return { status, body: { ok: true, wrote: false } };
}
