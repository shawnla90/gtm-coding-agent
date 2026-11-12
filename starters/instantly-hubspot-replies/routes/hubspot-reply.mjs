// Copy to app/api/hubspot/reply/route.js.
// Verify the HubSpot v3 signature with the app client secret before any reply.
// The secret comes from the app Auth tab. A `vercel env pull` of HUBSPOT_APP_SECRET
// is a placeholder, not that secret. The signature check lives in
// reply_loop.signature_is_valid.
// A thread load that returns 200 and zero messages is "No Instantly thread".
// manualMql opens an unowned deal. It does not send.

export function allowlistStatus(email, allowlist) {
  const normalized = String(email || "").trim().toLowerCase();
  const domain = normalized.includes("@") ? normalized.split("@")[1] : "";
  const allowed = (allowlist || []).some((item) => {
    const token = String(item || "").trim().toLowerCase();
    if (!token || !normalized) return false;
    if (token.startsWith("@")) return token.slice(1) === domain;
    return token === normalized;
  });
  return allowed ? 200 : 403;
}

export function threadStatus(httpStatus, messages) {
  if (httpStatus !== 200) return { httpStatus, view: "auth_failure" };
  if (!messages || messages.length === 0) {
    return { httpStatus: 200, view: "no_instantly_thread" };
  }
  return { httpStatus: 200, view: "thread" };
}
