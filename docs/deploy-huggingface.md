# Share CoupleCare AI with friends — Hugging Face Spaces

This puts the app online as a free Hugging Face Space so a few people can use it from their browser. It runs in
cloud mode: replies come from Groq (your key), voice input uses Groq Whisper, and there is no local model.

**What it costs:** nothing on Hugging Face's free CPU tier. All visitors share your Groq free quota
(about 100 chat messages a day in total, ~3 per minute).

**Good to know before sharing**

- Anyone with the link can use it, and their messages are processed on the Space and sent to Groq.
- Conversations are kept in memory only and disappear when the Space restarts or sleeps.
- A free Space sleeps after a period without visitors; the first visitor then waits about a minute.
- The knowledge base is the project's example guides, not expert-reviewed content. It is not a crisis service.

## One-time setup (about 10 minutes)

1. **Create a Hugging Face account** at <https://huggingface.co/join> (free).
2. **Create an access token** for uploading: <https://huggingface.co/settings/tokens> → *Create new token* →
   type **Write** → copy it. You will paste it as the password in step 5. Keep it private.
3. **Create the Space**: <https://huggingface.co/new-space>
   - *Space name*: e.g. `couplecare-ai`
   - *SDK*: **Docker** → *Blank* template
   - *Hardware*: **CPU basic (free)**
   - *Visibility*: **Public** (so friends can open it without an account)
   - Click **Create Space**.
4. **Add your Groq key as a secret**: in the Space, open **Settings → Variables and secrets → New secret**
   - Name: `COUPLECARE_GROQ_API_KEY`
   - Value: your Groq key (the same one as in your `.env`)
   - Secrets are hidden and are not part of the code.
5. **Upload the app** from the project folder in PowerShell (replace `yourname`):
   ```powershell
   scripts\deploy-huggingface.ps1 -Space yourname/couplecare-ai
   ```
   When Git asks, enter your Hugging Face **username** and paste the **access token** as the password.
6. **Wait for the build** (about 10–15 minutes the first time). Watch the **Logs** tab of the Space; when it says
   *Running*, open the **App** tab. Share the link with your friends:
   `https://huggingface.co/spaces/yourname/couplecare-ai`
   (or the direct address shown under the ⋮ menu → *Embed this Space*, e.g. `https://yourname-couplecare-ai.hf.space`).

## Updating later

After changing and committing the project, run the same command again:

```powershell
scripts\deploy-huggingface.ps1 -Space yourname/couplecare-ai
```

Only committed files are uploaded; `.env`, local models, caches and history are never included.

## If something goes wrong

| Symptom | Fix |
|---|---|
| Build fails in Logs | Open the Logs tab, copy the last lines, and fix the reported step (often a temporary download error: click *Restart* / *Factory rebuild*). |
| App says "AI generation offline" | The secret is missing or wrong: check `COUPLECARE_GROQ_API_KEY` in Settings → Variables and secrets, then *Restart* the Space. |
| "The free Groq limit has been reached" | The shared daily quota is used up; it resets automatically. |
| Push asks for a password repeatedly | Use the access token (type **Write**) as the password, not your account password. |
