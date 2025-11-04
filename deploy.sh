#!/bin/bash

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║         DEPLOYING VERDICT BACKEND TO RAILWAY             ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

cd "$(dirname "$0")"

echo "→ Step 1: Login to Railway..."
railway login

echo ""
echo "→ Step 2: Initialize Railway project..."
railway init

echo ""
echo "→ Step 3: Deploying backend..."
railway up

echo ""
echo "→ Step 4: Setting up domain..."
railway domain

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                  DEPLOYMENT COMPLETE!                     ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "1. Copy your Railway URL from above"
echo "2. Update frontend/.env.local with:"
echo "   NEXT_PUBLIC_API_URL=https://your-railway-url.railway.app"
echo "3. Redeploy frontend: cd ../frontend && vercel --prod --yes"
echo ""

