import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  serverExternalPackages: ["better-sqlite3"],
  // Force-include the SQLite DB in the serverless function bundle.
  // Without this, Vercel traces only JS imports and data/intel.db gets
  // excluded, causing fileMustExist to throw at runtime.
  outputFileTracingIncludes: {
    "/*": ["./data/intel.db"],
  },
  images: {
    // CDN hosts used by LinkedInAvatar (src/components/linkedin-avatar.tsx)
    // for engager + source logos. If avatars 404, URLs may be signed — see
    // open-risks in the pre-launch plan.
    remotePatterns: [
      // LinkedIn + X
      { protocol: "https", hostname: "media.licdn.com" },
      { protocol: "https", hostname: "static.licdn.com" },
      { protocol: "https", hostname: "pbs.twimg.com" },
      { protocol: "https", hostname: "abs.twimg.com" },
      // Reddit (subreddit icons — populated by scripts/enrich_source_avatars.py)
      { protocol: "https", hostname: "styles.redditmedia.com" },
      { protocol: "https", hostname: "b.thumbs.redditmedia.com" },
      { protocol: "https", hostname: "a.thumbs.redditmedia.com" },
      { protocol: "https", hostname: "www.redditstatic.com" },
      // icon.horse (domain-logo fallback for placeholder/target sources)
      { protocol: "https", hostname: "icon.horse" },
    ],
  },
  turbopack: {
    root: path.resolve(__dirname),
  },
};

export default nextConfig;
