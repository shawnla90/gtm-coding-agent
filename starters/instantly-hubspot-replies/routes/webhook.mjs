// Copy to app/api/instantly/webhook/route.js.
// Auth matches reply_loop.webhook_http_status. Writes stay in the Python rules.

export function webhookStatus(headerValue, expected) {
  if (!expected || headerValue !== expected) return 401;
  return 200;
}

export function webhookResponse(request, expectedSecret) {
  const presented = request.headers.get("x-instantly-secret");
  const status = webhookStatus(presented, expectedSecret);
  if (status === 401) return { status, body: { ok: false } };
  return { status, body: { ok: true } };
}
