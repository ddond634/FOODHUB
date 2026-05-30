-- Ensure rider profile exists for demo rider account
INSERT INTO riders (user_id, verified, rider_status, availability)
SELECT id, 1, 'active', 'online'
FROM users
WHERE email = 'rider@example.com'
ON CONFLICT (user_id) DO UPDATE SET
  verified = EXCLUDED.verified,
  rider_status = EXCLUDED.rider_status,
  availability = EXCLUDED.availability;
