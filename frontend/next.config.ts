import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",            // anything from /api/*
        destination: "http://localhost:8000/api/:path*", // redirect to FastAPI
      },
    ];
  },
};

export default nextConfig;
