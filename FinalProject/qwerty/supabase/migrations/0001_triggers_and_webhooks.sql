-- Triggers and functions for Hub app
-- 1) Notify an internal channel when a new order is created
-- 2) Example webhook call on order status change (using pg_notify for Edge Function to consume)

-- Function: notify_new_order
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

-- Trigger: call notify_new_order after insert on orders
DROP TRIGGER IF EXISTS orders_notify_insert ON orders;
CREATE TRIGGER orders_notify_insert
AFTER INSERT ON orders
FOR EACH ROW EXECUTE FUNCTION notify_new_order();


-- Function: notify_order_status_change (emit notification on status change)
CREATE OR REPLACE FUNCTION notify_order_status_change() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    payload json;
BEGIN
    IF NEW.status IS DISTINCT FROM OLD.status THEN
        payload := json_build_object(
            'order_id', NEW.id,
            'old_status', OLD.status,
            'new_status', NEW.status,
            'changed_at', now()
        );
        PERFORM pg_notify('order_status_changes', payload::text);
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS orders_status_change ON orders;
CREATE TRIGGER orders_status_change
AFTER UPDATE ON orders
FOR EACH ROW EXECUTE FUNCTION notify_order_status_change();


-- Note: Set up an Edge Function or external process to LISTEN on these channels
-- Example Edge Function can LISTEN to 'orders_channel' and 'order_status_changes'
