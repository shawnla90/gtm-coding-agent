export type DrawerType = "signal" | "source" | "engager";

export interface DrawerTarget {
  type: DrawerType;
  id: number;
}

export interface EngagerDrawerData {
  id: number;
  name: string | null;
  title: string | null;
  company: string | null;
  profileUrl: string | null;
  profileImageUrl: string | null;
  platform: string;
  stars: number | null;
  engagements: {
    id: number;
    engagement_type: string;
    comment_text: string | null;
    post_url: string | null;
    content_title: string | null;
    content_body: string | null;
    source_name: string | null;
  }[];
  reasoning: { signal_title?: string; reasoning: string }[];
}

export interface SignalDrawerLead {
  id: number;
  name: string | null;
  title: string | null;
  company: string | null;
  profile_url: string | null;
  profile_image_url: string | null;
  platform: string;
  overall_stars: number;
}

export interface SignalDrawerData {
  id: number;
  title: string;
  description: string | null;
  signal_type: string;
  urgency: "act-now" | "this-week" | "this-month" | "backlog";
  source_name: string | null;
  source_id: number | null;
  platform: string | null;
  post_published_at: string | null;
  post_age_days: number | null;
  content_url: string | null;
  content_body: string | null;
  content_likes: number;
  content_comments: number;
  outreach_angle: string | null;
  opener_draft: string | null;
  leads: SignalDrawerLead[];
}

export interface SourceDrawerRecentContent {
  id: number;
  title: string | null;
  body: string | null;
  url: string | null;
  published_at: string | null;
  engagement_likes: number;
  engagement_comments: number;
}

export interface SourceDrawerSignalSummary {
  id: number;
  title: string;
  signal_type: string;
  urgency: "act-now" | "this-week" | "this-month" | "backlog";
  post_age_days: number | null;
}

export interface SourceDrawerEngager {
  id: number;
  name: string | null;
  title: string | null;
  company: string | null;
  profile_url: string | null;
  profile_image_url: string | null;
  platform: string;
  overall_stars: number;
}

export interface SourceDrawerData {
  id: number;
  name: string;
  title: string | null;
  company: string | null;
  handle: string | null;
  platform: string;
  relevance: string | null;
  profileUrl: string | null;
  profileImageUrl: string | null;
  followers: number | null;
  stats: {
    total_posts: number;
    signal_count: number;
    icp_engager_count: number;
  };
  recentContent: SourceDrawerRecentContent[];
  signals: SourceDrawerSignalSummary[];
  topEngagers: SourceDrawerEngager[];
}

export type DrawerData =
  | { type: "signal"; data: SignalDrawerData }
  | { type: "source"; data: SourceDrawerData }
  | { type: "engager"; data: EngagerDrawerData };
