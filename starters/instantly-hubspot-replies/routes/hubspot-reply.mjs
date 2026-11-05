// Copy to app/api/hubspot/reply/route.js.
// Verify the HubSpot v3 signature with the app client secret before any reply.
// The signature check itself lives in reply_loop.signature_is_valid.

export function allowlistStatus(email, allowlist) {
  const allowed = new Set(
    (allowlist || []).map((item) => String(item).trim().toLowerCase()).filter(Boolean),
  );
  if (!email || !allowed.has(String(email).trim().toLowerCase())) return 403;
  return 200;
}
