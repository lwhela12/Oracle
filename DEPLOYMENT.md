# Vercel Deployment Guide

This guide will help you deploy the Oracle application to Vercel.

## Prerequisites

1. A [Vercel account](https://vercel.com/signup)
2. A Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

## Deployment Steps

### 1. Environment Variables (CRITICAL - REQUIRED)

**IMPORTANT:** The app will crash without this environment variable set!

Before deploying, you MUST set up your environment variable in Vercel:

1. Go to your Vercel project dashboard
2. Navigate to **Settings** → **Environment Variables**
3. Add the following environment variable:
   - **Name:** `GEMINI_API_KEY`
   - **Value:** Your Google Gemini API key (get one at https://makersuite.google.com/app/apikey)
   - **Environments:** Select all (Production, Preview, Development)
4. Click **Save**

**After adding the environment variable, you MUST redeploy the app** for it to take effect.

### 2. Deploy to Vercel

#### Option A: Deploy via Vercel Dashboard

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click **Add New** → **Project**
3. Import your Git repository
4. Vercel will automatically detect the `vercel.json` configuration
5. Click **Deploy**

#### Option B: Deploy via Vercel CLI

```bash
# Install Vercel CLI
npm i -g vercel

# Login to Vercel
vercel login

# Deploy
vercel

# Deploy to production
vercel --prod
```

### 3. Verify Deployment

After deployment, Vercel will provide you with a URL. Visit the URL to ensure:

1. The homepage loads correctly
2. The Oracle chatbot initializes
3. You can perform tarot, I Ching, and rune readings

## Troubleshooting

### Application Crashes

If the app crashes, check:

1. **Environment Variables:** Ensure `GEMINI_API_KEY` is set correctly in Vercel
   - Go to Settings → Environment Variables
   - Verify the variable name is exactly `GEMINI_API_KEY` (case-sensitive)
   - Ensure it's enabled for all environments (Production, Preview, Development)
   - After adding/changing, redeploy the app
2. **Build Logs:** Check Vercel's deployment logs for errors
3. **Function Logs:** Check Vercel's function logs for runtime errors
   - Look for "GEMINI_API_KEY environment variable is not set" error
   - This indicates the environment variable wasn't configured properly

### Static Files Not Loading

If images or other static files don't load:

1. Verify the `static/` directory is included in your repository
2. Check the browser console for 404 errors
3. Ensure file paths in HTML use relative paths

### API Errors

If you see "API key not found" or similar errors:

1. Double-check that `GEMINI_API_KEY` is set in Vercel's environment variables
2. Redeploy the application after setting environment variables
3. Check that your Gemini API key is valid and has quota remaining

## Configuration Files

- **vercel.json:** Configures Vercel to run the Flask application and serve static files
- **.env.example:** Template for required environment variables
- **requirements.txt:** Python dependencies that Vercel will install

## Local Development

To run locally:

```bash
# Create .env file from template
cp .env.example .env

# Add your API key to .env
# GEMINI_API_KEY=your_actual_api_key_here

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

The app will be available at `http://localhost:5001`
