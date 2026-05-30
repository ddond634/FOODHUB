Supabase Edge Functions for FOODHUB

This folder contains Edge Functions to replace parts of the Flask backend with Supabase serverless routes.

Included functions:
- `get_users` - GET - returns up to 100 users from the `users` table.
- `create_order` - POST - creates an order in the `orders` table and inserts related `order_items`.
- `product_api` - GET - public product routes for listing, search, suggestions, and fetching product details.

Deploying functions
1. Ensure you are linked to your project (`supabase link --project-ref <ref>`).
2. Add the required secrets in Supabase dashboard or via CLI:
   - `SUPABASE_URL` (project URL)
   - `SUPABASE_SERVICE_ROLE_KEY` (service role key) for write operations
   - `SUPABASE_ANON_KEY` for read-only product endpoints if needed
   - `JWT_SECRET` for `commerce_api` (must match Flask `.env` JWT_SECRET so Hub login tokens work)

Example deploy commands:

```
supabase functions deploy get_users --project-ref sfeccfbdmbwoblixyoti
supabase functions deploy create_order --project-ref sfeccfbdmbwoblixyoti
supabase functions deploy product_api --project-ref sfeccfbdmbwoblixyoti
supabase functions deploy commerce_api --project-ref sfeccfbdmbwoblixyoti
supabase secrets set JWT_SECRET=your-secret-key-change-in-production --project-ref sfeccfbdmbwoblixyoti
```

Call the functions
- GET https://<functions-base>/get_users
- POST https://<functions-base>/create_order with JSON body
- GET https://<functions-base>/product_api/products/suggestions?q=term
- GET https://<functions-base>/product_api/products/:id
- GET https://<functions-base>/product_api/products

Notes
- `create_order` now maps frontend order payload fields to the `orders` table schema and writes `order_items`.
- `product_api` is a public product route replacement for legacy Flask product search and suggestions.
- Continue converting additional authenticated routes and storefront APIs into functions as the backend migration progresses.
