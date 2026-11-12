// Copy to app/api/instantly/webhook/route.js.
// Auth matches reply_loop.webhook_http_status. Writes stay in the Python rules.
// Before a write, call campaign_in_scope. The name guard runs only when
// INSTANTLY_REPLY_TEST_MODE is on. reply_received logs the email and does not
// open a deal. lead_interested does.

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
