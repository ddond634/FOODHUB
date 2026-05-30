import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';

class RiderDashboardScreen extends StatefulWidget {
  const RiderDashboardScreen({super.key});

  @override
  State<RiderDashboardScreen> createState() => _RiderDashboardScreenState();
}

class _RiderDashboardScreenState extends State<RiderDashboardScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<AppState>().refreshRiderOrders();
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final dashboard = state.riderDashboard;
    final completed = state.assignedRiderOrders
        .where((o) => ['delivered', 'completed'].contains(o.status))
        .toList();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Rider Analytics'),
        actions: [
          IconButton(onPressed: state.refreshRiderOrders, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: state.refreshRiderOrders,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (dashboard == null)
              const Center(child: Padding(padding: EdgeInsets.all(32), child: CircularProgressIndicator()))
            else ...[
              Text('Delivery earnings', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              Text(
                '${dashboard.riderFeeRate.toStringAsFixed(1)}% of product sales per delivery',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 12),
              GridView.count(
                crossAxisCount: 2,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                mainAxisSpacing: 12,
                crossAxisSpacing: 12,
                childAspectRatio: 1.5,
                children: [
                  _metricCard(context, 'Total earned', '₱${dashboard.totalEarnings.toStringAsFixed(2)}', Icons.payments),
                  _metricCard(context, 'Today', '₱${dashboard.earningsToday.toStringAsFixed(2)}', Icons.today),
                  _metricCard(context, 'Completed', '${dashboard.completedDeliveries}', Icons.check_circle_outline),
                  _metricCard(context, 'Active now', '${dashboard.activeDeliveries}', Icons.delivery_dining),
                ],
              ),
            ],
            const SizedBox(height: 24),
            Text('Earnings per delivery', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            if (completed.isEmpty)
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Center(child: Text('Complete deliveries to see earnings here')),
                ),
              )
            else
              ...completed.map((order) => Card(
                    child: ListTile(
                      leading: const CircleAvatar(child: Icon(Icons.local_shipping, size: 20)),
                      title: Text('Order #${order.id}'),
                      subtitle: Text(
                        'Product sales: ₱${order.productSubtotal.toStringAsFixed(2)} · ${order.status}',
                      ),
                      trailing: Text(
                        '₱${order.riderEarnings.toStringAsFixed(2)}',
                        style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.green),
                      ),
                    ),
                  )),
          ],
        ),
      ),
    );
  }

  Widget _metricCard(BuildContext context, String label, String value, IconData icon) {
    return Card(
      color: Theme.of(context).colorScheme.primaryContainer,
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 22),
            const Spacer(),
            Text(label, style: const TextStyle(fontSize: 12)),
            Text(value, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          ],
        ),
      ),
    );
  }
}
