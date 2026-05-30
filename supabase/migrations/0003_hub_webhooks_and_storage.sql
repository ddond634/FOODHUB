-- Hub database webhooks: dispatch row changes to webhook_handler edge function
-- Replaces client polling with push-driven updates via Realtime broadcast.

CREATE EXTENSION IF NOT EXISTS pg_net WITH SCHEMA extensions;

CREATE OR REPLACE FUNCTION public.hub_dispatch_webhook()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
  payload jsonb;
  webhook_url text := 'https://sfeccfbdmbwoblixyoti.supabase.co/functions/v1/webhook_handler';
  anon_key text := 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNmZWNjZmJkbWJ3b2JsaXh5b3RpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwODAwNTksImV4cCI6MjA5NTY1NjA1OX0.uM7DX7T-PQqPsMIwh-Fna1BUtVkkOhR4PiT2YqYlhIE';
BEGIN
  payload := jsonb_build_object(
    'type', TG_OP,
    'table', TG_TABLE_NAME,
    'schema', TG_TABLE_SCHEMA,
    'record', CASE WHEN TG_OP = 'DELETE' THEN NULL ELSE to_jsonb(NEW) END,
    'old_record', CASE WHEN TG_OP = 'INSERT' THEN NULL ELSE to_jsonb(OLD) END
  );

  PERFORM net.http_post(
    url := webhook_url,
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'Authorization', 'Bearer ' || anon_key,
      'apikey', anon_key
    ),
    body := payload
  );

  RETURN COALESCE(NEW, OLD);
END;
$$;

-- Products catalog updates
DROP TRIGGER IF EXISTS hub_webhook_products ON public.products;
CREATE TRIGGER hub_webhook_products
AFTER INSERT OR UPDATE OR DELETE ON public.products
FOR EACH ROW EXECUTE FUNCTION public.hub_dispatch_webhook();

-- Active shop / seller updates
DROP TRIGGER IF EXISTS hub_webhook_sellers ON public.sellers;
CREATE TRIGGER hub_webhook_sellers
AFTER INSERT OR UPDATE OR DELETE ON public.sellers
FOR EACH ROW EXECUTE FUNCTION public.hub_dispatch_webhook();

-- Order lifecycle updates (complements pg_notify triggers in 0001)
DROP TRIGGER IF EXISTS hub_webhook_orders ON public.orders;
CREATE TRIGGER hub_webhook_orders
AFTER INSERT OR UPDATE OR DELETE ON public.orders
FOR EACH ROW EXECUTE FUNCTION public.hub_dispatch_webhook();

-- Ensure hub_uploads storage bucket exists (public read for product images)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'hub_uploads',
  'hub_uploads',
  true,
  52428800,
  ARRAY['image/png', 'image/jpeg', 'image/webp', 'image/gif']::text[]
)
ON CONFLICT (id) DO UPDATE SET
  public = EXCLUDED.public,
  file_size_limit = EXCLUDED.file_size_limit,
  allowed_mime_types = EXCLUDED.allowed_mime_types;

-- Public read policy for hub_uploads
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'storage' AND tablename = 'objects' AND policyname = 'hub_uploads_public_read'
  ) THEN
    CREATE POLICY hub_uploads_public_read ON storage.objects
      FOR SELECT
      USING (bucket_id = 'hub_uploads');
  END IF;
END $$;
