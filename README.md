# eToro → WhatsApp Notifier

Sends a WhatsApp notification whenever any tracked eToro user publishes a new text post on their public profile. Each notification names the author, e.g. `@harryh1993 posted: https://www.etoro.com/posts/…`.

## Setup

### 1. CallMeBot (one-time)
1. Add the phone number **+34 644 63 38 90** to your WhatsApp contacts (name it e.g. "CallMeBot").
2. Send it this exact message: `I allow callmebot to send me messages`
3. Wait for a reply containing your API key. Save it.

### 2. Configure GitHub secrets
In this repo's **Settings → Secrets and variables → Actions**, add:
- `CALLMEBOT_PHONE` — your phone in international format, e.g. `+447700900000`
- `CALLMEBOT_APIKEY` — the key you received

### 3. Configure the profiles (if different from defaults)
Edit the `PROFILE_URLS` list at the top of `check_etoro.py`. Each profile is scraped, diffed, and notified independently; a failure on one profile doesn't affect the others.

### 4. First run
Go to **Actions → Check eToro → Run workflow** and trigger it manually. This seeds one `state/seen-<username>.json` file per tracked profile with currently-visible posts and sends no notifications. After that, the cron takes over every 15 min.

## Local development

```bash
python -m venv .venv
.venv/Scripts/activate   # Windows
pip install -r requirements.txt
playwright install chromium
pytest
```
