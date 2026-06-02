const UPSTREAM_ORIGIN = "https://imaginative-love-production.up.railway.app";

function isAdminPath(pathname) {
  return (
    pathname === "/admin" ||
    pathname === "/admin-console" ||
    pathname.startsWith("/admin-console/") ||
    pathname.startsWith("/admin-api/")
  );
}

function unauthorized() {
  return new Response("Admin access required", {
    status: 401,
    headers: {
      "WWW-Authenticate": 'Basic realm="SpeakOut Admin"',
      "Cache-Control": "no-store",
    },
  });
}

function hasAdminAccess(request, env) {
  const adminUser = env.ADMIN_USER || "admin";
  const adminPassword = env.ADMIN_PASSWORD || "";
  if (!adminPassword) return false;
  const authorization = request.headers.get("Authorization") || "";
  const expected = `Basic ${btoa(`${adminUser}:${adminPassword}`)}`;
  return authorization === expected;
}

export default {
  async fetch(request, env) {
    const incomingUrl = new URL(request.url);

    if (isAdminPath(incomingUrl.pathname) && !hasAdminAccess(request, env)) {
      return unauthorized();
    }

    const upstreamUrl = new URL(request.url);
    const upstreamOrigin = new URL(UPSTREAM_ORIGIN);
    upstreamUrl.protocol = upstreamOrigin.protocol;
    upstreamUrl.hostname = upstreamOrigin.hostname;
    upstreamUrl.port = upstreamOrigin.port;

    const headers = new Headers(request.headers);
    headers.delete("Authorization");
    headers.set("X-Forwarded-Host", incomingUrl.host);
    headers.set("X-Forwarded-Proto", incomingUrl.protocol.replace(":", ""));

    const upstreamMethod = request.method === "HEAD" ? "GET" : request.method;
    const init = {
      method: upstreamMethod,
      headers,
      redirect: "manual",
    };
    if (!["GET", "HEAD"].includes(request.method)) {
      init.body = request.body;
    }

    const response = await fetch(upstreamUrl.toString(), init);
    const responseHeaders = new Headers(response.headers);
    responseHeaders.set("X-Speakout-Edge", "cloudflare-pages-proxy");

    return new Response(request.method === "HEAD" ? null : response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  },
};
