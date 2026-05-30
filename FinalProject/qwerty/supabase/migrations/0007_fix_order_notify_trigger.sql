-- Fix checkout failure: notify_new_order referenced NEW.user_id but orders uses customer_id

CREATE OR REPLACE FUNCTION notify_new_order() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    payload json;
BEGIN
    payload := json_build_object(
        'order_id', NEW.id,
        'customer_id', NEW.customer_id,
        'status', NEW.status,
        'created_at', NEW.created_at
    );

    PERFORM pg_notify('orders_channel', payload::text);
    RETURN NEW;
END;
$$;
