import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { BottomNavigation } from "@/pwa/components/BottomNavigation";
import { InstallPrompt } from "@/pwa/components/InstallPrompt";
import { OfflineBanner } from "@/pwa/components/OfflineBanner";
import { ServiceWorkerUpdatePrompt } from "@/pwa/components/ServiceWorkerUpdatePrompt";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "YantrAI Track Anything",
  description: "Enterprise productivity and team activity tracking with AI-powered insights",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "YantrAI",
  },
  formatDetection: {
    telephone: false,
  },
  viewport: {
    width: "device-width",
    initialScale: 1,
    maximumScale: 5,
    userScalable: true,
    viewportFit: "cover",
  },
  icons: {
    icon: [
      { url: "/icons/icon-192x192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512x512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [
      { url: "/icons/icon-192x192.png", sizes: "192x192", type: "image/png" },
    ],
  },
  themeColor: "#1f2937",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <meta name="theme-color" content="#1f2937" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <meta name="apple-mobile-web-app-title" content="YantrAI" />
        <meta name="msapplication-TileColor" content="#1f2937" />
        <meta name="msapplication-TileImage" content="/icons/icon-192x192.png" />
        <link rel="apple-touch-icon" href="/icons/icon-192x192.png" />
        <link rel="icon" type="image/png" href="/icons/icon-192x192.png" sizes="192x192" />
        <link rel="mask-icon" href="/icons/icon-192x192.png" color="#1f2937" />
      </head>
      <body className={inter.className} suppressHydrationWarning>
        <OfflineBanner />
        {children}
        <BottomNavigation />
        <InstallPrompt />
        <ServiceWorkerUpdatePrompt />
        <ServiceWorkerRegister />
      </body>
    </html>
  );
}

function ServiceWorkerRegister() {
  return (
    <script
      dangerouslySetInnerHTML={{
        __html: `
          if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
            window.addEventListener('load', function() {
              navigator.serviceWorker.register('/sw.js')
                .then(function(registration) {
                  console.log('Service Worker registered:', registration);

                  // Check for updates periodically
                  setInterval(function() {
                    registration.update();
                  }, 60000); // Check every minute

                  // Notify user when new service worker is ready
                  registration.addEventListener('updatefound', function() {
                    const newWorker = registration.installing;
                    newWorker.addEventListener('statechange', function() {
                      if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                        // New service worker available
                        console.log('New app version available. Refresh to update.');
                        // You can show a toast/notification here
                        const event = new CustomEvent('sw-update-available');
                        window.dispatchEvent(event);
                      }
                    });
                  });
                })
                .catch(function(error) {
                  console.log('Service Worker registration failed:', error);
                });
            });
          }
        `,
      }}
    />
  );
}
