-- SQLite schema for Hub e-commerce & ERP integration
PRAGMA foreign_keys=ON;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    role TEXT CHECK(role IN ('admin','customer','seller','rider')) NOT NULL DEFAULT 'customer',
    otp_code TEXT,
    is_verified INTEGER DEFAULT 0,
    created_at TEXT
);

CREATE TABLE sellers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    business_name TEXT,
    category TEXT,
    region TEXT,
    province TEXT,
    city TEXT,
    verified INTEGER DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE riders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    vehicle_type TEXT,
    driver_license TEXT,
    plate_number TEXT,
    verified INTEGER DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    contact TEXT
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL,
    stock INTEGER DEFAULT 0,
    seller_id INTEGER,
    category TEXT,
    img_url TEXT,
    created_at TEXT,
    FOREIGN KEY(seller_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Inventory / ERP movements
CREATE TABLE inventory_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    qty INTEGER NOT NULL,
    movement_type TEXT CHECK(movement_type IN ('sale','purchase','adjustment')) NOT NULL,
    ref TEXT,
    created_at TEXT,
    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    customer_name TEXT,
    customer_phone TEXT,
    customer_address TEXT,
    subtotal REAL,
    delivery_fee REAL,
    total REAL,
    payment TEXT,
    status TEXT CHECK(status IN ('placed','pending','processing','ready','dispatched','in-transit','shipped','delivered','completed','cancelled')) DEFAULT 'placed',
    rider_id INTEGER,
    created_at TEXT,
    delivered_at TEXT,
    FOREIGN KEY(rider_id) REFERENCES riders(id) ON DELETE SET NULL
);

CREATE TABLE order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER,
    quantity INTEGER DEFAULT 1,
    price REAL,
    FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY(product_id) REFERENCES products(id)
);

-- Purchase Orders for ERP
CREATE TABLE purchase_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER,
    status TEXT CHECK(status IN ('draft','ordered','received','closed')) DEFAULT 'draft',
    created_at TEXT,
    FOREIGN KEY(supplier_id) REFERENCES suppliers(id)
);

CREATE TABLE purchase_order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    po_id INTEGER NOT NULL,
    product_id INTEGER,
    quantity INTEGER DEFAULT 1,
    price REAL,
    FOREIGN KEY(po_id) REFERENCES purchase_orders(id) ON DELETE CASCADE,
    FOREIGN KEY(product_id) REFERENCES products(id)
);

-- Refresh tokens for secure session rotation and revocation
CREATE TABLE refresh_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_hash TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked INTEGER DEFAULT 0,
    created_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Simple sample data (optional) --
-- see server.py seed_data doing actual inserts

-- OTP table for verification codes
CREATE TABLE IF NOT EXISTS otp_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT,
    code TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used INTEGER DEFAULT 0,
    attempts INTEGER DEFAULT 0,
    created_at TEXT
);

-- Wishlist table
CREATE TABLE IF NOT EXISTS wishlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    created_at TEXT,
    UNIQUE(user_id, product_id),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- Reviews table
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    rating INTEGER CHECK(rating >= 1 AND rating <= 5),
    title TEXT,
    body TEXT,
    created_at TEXT,
    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Notifications table
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    title TEXT,
    body TEXT,
    read INTEGER DEFAULT 0,
    metadata TEXT,
    created_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Useful Queries (examples):
-- 1. Create Order (transactional):
-- BEGIN;
-- INSERT INTO orders (customer_name,customer_phone,customer_address,subtotal,delivery_fee,total,payment,status,created_at) VALUES (?,?,?,?,?,?,?,?,?);
-- INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?,?,?,?);
-- UPDATE products SET stock = stock - ? WHERE id=?;
-- INSERT INTO inventory_movements (product_id,qty,movement_type,ref,created_at) VALUES (?,?,?,?,?);
-- COMMIT;

-- 2. Automatic purchase order if below threshold
-- Notifications table
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT,
    body TEXT,
    read INTEGER DEFAULT 0,
    metadata TEXT,
    created_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Rider location tracking (for real-time delivery tracking)
CREATE TABLE IF NOT EXISTS rider_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rider_id INTEGER NOT NULL,
    order_id INTEGER,
    latitude REAL,
    longitude REAL,
    updated_at TEXT,
    FOREIGN KEY(rider_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE SET NULL
);

-- Proof of delivery (photos/signatures)
CREATE TABLE IF NOT EXISTS proof_of_delivery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    rider_id INTEGER,
    image_url TEXT,
    signature_url TEXT,
    notes TEXT,
    created_at TEXT,
    FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY(rider_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Disputes table for handling complaints
CREATE TABLE IF NOT EXISTS disputes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    complainant_id INTEGER,
    complainant_role TEXT,
    description TEXT,
    status TEXT DEFAULT 'open',
    resolution TEXT,
    created_at TEXT,
    resolved_at TEXT,
    FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY(complainant_id) REFERENCES users(id)
);

-- Rider earnings tracking
CREATE TABLE IF NOT EXISTS rider_earnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rider_id INTEGER NOT NULL,
    order_id INTEGER,
    amount REAL,
    created_at TEXT,
    FOREIGN KEY(rider_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE SET NULL
);

-- Rider payouts
CREATE TABLE IF NOT EXISTS rider_payouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rider_id INTEGER NOT NULL,
    amount REAL,
    status TEXT DEFAULT 'pending',
    payment_method TEXT,
    payout_date TEXT,
    created_at TEXT,
    FOREIGN KEY(rider_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Sample queries for reference
-- 1. Get seller's products by category
-- SELECT * FROM products WHERE seller_id=? AND category=? ORDER BY created_at DESC;

-- 2. Get customer orders with full details
-- SELECT o.*, GROUP_CONCAT(p.title) as items FROM orders o 
-- LEFT JOIN order_items oi ON o.id=oi.order_id 
-- LEFT JOIN products p ON oi.product_id=p.id 
-- WHERE o.customer_id=? 
-- GROUP BY o.id 
-- ORDER BY o.created_at DESC;

-- 3. Get seller's pending orders
-- SELECT o.id, o.customer_name, COUNT(oi.id) as item_count, SUM(oi.quantity) as total_qty 
-- FROM orders o 
-- INNER JOIN order_items oi ON o.id=oi.order_id 
-- INNER JOIN products p ON oi.product_id=p.id 
-- WHERE p.seller_id=? AND o.status IN ('placed', 'processing') 
-- GROUP BY o.id 
-- ORDER BY o.created_at ASC;

-- 4. Get available deliveries for rider
-- SELECT o.id, o.customer_name, o.customer_address, COUNT(oi.id) as items 
-- FROM orders o 
-- LEFT JOIN order_items oi ON o.id=oi.order_id 
-- WHERE o.status='ready' AND o.rider_id IS NULL 
-- GROUP BY o.id;

-- 5. Get top rated products
-- SELECT p.id, p.title, AVG(r.rating) as avg_rating, COUNT(r.id) as review_count 
-- FROM products p 
-- LEFT JOIN reviews r ON p.id=r.product_id 
-- GROUP BY p.id 
-- HAVING review_count > 0 
-- ORDER BY avg_rating DESC;
