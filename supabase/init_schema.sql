-- Video2Text Supabase schema bootstrap
-- Run this in Supabase SQL Editor (project: dcbpysgftwbjasaucbbr)

create extension if not exists pgcrypto;

create table if not exists public.youtube_videos (
  video_id text primary key,
  video_data jsonb,
  transcript text,
  chapters jsonb,
  like_counts integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.key_takeaways_images (
  video_id text primary key references public.youtube_videos(video_id) on delete cascade,
  image_url text,
  status text not null default 'completed' check (status in ('pending', 'completed', 'failed')),
  error_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.user_usage (
  id bigint generated always as identity primary key,
  user_id uuid,
  video_id text not null,
  video_title text,
  action_type text not null default 'analysis',
  created_at timestamptz not null default now()
);

-- Used by backend /api/videos to mark if user liked a video
create table if not exists public.video_likes (
  id bigint generated always as identity primary key,
  user_id uuid not null,
  video_id text not null references public.youtube_videos(video_id) on delete cascade,
  created_at timestamptz not null default now(),
  unique (user_id, video_id)
);

-- Used by frontend favorites
create table if not exists public.user_favorites (
  id bigint generated always as identity primary key,
  user_id uuid not null,
  video_id text not null references public.youtube_videos(video_id) on delete cascade,
  created_at timestamptz not null default now(),
  unique (user_id, video_id)
);

-- Used by frontend sentence comments
create table if not exists public.sentence_comments (
  id uuid primary key default gen_random_uuid(),
  video_id text not null references public.youtube_videos(video_id) on delete cascade,
  section_id text not null,
  sentence_index integer not null,
  sentence_content text not null,
  author text not null,
  avatar text,
  comment_text text not null,
  is_ai_generated boolean not null default false,
  like_count integer not null default 0,
  created_at timestamptz not null default now()
);

create index if not exists idx_user_usage_user_id on public.user_usage(user_id);
create index if not exists idx_user_usage_video_id on public.user_usage(video_id);
create index if not exists idx_video_likes_user_id on public.video_likes(user_id);
create index if not exists idx_video_likes_video_id on public.video_likes(video_id);
create index if not exists idx_user_favorites_user_id on public.user_favorites(user_id);
create index if not exists idx_user_favorites_video_id on public.user_favorites(video_id);
create index if not exists idx_sentence_comments_lookup
  on public.sentence_comments(video_id, section_id, sentence_index, created_at);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists tr_youtube_videos_updated_at on public.youtube_videos;
create trigger tr_youtube_videos_updated_at
before update on public.youtube_videos
for each row
execute function public.set_updated_at();

drop trigger if exists tr_key_takeaways_images_updated_at on public.key_takeaways_images;
create trigger tr_key_takeaways_images_updated_at
before update on public.key_takeaways_images
for each row
execute function public.set_updated_at();

