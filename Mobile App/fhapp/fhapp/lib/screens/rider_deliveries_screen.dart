import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/order.dart';
import '../providers/app_state.dart';

class RiderDeliveriesScreen extends StatefulWidget {
  const RiderDeliveriesScreen({super.key});

  @override
  State<RiderDeliveriesScreen> createState() => _RiderDeliveriesScreenState();
}

class _RiderDeliveriesScreenState extends State<RiderDeliveriesScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<AppState>().refreshRiderOrders();
    });
  }

  String _nextAction(HubOrder order) {
    switch (order.status) {
      case 'dispatched':
      case 'ready':
      case 'placed':
        return 'Pick up → On the way';
      case 'in-transit':
        return 'Mark delivered';
      default:
        return '';
    }
  }

  Future<void> _advanceOrder(HubOrder order) async {
    final state = context.read<AppState>();
    try {
      if (['dispatched', 'ready', 'placed'].contains(order.status)) {
        await state.updateRiderDelivery(order.id, 'in-transit');
      } else if (order.status == 'in-transit') {
        await state.updateRiderDelivery(order.id, 'delivered');
      }
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Status updated')));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final dashboard = state.riderDashboard;
    final completed = state.assignedRiderOrders
        .where((o) => ['delivered', 'completed'].contains(o.status))
        .toList();

    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Deliveries'),
          actions: [
            IconButton(onPressed: state.refreshRiderOrders, icon: const Icon(Icons.refresh)),
          ],
          bottom: const TabBar(tabs: [
            Tab(text: 'Available'),
            Tab(text: 'My Deliveries'),
          ]),
        ),
        body: Column(
          children: [
            if (dashboard != null)
              Padding(
                padding: const EdgeInsets.all(16),
                child: Card(
                  color: Theme.of(context).colorScheme.primaryContainer,
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Delivery Earnings (${dashboard.riderFeeRate.toStringAsFixed(1)}% of product sales)',
                            style: Theme.of(context).textTheme.titleSmall),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            Expanded(child: _earningsTile('Total Earned', '₱${dashboard.totalEarnings.toStringAsFixed(2)}')),
                            Expanded(child: _earningsTile('Today', '₱${dashboard.earningsToday.toStringAsFixed(2)}')),
                            Expanded(child: _earningsTile('Completed', '${dashboard.completedDeliveries}')),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            if (completed.isNotEmpty)
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: Text('Earnings per delivery', style: Theme.of(context).textTheme.titleSmall),
                ),
              ),
            if (completed.isNotEmpty)
              SizedBox(
                height: 100,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  itemCount: completed.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 12),
                  itemBuilder: (context, index) {
                    final order = completed[index];
                    return SizedBox(
                      width: 170,
                      child: Card(
                        child: Padding(
                          padding: const EdgeInsets.all(12),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('#${order.id}', style: const TextStyle(fontWeight: FontWeight.bold)),
                              Text('Sales: ₱${order.productSubtotal.toStringAsFixed(2)}', style: const TextStyle(fontSize: 12)),
                              Text('Fee: ₱${order.riderEarnings.toStringAsFixed(2)}', style: const TextStyle(fontSize: 12, color: Colors.green)),
                            ],
                          ),
                        ),
                      ),
                    );
                  },
                ),
              ),
            Expanded(
              child: TabBarView(
                children: [
                  _orderList(
                    state.availableRiderOrders,
                    showAccept: true,
                    onAccept: (order) => state.acceptRiderOrder(order.id),
                  ),
                  _orderList(
                    state.assignedRiderOrders,
                    showAccept: false,
                    onAdvance: _advanceOrder,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _earningsTile(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontSize: 12, color: Colors.black54)),
        Text(value, style: const TextStyle(fontWeight: FontWeight.bold)),
      ],
    );
  }

  Widget _orderList(
    List<HubOrder> orders, {
    required bool showAccept,
    Future<void> Function(HubOrder)? onAccept,
    Future<void> Function(HubOrder)? onAdvance,
  }) {
    if (orders.isEmpty) {
      return const Center(child: Text('No orders here'));
    }
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: orders.length,
      separatorBuilder: (_, __) => const SizedBox(height: 12),
      itemBuilder: (context, index) {
        final order = orders[index];
        final action = _nextAction(order);
        return Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Order #${order.id}', style: const TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 4),
                Text(order.customerName),
                Text(order.customerPhone),
                Text(order.customerAddress, maxLines: 2, overflow: TextOverflow.ellipsis),
                const SizedBox(height: 8),
                Text('Status: ${order.status}'),
                Text('Product sales: ₱${order.productSubtotal.toStringAsFixed(2)}'),
                if (order.riderEarnings > 0)
                  Text('Delivery fee: ₱${order.riderEarnings.toStringAsFixed(2)}'),
                Text('Order total: ₱${order.total.toStringAsFixed(2)} · ${order.payment}'),
                if (order.items != null) Text('Items: ${order.items}'),
                const SizedBox(height: 12),
                if (showAccept)
                  ElevatedButton(
                    onPressed: onAccept == null ? null : () => onAccept(order),
                    child: const Text('Accept / Pick up'),
                  )
                else if (action.isNotEmpty)
                  ElevatedButton(
                    onPressed: onAdvance == null ? null : () => onAdvance(order),
                    child: Text(action),
                  ),
              ],
            ),
          ),
        );
      },
    );
  }
}
