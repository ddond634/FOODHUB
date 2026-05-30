import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../config/supabase_config.dart';
import '../providers/app_state.dart';
import '../widgets/checkout_form_dialog.dart';

class CartScreen extends StatefulWidget {
  const CartScreen({super.key});

  @override
  State<CartScreen> createState() => _CartScreenState();
}

class _CartScreenState extends State<CartScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<AppState>().refreshCart();
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final items = state.cartItems;
    final deliveryFee = items.isEmpty ? 0.0 : 50.0;
    final total = state.cartTotal + deliveryFee;

    return Scaffold(
      appBar: AppBar(
        title: const Text('My Cart'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: state.busy ? null : state.refreshCart,
          ),
        ],
      ),
      body: state.busy && items.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : items.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.shopping_cart_outlined, size: 64, color: Colors.grey.shade400),
                      const SizedBox(height: 12),
                      const Text('Your cart is empty'),
                    ],
                  ),
                )
              : Column(
                  children: [
                    Expanded(
                      child: ListView.separated(
                        padding: const EdgeInsets.all(16),
                        itemCount: items.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 12),
                        itemBuilder: (context, index) {
                          final item = items[index];
                          final imageUrl = SupabaseConfig.resolveImageUrl(item.imgUrl);
                          return Card(
                            child: Padding(
                              padding: const EdgeInsets.all(12),
                              child: Row(
                                children: [
                                  ClipRRect(
                                    borderRadius: BorderRadius.circular(8),
                                    child: SizedBox(
                                      width: 72,
                                      height: 72,
                                      child: imageUrl.isEmpty
                                          ? Container(color: Colors.grey.shade200)
                                          : CachedNetworkImage(imageUrl: imageUrl, fit: BoxFit.cover),
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(item.title, maxLines: 2, overflow: TextOverflow.ellipsis),
                                        const SizedBox(height: 4),
                                        Text('₱${item.unitPrice.toStringAsFixed(2)}'),
                                        Row(
                                          children: [
                                            IconButton(
                                              onPressed: state.busy
                                                  ? null
                                                  : () => state.updateCartQuantity(item.cartId, item.quantity - 1),
                                              icon: const Icon(Icons.remove_circle_outline),
                                            ),
                                            Text('${item.quantity}'),
                                            IconButton(
                                              onPressed: state.busy
                                                  ? null
                                                  : () => state.updateCartQuantity(item.cartId, item.quantity + 1),
                                              icon: const Icon(Icons.add_circle_outline),
                                            ),
                                            const Spacer(),
                                            IconButton(
                                              onPressed: state.busy ? null : () => state.removeFromCart(item.cartId),
                                              icon: const Icon(Icons.delete_outline, color: Colors.red),
                                            ),
                                          ],
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          );
                        },
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: 0.05),
                            blurRadius: 8,
                            offset: const Offset(0, -2),
                          ),
                        ],
                      ),
                      child: Column(
                        children: [
                          _summaryRow('Subtotal', state.cartTotal),
                          _summaryRow('Delivery', deliveryFee),
                          const Divider(),
                          _summaryRow('Total', total, bold: true),
                          const SizedBox(height: 12),
                          ElevatedButton(
                            onPressed: state.busy
                                ? null
                                : () async {
                                    final user = state.user;
                                    final buyerInfo = await showCheckoutFormDialog(
                                      context,
                                      defaultFirstName: user?.firstName,
                                      defaultLastName: user?.lastName,
                                      defaultEmail: user?.email,
                                    );
                                    if (buyerInfo == null || !context.mounted) return;

                                    final payment = await showDialog<String>(
                                      context: context,
                                      builder: (ctx) => SimpleDialog(
                                        title: const Text('Payment method'),
                                        children: [
                                          SimpleDialogOption(
                                            onPressed: () => Navigator.pop(ctx, 'Cash on Delivery'),
                                            child: const Text('Cash on Delivery'),
                                          ),
                                          SimpleDialogOption(
                                            onPressed: () => Navigator.pop(ctx, 'GCash'),
                                            child: const Text('GCash (demo)'),
                                          ),
                                        ],
                                      ),
                                    );
                                    if (payment == null || !context.mounted) return;
                                    try {
                                      final orderId = await state.checkout(
                                        payment: payment,
                                        buyerInfo: buyerInfo,
                                      );
                                      if (!context.mounted) return;
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        SnackBar(content: Text('Order #$orderId placed — rider can pick it up')),
                                      );
                                    } catch (e) {
                                      if (!context.mounted) return;
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        SnackBar(content: Text(state.error ?? 'Checkout failed')),
                                      );
                                    }
                                  },
                            child: const Text('Proceed to Checkout'),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
    );
  }

  Widget _summaryRow(String label, double amount, {bool bold = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Text(label, style: TextStyle(fontWeight: bold ? FontWeight.bold : FontWeight.normal)),
          const Spacer(),
          Text(
            '₱${amount.toStringAsFixed(2)}',
            style: TextStyle(fontWeight: bold ? FontWeight.bold : FontWeight.normal),
          ),
        ],
      ),
    );
  }
}
