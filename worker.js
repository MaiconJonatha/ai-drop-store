// Cloudflare Worker - AI Drop Store Proxy
// Deploy the FastAPI app on a VPS/Render and proxy through Cloudflare

const BACKEND_URL = "https://ai-drop-store.onrender.com";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const backendUrl = BACKEND_URL + url.pathname + url.search;
    
    const response = await fetch(backendUrl, {
      method: request.method,
      headers: request.headers,
      body: request.method !== "GET" ? request.body : undefined,
    });
    
    const newResponse = new Response(response.body, response);
    newResponse.headers.set("X-Powered-By", "AI Drop Store");
    newResponse.headers.set("Cache-Control", "public, max-age=60");
    return newResponse;
  },
};
