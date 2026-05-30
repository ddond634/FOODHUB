-- Align live DB with commerce_api checkout and auth profile updates

ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS customer_id INT REFERENCES public.users(id) ON DELETE SET NULL;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS customer_name VARCHAR(255);
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS customer_phone VARCHAR(50);
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS customer_address TEXT;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS subtotal DECIMAL(12,2);
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS delivery_fee DECIMAL(12,2);
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS total DECIMAL(12,2);
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS payment VARCHAR(100);
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS status VARCHAR(255) DEFAULT 'placed';
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS rider_id INT;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS delivered_at TIMESTAMPTZ;

ALTER TABLE public.users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500);
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS gender VARCHAR(50);
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS birthdate DATE;

CREATE INDEX IF NOT EXISTS idx_orders_customer ON public.orders(customer_id);
