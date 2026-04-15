"use server";

import {
  getEngagerById,
  getEngagerEngagements,
  getLeadReasoning,
  getSignalDrawerData,
  getSourceDrawerData,
} from "@/lib/db";
import type {
  EngagerDrawerData,
  SignalDrawerData,
  SourceDrawerData,
} from "@/components/drawers/types";

export async function fetchEngagerDrawerData(
  engagerId: number,
): Promise<EngagerDrawerData | null> {
  const engager = getEngagerById(engagerId);
  if (!engager) return null;

  const engagements = getEngagerEngagements(engagerId, 15);
  const reasoning = getLeadReasoning(engagerId);

  return {
    id: engager.id,
    name: engager.name,
    title: engager.title,
    company: engager.company ?? engager.parsed_company,
    profileUrl: engager.profile_url,
    profileImageUrl: engager.profile_image_url,
    platform: engager.platform,
    stars: engager.overall_stars ?? null,
    engagements: engagements.map((e) => ({
      id: e.id,
      engagement_type: e.engagement_type,
      comment_text: e.comment_text,
      post_url: e.post_url,
      content_title: e.content_title,
      content_body: e.content_body,
      source_name: e.source_name,
    })),
    reasoning: reasoning.map((r) => ({
      signal_title: (r as { signal_title?: string }).signal_title,
      reasoning: r.reasoning,
    })),
  };
}

export async function fetchSignalDrawerData(
  signalId: number,
): Promise<SignalDrawerData | null> {
  const payload = getSignalDrawerData(signalId);
  return payload;
}

export async function fetchSourceDrawerData(
  sourceId: number,
): Promise<SourceDrawerData | null> {
  const payload = getSourceDrawerData(sourceId);
  return payload;
}
