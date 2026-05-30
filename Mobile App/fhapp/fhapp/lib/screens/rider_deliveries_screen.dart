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
        body: TabBarView(
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
                  Text('Your fee: ₱${order.riderEarnings.toStringAsFixed(2)}'),
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
