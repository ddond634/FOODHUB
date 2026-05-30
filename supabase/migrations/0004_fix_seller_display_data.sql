-- Restore human-readable store names and seller profile fields for demo accounts.

UPDATE users SET first_name = 'Fresh', last_name = 'Greens' WHERE email = 'seller1@example.com';
UPDATE users SET first_name = 'Metro', last_name = 'Snacks' WHERE email = 'seller2@example.com';
UPDATE users SET first_name = 'Daily', last_name = 'Bites' WHERE email = 'seller3@example.com';
UPDATE users SET first_name = 'Picnic', last_name = 'Pantry' WHERE email = 'seller4@example.com';
UPDATE users SET first_name = 'Baker', last_name = 'Corner' WHERE email = 'seller5@example.com';

UPDATE sellers SET
  business_name = 'Fresh Greens Market',
  category = 'Produce',
  city = 'Quezon City',
  province = 'Metro Manila',
  region = 'NCR'
WHERE user_id = (SELECT id FROM users WHERE email = 'seller1@example.com');

UPDATE sellers SET
  business_name = 'Metro Snacks Co.',
  category = 'Snacks',
  city = 'Makati City',
  province = 'Metro Manila',
  region = 'NCR'
WHERE user_id = (SELECT id FROM users WHERE email = 'seller2@example.com');

UPDATE sellers SET
  business_name = 'Daily Bites Kitchen',
  category = 'Prepared Meals',
  city = 'Pasig City',
  province = 'Metro Manila',
  region = 'NCR'
WHERE user_id = (SELECT id FROM users WHERE email = 'seller3@example.com');

UPDATE sellers SET
  business_name = 'Picnic Pantry',
  category = 'Beverages',
  city = 'Taguig City',
  province = 'Metro Manila',
  region = 'NCR'
WHERE user_id = (SELECT id FROM users WHERE email = 'seller4@example.com');

UPDATE sellers SET
  business_name = 'Baker''s Corner',
  category = 'Bakery',
  city = 'Manila',
  province = 'Metro Manila',
  region = 'NCR'
WHERE user_id = (SELECT id FROM users WHERE email = 'seller5@example.com');
