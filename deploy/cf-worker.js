// Cloudflare Worker — Agent API 代理
// 部署: npx wrangler deploy
// 免费: 10万次/天 · 全球CDN

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type",
        },
      });
    }

    const url = new URL(request.url);

    // Health check
    if (url.pathname === "/api/health") {
      return Response.json({ status: "ok", provider: "deepseek", model: "deepseek-v4-flash" });
    }

    // Chat endpoint
    if (url.pathname === "/api/chat" && request.method === "POST") {
      try {
        const { message } = await request.json();
        const resp = await fetch("https://api.deepseek.com/v1/chat/completions", {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${env.DEEPSEEK_API_KEY}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            model: "deepseek-v4-flash",
            messages: [
              { role: "system", content: "你是自主 AI Agent。用中文回答，简洁专业。" },
              { role: "user", content: message },
            ],
            temperature: 0.1,
            max_tokens: 4096,
          }),
        });
        const data = await resp.json();
        if (data.error) {
          return Response.json({ error: data.error.message }, { status: 400 });
        }
        return Response.json(
          { answer: data.choices[0].message.content, model: "deepseek-v4-flash" },
          { headers: { "Access-Control-Allow-Origin": "*" } }
        );
      } catch (e) {
        return Response.json({ error: e.message }, { status: 500 });
      }
    }

    return Response.json({ error: "Not found" }, { status: 404 });
  },
};
