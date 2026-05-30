import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';

class SellerDashboardScreen extends StatefulWidget {
  const SellerDashboardScreen({super.key});

  @override
  State<SellerDashboardScreen> createState() => _SellerDashboardScreenState();
}

class _SellerDashboardScreenState extends State<SellerDashboardScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<AppState>().refreshSellerEarnings();
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final dashboard = state.sellerDashboard;
    final earnings = state.sellerEarnings;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Seller Analytics'),
        actions: [
          IconButton(
            onPressed: state.refreshSellerEarnings,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: state.refreshSellerEarnings,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (dashboard == null)
              const Center(child: Padding(padding: EdgeInsets.all(32), child: CircularProgressIndicator()))
            else ...[
              Text('Overview', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 12),
              GridView.count(
                crossAxisCount: 2,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                mainAxisSpacing: 12,
                crossAxisSpacing: 12,
                childAspectRatio: 1.4,
                children: [
                  _metricCard(context, 'Sales (Month)', '₱${dashboard.salesMonth.toStringAsFixed(2)}', Icons.trending_up),
                  _metricCard(context, 'Profit (Month)', '₱${dashboard.netProfitMonth.toStringAsFixed(2)}', Icons.savings_outlined),
                  _metricCard(context, 'Sales (Today)', '₱${dashboard.salesToday.toStringAsFixed(2)}', Icons.today),
                  _metricCard(context, 'Total Orders', '${dashboard.totalOrders}', Icons.receipt_long),
                  _metricCard(context, 'Pending', '${dashboard.pendingOrders}', Icons.pending_actions),
                  _metricCard(context, 'Products', '${state.sellerProducts.length}', Icons.inventory_2),
                ],
              ),
            ],
            if (earnings != null) ...[
              const SizedBox(height: 24),
              Text('Commission breakdown', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    children: [
                      _breakdownRow('Gross sales', earnings.grossRevenue),
                      _breakdownRow('Platform fee (10%)', earnings.platformCommission, color: Colors.orange),
                      _breakdownRow('Rider fees (2.5%)', earnings.riderFees, color: Colors.blue),
                      const Divider(),
                      _breakdownRow('Net profit', earnings.netProfit, bold: true, color: Colors.green),
                    ],
                  ),
                ),
              ),
            ],
            if (earnings != null && earnings.transactions.isNotEmpty) ...[
              const SizedBox(height: 24),
              Text('Profit per delivery', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              ...earnings.transactions.take(20).map((txn) => Card(
                    child: ListTile(
                      leading: CircleAvatar(child: Text('#${txn.orderId}')),
                      title: Text('₱${txn.grossSales.toStringAsFixed(2)} sales'),
                      subtitle: Text('Fee: ₱${(txn.platformCommission + txn.riderFee).toStringAsFixed(2)} · ${txn.status}'),
                      trailing: Text(
                        '₱${txn.netProfit.toStringAsFixed(2)}',
                        style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.green),
                      ),
                    ),
                  )),
            ],
          ],
        ),
      ),
    );
  }

  Widget _metricCard(BuildContext context, String label, String value, IconData icon) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 22, color: Theme.of(context).colorScheme.primary),
            const Spacer(),
            Text(label, style: const TextStyle(fontSize: 12, color: Colors.black54)),
            Text(value, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
          ],
        ),
      ),
    );
  }

  Widget _breakdownRow(String label, double amount, {bool bold = false, Color? color}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Expanded(child: Text(label, style: TextStyle(fontWeight: bold ? FontWeight.bold : FontWeight.normal))),
          Text(
            '₱${amount.toStringAsFixed(2)}',
            style: TextStyle(fontWeight: bold ? FontWeight.bold : FontWeight.normal, color: color),
          ),
        ],
      ),
    );
  }
}
