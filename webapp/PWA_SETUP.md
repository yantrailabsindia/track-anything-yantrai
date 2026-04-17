# YantrAI Track Anything - PWA Setup Guide

## ✅ What's Been Implemented

Your webapp is now a **fully-functional Progressive Web App (PWA)** with native app-like experience on iOS and Android.

### Core Features

#### 1. **PWA Manifest & Installation**
- File: `public/manifest.json`
- Defines app metadata (name, icons, colors, display mode)
- Display mode: `standalone` (hides browser URL bar)
- Start URL: `/dashboard` (app opens to dashboard)
- Theme color: Dark gray (#1f2937)

#### 2. **Service Worker**
- File: `public/sw.js`
- Handles offline functionality and caching
- Caching strategy:
  - Network-first: API calls (real-time data)
  - Cache-first: Static assets (JS, CSS, images)
  - Stale-while-revalidate: Dashboard data
- Auto-updates detection
- Background sync support

#### 3. **Mobile-Optimized UI**
- Bottom Navigation: Mobile-only tabs at bottom (Dashboard, Activity, Teams, Chat, Settings)
- Responsive Design: Tailwind CSS breakpoints for mobile
- Touch-Friendly: Minimum 44px tap targets (iOS standard)
- Safe Area Support: Notched device support (iPhone X+, Android notches)

#### 4. **Installation Features**
- Auto-Detection: Browser automatically offers install prompt
- iOS: "Add to Home Screen" option in Safari share menu
- Android: Install button appears in Chrome address bar
- Custom install banner with instructions

#### 5. **Update Management**
- Service worker checks for updates every minute
- User notification when app update available
- One-click restart to apply new version
- No app store submission needed

#### 6. **Offline Support**
- Offline banner when connection lost
- Cached data available offline
- Pending actions queued for sync when online
- IndexedDB storage for offline data

---

## 🚀 How to Test PWA Locally

### Start Development Server
```bash
cd webapp
npm run dev
```
Server runs at http://localhost:3000

### Test on Desktop Chrome
1. Open http://localhost:3000
2. Open DevTools (F12)
3. Go to Application → Manifest
   - Verify manifest.json is loaded
   - Check start URL, display mode, icons
4. Go to Application → Service Workers
   - Verify sw.js is registered and activated
5. Address bar should show Install button

### Test on Mobile Devices
1. Navigate to your server IP (for local network testing)
2. Android: Tap address bar → Install YantrAI
3. iOS: Tap Share → Add to Home Screen
4. App opens full-screen (no URL bar)

### Test Offline
1. Install app on device
2. DevTools (Desktop): Network → Offline
3. App continues working with cached data
4. Offline banner appears at top

### Test Updates
1. Make a change to webapp/app/page.tsx
2. App should show "App Update Available" notification
3. Click "Restart App" to apply update

---

## 📁 Files Created

New files:
- public/manifest.json - PWA manifest
- public/sw.js - Service worker
- public/icons/* - App icons (192x192, 512x512)
- components/BottomNavigation.tsx - Mobile nav
- components/InstallPrompt.tsx - Install banner
- components/OfflineBanner.tsx - Offline indicator
- components/ServiceWorkerUpdatePrompt.tsx - Update notification
- lib/pwa-utils.ts - PWA utilities
- lib/offline.ts - Offline utilities
- tailwind.config.ts - Tailwind config

Modified files:
- app/layout.tsx - Added PWA metadata and components
- app/globals.css - Added mobile and PWA styles

---

## 🔧 Configuration

### Change App Name/Colors
Edit `public/manifest.json`:
- name: Long app name
- short_name: Short name (max 12 chars)
- theme_color: Status bar color
- background_color: Splash screen color

### Change Start URL
Edit manifest.json:
- start_url: Which page opens when user taps icon

### Change Caching Strategy
Edit `public/sw.js`:
- Modify CACHE_NAME for new cache version
- Update fetch event listener for different caching rules

---

## 📊 Lighthouse Audit

Run Lighthouse to verify PWA score (target: 90+):
1. DevTools → Lighthouse
2. Select Mobile
3. Check Progressive Web App
4. Run audit

Should show all green:
- Manifest present
- Service worker present
- Can be installed
- Works offline
- Responsive design
- Secure (HTTPS)

---

## 🚢 Deployment to Production

### 1. Build for Production
```bash
npm run build
npm start
```

### 2. Update Manifest
Edit public/manifest.json with production domain

### 3. Deploy to Cloud
Options: Vercel, Netlify, AWS Amplify, DigitalOcean, etc.

### 4. Enable HTTPS
PWA requires HTTPS in production (except localhost)

### 5. Monitor Updates
Service worker checks for updates every minute
Users see notification when new version available
Click "Restart App" to reload with new code

---

## 🔒 Security

- Service worker only caches non-sensitive data
- API tokens stored in memory (not cached)
- Login page not cached (always fetch fresh)
- HTTPS enforced in production
- Manifest uses standalone display mode

---

## 📱 User Installation

### iOS
1. Open Safari
2. Go to yourdomain.com
3. Tap Share → "Add to Home Screen"
4. Tap "Add"
5. App appears on home screen

### Android
1. Open Chrome
2. Go to yourdomain.com
3. Tap address bar menu (⋮)
4. Tap "Install YantrAI"
5. Confirm installation
6. App appears on home screen

---

## 🐛 Troubleshooting

- App not installing: Check HTTPS (except localhost), iOS 15.4+, Chrome updated
- Service worker not updating: Hard refresh (Ctrl+Shift+F5) or clear cache
- Offline mode not working: Verify service worker is active in DevTools
- Icons not showing: Verify icon files exist, check manifest.json paths

---

**Status:** ✅ PWA Implementation Complete
**Last Updated:** 2026-04-13
