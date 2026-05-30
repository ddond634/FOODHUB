class SellerDashboardStats {
  final double salesMonth;
  final double salesToday;
  final double netProfitMonth;
  final double netProfit;
  final int totalOrders;
  final int pendingOrders;

  const SellerDashboardStats({
    required this.salesMonth,
    required this.salesToday,
    required this.netProfitMonth,
    required this.netProfit,
    required this.totalOrders,
    required this.pendingOrders,
  });

  factory SellerDashboardStats.fromJson(Map<String, dynamic> json) {
    return SellerDashboardStats(
      salesMonth: (json['sales_month'] as num?)?.toDouble() ?? 0,
      salesToday: (json['sales_today'] as num?)?.toDouble() ?? 0,
      netProfitMonth: (json['net_profit_month'] as num?)?.toDouble() ?? 0,
      netProfit: (json['net_profit'] as num?)?.toDouble() ?? 0,
      totalOrders: (json['total_orders'] as num?)?.toInt() ?? 0,
      pendingOrders: (json['pending_orders'] as num?)?.toInt() ?? 0,
    );
  }
}

class SellerOrderEarning {
  final int orderId;
  final String orderDate;
  final String status;
  final double grossSales;
  final double riderFee;
  final double platformCommission;
  final double netProfit;

  const SellerOrderEarning({
    required this.orderId,
    required this.orderDate,
    required this.status,
    required this.grossSales,
    required this.riderFee,
    required this.platformCommission,
    required this.netProfit,
  });

  factory SellerOrderEarning.fromJson(Map<String, dynamic> json) {
    return SellerOrderEarning(
      orderId: (json['order_id'] as num).toInt(),
      orderDate: json['order_date']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      grossSales: (json['gross_sales'] as num?)?.toDouble() ?? 0,
      riderFee: (json['rider_fee'] as num?)?.toDouble() ?? 0,
      platformCommission: (json['platform_commission'] as num?)?.toDouble() ?? 0,
      netProfit: (json['net_profit'] as num?)?.toDouble() ?? 0,
    );
  }
}

class SellerEarningsSummary {
  final double grossRevenue;
  final double netProfit;
  final double riderFees;
  final double platformCommission;
  final List<SellerOrderEarning> transactions;

  const SellerEarningsSummary({
    required this.grossRevenue,
    required this.netProfit,
    required this.riderFees,
    required this.platformCommission,
    required this.transactions,
  });

  factory SellerEarningsSummary.fromJson(Map<String, dynamic> json) {
    final txns = json['transactions'] as List<dynamic>? ?? [];
    return SellerEarningsSummary(
      grossRevenue: (json['gross_revenue'] as num?)?.toDouble() ?? 0,
      netProfit: (json['net_profit'] as num?)?.toDouble() ?? (json['total_earnings'] as num?)?.toDouble() ?? 0,
      riderFees: (json['rider_fees'] as num?)?.toDouble() ?? 0,
      platformCommission: (json['platform_commission'] as num?)?.toDouble() ?? 0,
      transactions: txns.map((e) => SellerOrderEarning.fromJson(e as Map<String, dynamic>)).toList(),
    );
  }
}

class RiderDashboardStats {
  final double totalEarnings;
  final double earningsToday;
  final int completedDeliveries;
  final int activeDeliveries;
  final double riderFeeRate;

  const RiderDashboardStats({
    required this.totalEarnings,
    required this.earningsToday,
    required this.completedDeliveries,
    required this.activeDeliveries,
    required this.riderFeeRate,
  });

  factory RiderDashboardStats.fromJson(Map<String, dynamic> json) {
    return RiderDashboardStats(
      totalEarnings: (json['total_earnings'] as num?)?.toDouble() ?? 0,
      earningsToday: (json['earnings_today'] as num?)?.toDouble() ?? 0,
      completedDeliveries: (json['completed_deliveries'] as num?)?.toInt() ?? 0,
      activeDeliveries: (json['active_deliveries'] as num?)?.toInt() ?? 0,
      riderFeeRate: (json['rider_service_fee_percentage'] as num?)?.toDouble() ?? 2.5,
    );
  }
}
