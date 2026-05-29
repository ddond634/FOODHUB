-- MySQL-compatible schema for Hub e-commerce & ERP integration
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    middle_name VARCHAR(255) NULL,
    last_name VARCHAR(100),
    suffix VARCHAR(50) NULL,
    phone VARCHAR(50) NULL,
    address_line1 VARCHAR(255) NULL,
    address_line2 VARCHAR(255) NULL,
    city VARCHAR(100) NULL,
    province VARCHAR(100) NULL,
    region VARCHAR(100) NULL,
    postal_code VARCHAR(20) NULL,
    role VARCHAR(255) NOT NULL DEFAULT 'customer',
    otp_code VARCHAR(6),
    is_verified SMALLINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sellers (
    id SERIAL PRIMARY KEY,
    user_id INT UNIQUE NOT NULL,
    business_name VARCHAR(255),
    category VARCHAR(100),
    business_permit VARCHAR(512),
    valid_id VARCHAR(512),
    address_proof VARCHAR(512),
    business_logo VARCHAR(512),
    region VARCHAR(100),
    province VARCHAR(100),
    city VARCHAR(100),
    verified SMALLINT DEFAULT 0,
    missing_requirements TEXT,
    shop_status VARCHAR(255) DEFAULT 'pending',
    approved_at TIMESTAMP,
    declined_at TIMESTAMP,
    declined_by INT,
    decline_reason TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (declined_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS riders (
    id SERIAL PRIMARY KEY,
    user_id INT UNIQUE NOT NULL,
    vehicle_type VARCHAR(50),
    driver_license VARCHAR(255),
    valid_id VARCHAR(512),
    vehicle_or_cr VARCHAR(512),
    profile_photo VARCHAR(512),
    plate_number VARCHAR(50),
    verified SMALLINT DEFAULT 0,
    rider_status VARCHAR(255) DEFAULT 'pending',
    availability VARCHAR(255) DEFAULT 'offline',
    current_location VARCHAR(255),
    approved_at TIMESTAMP,
    last_active TIMESTAMP,
    suspended_at TIMESTAMP,
    suspended_by INT,
    suspension_reason TEXT,
    suspension_type VARCHAR(255),
    missing_requirements TEXT,
    declined_at TIMESTAMP,
    declined_by INT,
    decline_reason TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (suspended_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (declined_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS suppliers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    contact VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(12,2) NOT NULL,
    stock INT DEFAULT 0,
    seller_id INT,
    category VARCHAR(100),
    img_url VARCHAR(768),
    manufacture_date DATE,
    expiry_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (seller_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Product variations table for size, flavor, etc.
CREATE TABLE IF NOT EXISTS product_variation_options (
    id SERIAL PRIMARY KEY,
    product_id INT NOT NULL,
    variation_type VARCHAR(50) NOT NULL ,
    variation_value VARCHAR(100) NOT NULL ,
    price_adjustment DECIMAL(12,2) DEFAULT 0.00 ,
    stock INT DEFAULT 0,
    sku VARCHAR(100) UNIQUE ,
    is_available SMALLINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE);

-- Inventory movements for product variations
CREATE TABLE IF NOT EXISTS inventory_movements_variations (
    id SERIAL PRIMARY KEY,
    variation_id INT NOT NULL,
    qty INT NOT NULL,
    movement_type VARCHAR(255) NOT NULL,
    ref VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (variation_id) REFERENCES product_variation_options(id) ON DELETE CASCADE);

CREATE TABLE IF NOT EXISTS inventory_movements (
    id SERIAL PRIMARY KEY,
    product_id INT NOT NULL,
    qty INT NOT NULL,
    movement_type VARCHAR(255) NOT NULL,
    ref VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    customer_id INT,
    customer_name VARCHAR(255),
    customer_phone VARCHAR(50),
    customer_address TEXT,
    subtotal DECIMAL(12,2),
    delivery_fee DECIMAL(12,2),
    total DECIMAL(12,2),
    payment VARCHAR(100),
    status VARCHAR(255) DEFAULT 'placed',
    rider_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    delivered_at TIMESTAMP NULL,
    FOREIGN KEY (rider_id) REFERENCES riders(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT,
    variation_id INT DEFAULT NULL,
    variation_details TEXT ,
    quantity INT DEFAULT 1,
    price DECIMAL(12,2),
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (variation_id) REFERENCES product_variation_options(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS purchase_orders (
    id SERIAL PRIMARY KEY,
    supplier_id INT,
    status VARCHAR(255) DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
);

CREATE TABLE IF NOT EXISTS purchase_order_items (
    id SERIAL PRIMARY KEY,
    po_id INT NOT NULL,
    product_id INT,
    quantity INT DEFAULT 1,
    price DECIMAL(12,2),
    FOREIGN KEY (po_id) REFERENCES purchase_orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Refresh tokens table for token rotation and revocation
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    revoked SMALLINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Wishlist table for user saved products
CREATE TABLE IF NOT EXISTS wishlist (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    price_total DECIMAL(12,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, product_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE);

-- Cart items table for shopping cart
CREATE TABLE IF NOT EXISTS cart_items (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    variation_id INT DEFAULT NULL,
    quantity INT NOT NULL DEFAULT 1,
    price_total DECIMAL(12,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ,
    UNIQUE (user_id, product_id, variation_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (variation_id) REFERENCES product_variation_options(id) ON DELETE CASCADE);

-- Customer-to-Seller Chat Tables
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL,
    seller_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ,
    FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (seller_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (customer_id, seller_id));

CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    conversation_id INT NOT NULL,
    sender_id INT NOT NULL,
    sender_type VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    is_read SMALLINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE);

-- Audit logs table for admin actions
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    target_type VARCHAR(255) NOT NULL,
    target_id INT NOT NULL,
    action_type VARCHAR(255) NOT NULL,
    reason TEXT,
    amount DECIMAL(12,2),
    duration_days INT,
    admin_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE SET NULL);

-- Notifications table for user notifications
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    type VARCHAR(50) DEFAULT 'general',
    title VARCHAR(255) NOT NULL,
    body TEXT,
    message TEXT,
    action_url VARCHAR(512),
    "read" SMALLINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE);

-- Performance indexes for frequently queried columns
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_products_seller ON products(seller_id);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);
CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id);

-- Verification documents table for seller/rider uploads
CREATE TABLE IF NOT EXISTS verification_documents (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    user_type VARCHAR(255) NOT NULL,
    document_type VARCHAR(100) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(255) DEFAULT 'pending',
    admin_notes TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE);



-- Helpful admin queries
-- SELECT o.*, oi.product_id, oi.quantity, oi.price FROM orders o LEFT JOIN order_items oi ON oi.order_id=o.id ORDER BY o.created_at DESC;
-- SELECT * FROM products WHERE seller_id=?;
-- SELECT * FROM inventory_movements WHERE product_id=? ORDER BY created_at DESC;
