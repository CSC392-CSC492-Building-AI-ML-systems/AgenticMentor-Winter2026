import type { NextConfig } from "next";

const firebaseAuthDomain = process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || "mentor-e704f.firebaseapp.com";

const nextConfig: NextConfig = {
  async rewrites() {
    return {
      beforeFiles: [
        // Proxy Firebase Auth handler to our origin so redirect flow works when browsers block third-party cookies
        { source: "/__/auth/:path*", destination: `https://${firebaseAuthDomain}/__/auth/:path*` },
      ],
    };
  },
};

export default nextConfig;
