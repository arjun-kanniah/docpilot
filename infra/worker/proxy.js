// Forwards the custom domain to Cloud Run. Cloudflare streams response bodies through as they
// arrive, so answers still appear token by token.
//
// Requests reach Cloud Run from Cloudflare's addresses, so the visitor's IP goes in a header for
// the demo's rate limit, with a secret shared with the API so a direct caller can't forge it.
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    url.protocol = "https:";
    url.hostname = env.ORIGIN_HOST;
    url.port = "";

    const headers = new Headers(request.headers);
    headers.delete("host");
    headers.set("x-docpilot-client-ip", request.headers.get("cf-connecting-ip") ?? "");
    headers.set("x-docpilot-proxy-secret", env.PROXY_SECRET);

    return fetch(url, {
      method: request.method,
      headers,
      body: request.body,
      redirect: "manual",
    });
  },
};
