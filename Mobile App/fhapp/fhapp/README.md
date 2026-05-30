# FOODHUB Mobile App

Flutter mobile client for the FOODHUB e-commerce platform. It uses the **same Supabase project and database** as the website.

## Shared backend

| Service | URL | Purpose |
|---------|-----|---------|
| Auth | `auth_api` edge function | Login / register against Supabase `users` table |
| Products | `product_api` edge function | Browse, search, best sellers |
| Cart | `commerce_api` edge function | Add, update, remove cart items |
| Storage | `hub_uploads` bucket | Product images |

Credentials are in `lib/config/supabase_config.dart` (same anon key and project ref as the website).

## Features

- Sign in / register (customer accounts)
- Home — best sellers
- Shop — search, category filters, product grid
- Product detail
- Cart — synced with website cart via `commerce_api`
- Profile — account info and sign out

## Run the app

```bash
cd "Mobile App/fhapp/fhapp"
flutter pub get
flutter run
```

For Android emulator, no extra config is needed. For a physical device, ensure internet access to Supabase.

## Deploy auth API (one-time)

The mobile app authenticates via the `auth_api` edge function:

```bash
cd FinalProject/qwerty
supabase secrets set JWT_SECRET=your-secret-key-change-in-production --project-ref sfeccfbdmbwoblixyoti
supabase functions deploy auth_api --project-ref sfeccfbdmbwoblixyoti
```

`JWT_SECRET` must match the website Flask `.env` so cart tokens work with `commerce_api`.

## Project structure

```
lib/
  config/supabase_config.dart   # Shared Supabase URLs & keys
  models/                       # Product, CartItem, HubUser
  services/                     # API client, auth, products, cart
  providers/app_state.dart      # App-wide state
  screens/                      # UI screens
  widgets/product_card.dart
  theme/app_theme.dart
  main.dart
```

## Notes

- Cart items added on mobile appear on the website (and vice versa) for the same account.
- New accounts registered in the app are stored in Supabase Postgres `users`.
- Website accounts created via Flask/MySQL must exist in Supabase Postgres to sign in on mobile; run the MySQL → Supabase migration if needed.
