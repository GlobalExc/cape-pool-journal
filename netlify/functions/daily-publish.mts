// Runs every morning at 06:05 Cape Town time (04:05 UTC) and triggers a fresh build,
// so posts whose publish date has arrived go live automatically.
// Setup: Netlify → Project configuration → Build & deploy → Build hooks → Add build hook,
// then save its URL as an environment variable named BUILD_HOOK_URL.
export default async () => {
  const hook = Netlify.env.get("BUILD_HOOK_URL");
  if (!hook) {
    console.log("BUILD_HOOK_URL is not set; skipping rebuild");
    return;
  }
  const res = await fetch(hook, { method: "POST" });
  console.log(`Daily rebuild triggered: ${res.status}`);
};

export const config = { schedule: "5 4 * * *" };
