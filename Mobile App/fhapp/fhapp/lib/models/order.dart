class HubOrder {
  final int id;
  final String customerName;
  final String customerPhone;
  final String customerAddress;
  final double total;
  final String status;
  final String payment;
  final String? items;
  final double productSubtotal;
  final double riderEarnings;

  const HubOrder({
    required this.id,
    required this.customerName,
    required this.customerPhone,
    required this.customerAddress,
    required this.total,
    required this.status,
    required this.payment,
    this.items,
    this.productSubtotal = 0,
    this.riderEarnings = 0,
  });

  factory HubOrder.fromJson(Map<String, dynamic> json) {
    final subtotal = (json['product_subtotal'] as num?)?.toDouble()
        ?? (json['product_sales'] as num?)?.toDouble()
        ?? 0.0;
    final earnings = (json['rider_earnings'] as num?)?.toDouble()
        ?? (json['delivery_fee'] as num?)?.toDouble()
        ?? (subtotal * 0.025);
    return HubOrder(
      id: (json['id'] as num).toInt(),
      customerName: json['customer_name']?.toString() ?? '',
      customerPhone: json['customer_phone']?.toString() ?? '',
      customerAddress: json['customer_address']?.toString() ?? '',
      total: (json['total'] as num?)?.toDouble() ?? 0,
      status: json['status']?.toString() ?? 'placed',
      payment: json['payment']?.toString() ?? 'Cash on Delivery',
      items: json['items']?.toString(),
      productSubtotal: subtotal,
      riderEarnings: earnings,
    );
  }
}
