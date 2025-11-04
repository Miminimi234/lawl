# Deploy Backend to Railway

## Quick Deploy Steps:

### 1. Login to Railway
```bash
cd /Users/white_roze/LAwI/backend
railway login
```

### 2. Create/Link Project
```bash
railway init
```
Select "Create a new project" and name it "verdict-backend"

### 3. Deploy
```bash
railway up
```

### 4. Get Your Backend URL
```bash
railway domain
```

### 5. Update Frontend Environment Variable

Once you get your Railway URL (e.g., `https://verdict-backend-production.up.railway.app`), update the frontend:

Create `.env.local` in the frontend directory:
```
NEXT_PUBLIC_API_URL=https://your-railway-url.railway.app
```

Then redeploy frontend:
```bash
cd /Users/white_roze/LAwI/frontend
vercel --prod --yes
```

---

## Alternative: One-Line Deploy

```bash
cd /Users/white_roze/LAwI/backend && railway login && railway init && railway up && railway domain
```

---

## Files Already Created for Railway:

✅ `requirements.txt` - Python dependencies
✅ `Procfile` - Start command
✅ `railway.json` - Railway configuration
✅ `standalone_server.py` - Updated to use PORT env var
✅ `data/verdict_cases.json` - All 1589 cases

---

## What Railway Will Do:

1. Install Python dependencies from requirements.txt
2. Upload your data directory (23MB of cases)
3. Start the server on port assigned by Railway
4. Give you a public URL

---

## Expected Output:

After deployment, you should see:
- ✅ Build logs showing Python installation
- ✅ Server starting on `0.0.0.0:PORT`
- ✅ Public URL like `https://verdict-backend-production.up.railway.app`

Test it:
```bash
curl https://your-railway-url.railway.app/api/feed/live
```

You should see JSON with all your cases!

