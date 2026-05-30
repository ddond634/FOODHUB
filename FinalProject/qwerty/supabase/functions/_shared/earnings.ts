/** Shared FOODHUB earnings rules used by seller_api and rider_api */
export const RIDER_FEE_RATE = 0.025; // 2.5% of product sales (within 2–3% delivery fee range)
export const PLATFORM_COMMISSION_RATE = 0.10; // 10% platform fee on seller product sales

export function roundMoney(value: number): number {
  return Math.round(value * 100) / 100;
}

export function calcRiderEarnings(productSubtotal: number): number {
  return roundMoney(productSubtotal * RIDER_FEE_RATE);
}

export function calcSellerBreakdown(grossSales: number) {
  const rider_fee = roundMoney(grossSales * RIDER_FEE_RATE);
  const platform_commission = roundMoney(grossSales * PLATFORM_COMMISSION_RATE);
  const net_profit = roundMoney(grossSales - rider_fee - platform_commission);
  return { gross_sales: roundMoney(grossSales), rider_fee, platform_commission, net_profit };
}

export const COMPLETED_ORDER_STATUSES = ["delivered", "completed"];
export const ACTIVE_ORDER_STATUSES = ["placed", "ready", "pending", "dispatched", "in-transit", "processing"];
