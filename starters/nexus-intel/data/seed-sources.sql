-- Nexus Intel — starter seed sources (public data)
-- Sales intelligence / B2B GTM tools competitive commentary.
-- Sources: 17 public companies, 16 public thought leaders, 8 subreddits.
-- All LinkedIn handles point to publicly visible profiles.
-- Swap for your own ICP. See docs/voice-dna.md.

------------------------------------------------------------------------
-- COMPETITORS — Tier 1 (direct sales intelligence competitors)
------------------------------------------------------------------------
INSERT OR IGNORE INTO sources (platform, handle, url, name, company, country, relevance, tier, verticals, notes) VALUES
  ('linkedin', 'clay-hq', 'https://www.linkedin.com/company/clay-hq/', 'Clay', 'Clay', 'US', 'competitor', 'tier-1', 'sales-intelligence,data-enrichment', 'GTM engineering platform. Waterfall enrichment, AI-powered prospecting. Positioning as "GTM engineering" vs data vendor. Rising fast in the GTM engineering space.'),
  ('linkedin', 'zoominfo', 'https://www.linkedin.com/company/zoominfo/', 'ZoomInfo', 'ZoomInfo', 'US', 'competitor', 'tier-1', 'sales-intelligence,data-enrichment', 'Incumbent leader. 600M+ profiles, intent data, engagement. Enterprise-heavy pricing creates vulnerability in SMB/mid-market. Pricing complaints surface consistently from SMB and mid-market buyers.'),
  ('linkedin', 'lushadata', 'https://www.linkedin.com/company/lushadata/', 'Lusha', 'Lusha', 'IL', 'competitor', 'tier-1', 'sales-intelligence,data-enrichment', 'Contact data platform. Strong in EMEA. Simpler product, lower price point. Competes on ease of use.'),
  ('linkedin', 'cognism', 'https://www.linkedin.com/company/cognism/', 'Cognism', 'Cognism', 'UK', 'competitor', 'tier-1', 'sales-intelligence,data-enrichment', 'B2B data provider. Strong EMEA coverage, phone-verified mobile numbers. Diamond Data differentiator.'),
  ('linkedin', 'apolloio', 'https://www.linkedin.com/company/apolloio/', 'Apollo.io', 'Apollo.io', 'US', 'competitor', 'tier-1', 'sales-intelligence,outbound,data-enrichment', 'Major all-in-one sales platform. Track positioning, community activity, and audience response.');

------------------------------------------------------------------------
-- COMPETITORS — Tier 2 (secondary data/enrichment competitors)
------------------------------------------------------------------------
INSERT OR IGNORE INTO sources (platform, handle, url, name, company, country, relevance, tier, verticals, notes) VALUES
  ('linkedin', 'seamlessai', 'https://www.linkedin.com/company/seamlessai/', 'Seamless.AI', 'Seamless.AI', 'US', 'competitor', 'tier-2', 'sales-intelligence,data-enrichment', 'Real-time contact search. Lower-end market. Lower-end market presence.'),
  ('linkedin', 'clearbit', 'https://www.linkedin.com/company/clearbit/', 'Clearbit', 'HubSpot', 'US', 'competitor', 'tier-2', 'data-enrichment', 'Acquired by HubSpot 2023. Enrichment + reveal. Now part of HubSpot ecosystem — watch for deeper HubSpot integration signals.'),
  ('linkedin', 'rocketreach.co', 'https://www.linkedin.com/company/rocketreach.co/', 'RocketReach', 'RocketReach', 'US', 'competitor', 'tier-2', 'data-enrichment', 'Contact lookup tool. Lower tier — competes on price and simplicity.'),
  ('linkedin', 'leadiq-inc', 'https://www.linkedin.com/company/leadiq-inc/', 'LeadIQ', 'LeadIQ', 'US', 'competitor', 'tier-2', 'sales-intelligence,outbound', 'Prospecting platform with contact capture and CRM sync. Competes with Apollo on workflow.'),
  ('linkedin', 'orumhq', 'https://www.linkedin.com/company/orumhq/', 'Orum', 'Orum', 'US', 'competitor', 'tier-2', 'outbound', 'AI-powered dialer and live conversation platform. Parallel dialing competitor.');

------------------------------------------------------------------------
-- COMPETITORS — Adjacent (engagement/sales tools that overlap with Apollo)
------------------------------------------------------------------------
INSERT OR IGNORE INTO sources (platform, handle, url, name, company, country, relevance, tier, verticals, notes) VALUES
  ('linkedin', 'outreach-saas', 'https://www.linkedin.com/company/outreach-saas/', 'Outreach', 'Outreach', 'US', 'competitor', 'adjacent', 'outbound,engagement', 'Sales engagement platform. Pure-play sequences — no data layer. Apollo''s "all-in-one" pitch directly counters this.'),
  ('linkedin', 'salesloft', 'https://www.linkedin.com/company/salesloft/', 'Salesloft', 'Salesloft', 'US', 'competitor', 'adjacent', 'outbound,engagement', 'Sales engagement platform. Acquired by Vista Equity. Competes with Outreach and Apollo on sequence management.'),
  ('linkedin', 'gong-io', 'https://www.linkedin.com/company/gong-io/', 'Gong', 'Gong', 'US', 'competitor', 'adjacent', 'revenue-intelligence', 'Conversation intelligence + revenue intelligence. Adjacent competitor — tracks deals, not contacts.'),
  ('linkedin', 'nooksapp', 'https://www.linkedin.com/company/nooksapp/', 'Nooks', 'Nooks', 'US', 'competitor', 'adjacent', 'outbound', 'AI-powered parallel dialer and virtual salesfloor. SDR productivity tool.'),
  ('linkedin', 'hubspot', 'https://www.linkedin.com/company/hubspot/', 'HubSpot', 'HubSpot', 'US', 'competitor', 'adjacent', 'crm,engagement', 'CRM + Sales Hub. Now owns Clearbit. Watch for deeper enrichment integration into HubSpot core.'),
  ('linkedin', 'instantlyapp', 'https://www.linkedin.com/company/instantlyapp/', 'Instantly', 'Instantly', 'US', 'competitor', 'adjacent', 'outbound,engagement', 'Cold email at scale. Lead database + email warmup + sequences. Competes with Apollo on outbound email.'),
  ('linkedin', 'reply-io', 'https://www.linkedin.com/company/reply-io/', 'Reply.io', 'Reply.io', 'US', 'competitor', 'adjacent', 'outbound,engagement', 'Multichannel outreach platform. Strong in EMEA. AI SDR agent competitor.');

------------------------------------------------------------------------
-- THOUGHT LEADERS — Sales/GTM voices in Apollo's vertical
------------------------------------------------------------------------
INSERT OR IGNORE INTO sources (platform, handle, url, name, title, company, country, relevance, verticals, notes) VALUES
  ('linkedin', 'hschuck', 'https://www.linkedin.com/in/hschuck/', 'Henry Schuck', 'CEO & Founder', 'ZoomInfo', 'US', 'thought-leader', 'sales-intelligence,data-enrichment', 'ZoomInfo CEO. Public company CEO voice. Track for competitive positioning and market narrative.'),
  ('linkedin', 'chriswalker171', 'https://www.linkedin.com/in/chriswalker171/', 'Chris Walker', 'CEO', 'Passetto', 'US', 'thought-leader', 'gtm-engineering,revenue-ops', 'Refine Labs → Passetto. Dark social, demand gen, GTM strategy. Massive LinkedIn following. Shapes how revenue leaders think about GTM.'),
  ('linkedin', 'sahilmansuri', 'https://www.linkedin.com/in/sahilmansuri/', 'Sahil Mansuri', 'CEO', 'Bravado', 'US', 'thought-leader', 'outbound,sales-intelligence', 'Bravado CEO. Sales community builder. Voice of the SDR/AE community.'),
  ('linkedin', 'retentionadam', 'https://www.linkedin.com/in/retentionadam/', 'Adam Robinson', 'CEO', 'RB2B', 'US', 'thought-leader', 'gtm-engineering,data-enrichment', 'RB2B founder. Website visitor identification. Signal-based selling evangelist. Posts prolifically on LinkedIn.'),
  ('linkedin', 'jasonmlemkin', 'https://www.linkedin.com/in/jasonmlemkin/', 'Jason Lemkin', 'Founder', 'SaaStr', 'US', 'thought-leader', 'sales-intelligence,revenue-ops', 'SaaStr founder. SaaS industry elder statesman. Revenue leadership commentary.'),
  ('linkedin', 'nick-cegelski', 'https://www.linkedin.com/in/nick-cegelski/', 'Nick Cegelski', 'Co-Host', '30 Minutes to President''s Club', 'US', 'thought-leader', 'outbound,sales-intelligence', '30MPC co-host. Tactical sales content — cold calling, email sequences, objection handling. SDR audience goldmine.'),
  ('linkedin', 'armand-farrokh', 'https://www.linkedin.com/in/armand-farrokh/', 'Armand Farrokh', 'Co-Host', '30 Minutes to President''s Club', 'US', 'thought-leader', 'outbound,sales-intelligence', '30MPC co-host. Tactical sales content. Their audience IS Apollo''s ICP.'),
  ('linkedin', 'samsalesli', 'https://www.linkedin.com/in/samsalesli/', 'Sam McKenna', 'Founder', '#samsales Consulting', 'US', 'thought-leader', 'outbound,content-marketing', '#samsales founder. LinkedIn prospecting expert. "Show Me You Know Me" methodology.'),
  ('linkedin', 'kyletcoleman', 'https://www.linkedin.com/in/kyletcoleman/', 'Kyle Coleman', 'VP Marketing', 'ClickUp', 'US', 'thought-leader', 'gtm-engineering,outbound', 'Ex-Clari CMO, now ClickUp. AI-powered GTM thought leader. Prolific LinkedIn poster on outbound + GTM engineering.'),
  ('linkedin', 'beccholland-flipthescript', 'https://www.linkedin.com/in/beccholland-flipthescript/', 'Becc Holland', 'Founder & CEO', 'Flip the Script', 'US', 'thought-leader', 'outbound,content-marketing', 'Flip the Script founder. Cold outreach methodology. "Pattern interrupts" in cold email/calling.'),
  ('linkedin', 'mkosoglow', 'https://www.linkedin.com/in/mkosoglow/', 'Mark Kosoglow', 'Operator', 'Operator', 'US', 'thought-leader', 'outbound,revenue-ops', 'Ex-Outreach VP Sales. Sales leadership and outbound strategy voice. Deep engagement tool experience.'),
  ('linkedin', 'trishbertuzzi', 'https://www.linkedin.com/in/trishbertuzzi/', 'Trish Bertuzzi', 'Founder & CEO', 'The Bridge Group', 'US', 'thought-leader', 'sales-intelligence,outbound', 'The Bridge Group founder. Inside sales pioneer. SDR metrics and benchmarks authority.'),
  ('linkedin', 'morganjingramamp', 'https://www.linkedin.com/in/morganjingramamp/', 'Morgan Ingram', 'CEO', 'AMP Social', 'US', 'thought-leader', 'outbound,content-marketing', '4x LinkedIn Top Sales Voice. "Making Sales Human in an AI World." Outbound coaching + creator. Trained HubSpot, Snowflake, Salesforce teams.'),
  ('linkedin', 'voleksiienko', 'https://www.linkedin.com/in/voleksiienko/', 'Vlad Oleksiienko', 'VP of Growth', 'Reply.io', 'UA', 'thought-leader', 'outbound,engagement', 'Reply.io VP Growth. Multichannel outreach expert. Track for Reply.io positioning signals.'),
  ('linkedin', 'josh-braun', 'https://www.linkedin.com/in/josh-braun/', 'Josh Braun', 'Sales Trainer', 'Josh Braun', 'US', 'thought-leader', 'outbound,content-marketing', 'Badass B2B Growth Guide creator. "Radically honest" sales methodology. Anti-commission-breath approach. Weekly LinkedIn content.'),
  ('linkedin', 'williamallred', 'https://www.linkedin.com/in/williamallred/', 'Will Allred', 'Co-Founder', 'Lavender', 'US', 'thought-leader', 'outbound,ai-sales-tools', 'Lavender.ai co-founder. AI email coaching. Cold email data + best practices. Billions of analyzed sales emails.');

------------------------------------------------------------------------
-- COMMUNITIES — Subreddits (Reddit pain-point mining)
------------------------------------------------------------------------
INSERT OR IGNORE INTO sources (platform, handle, url, name, country, relevance, verticals, notes) VALUES
  ('reddit', 'sales', 'https://reddit.com/r/sales', 'r/sales', 'GLOBAL', 'community', 'outbound,sales-intelligence', 'Largest sales subreddit. SDRs/AEs venting about tools, data quality, sequences. Top source for audience pain-point signals.'),
  ('reddit', 'prospecting', 'https://reddit.com/r/prospecting', 'r/prospecting', 'GLOBAL', 'community', 'outbound,data-enrichment', 'Prospecting-specific subreddit. Tool comparisons, data quality complaints, workflow frustrations.'),
  ('reddit', 'salesdevelopment', 'https://reddit.com/r/salesdevelopment', 'r/salesdevelopment', 'GLOBAL', 'community', 'outbound', 'SDR/BDR subreddit. Career + tooling discussions. "What tools do you use" threads are signal goldmines.'),
  ('reddit', 'revops', 'https://reddit.com/r/revops', 'r/revops', 'GLOBAL', 'community', 'revenue-ops,data-enrichment', 'Revenue operations subreddit. Data hygiene, enrichment, CRM integration, tool stack discussions.'),
  ('reddit', 'SaaS', 'https://reddit.com/r/SaaS', 'r/SaaS', 'GLOBAL', 'community', 'sales-intelligence', 'SaaS subreddit. GTM strategy, tool recommendations, fundraising context.'),
  ('reddit', 'startups', 'https://reddit.com/r/startups', 'r/startups', 'GLOBAL', 'community', 'sales-intelligence', 'Startup subreddit. Early-stage founders evaluating sales tools — high-intent context.'),
  ('reddit', 'coldoutreach', 'https://reddit.com/r/coldoutreach', 'r/coldoutreach', 'GLOBAL', 'community', 'outbound', 'Cold outreach subreddit. Email deliverability, sequence strategies, tool comparisons.'),
  ('reddit', 'b2bsales', 'https://reddit.com/r/b2bsales', 'r/b2bsales', 'GLOBAL', 'community', 'outbound,sales-intelligence', 'B2B sales subreddit. Enterprise selling, prospecting tools, methodology discussions.');

