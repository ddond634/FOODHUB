import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/product.dart';
import '../providers/app_state.dart';

class SellerInventoryScreen extends StatefulWidget {
  const SellerInventoryScreen({super.key});

  @override
  State<SellerInventoryScreen> createState() => _SellerInventoryScreenState();
}

class _SellerInventoryScreenState extends State<SellerInventoryScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final state = context.read<AppState>();
      state.refreshSellerProducts();
      state.refreshSellerEarnings();
    });
  }

  Future<void> _showProductDialog({Product? product}) async {
    final titleCtrl = TextEditingController(text: product?.title ?? '');
    final descCtrl = TextEditingController(text: product?.description ?? '');
    final priceCtrl = TextEditingController(text: product?.price.toString() ?? '');
    final stockCtrl = TextEditingController(text: product?.stock.toString() ?? '0');
    final categoryCtrl = TextEditingController(text: product?.category ?? 'General');

    final saved = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(product == null ? 'Add Product' : 'Edit Product'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(controller: titleCtrl, decoration: const InputDecoration(labelText: 'Title')),
              TextField(controller: descCtrl, decoration: const InputDecoration(labelText: 'Description')),
              TextField(controller: priceCtrl, decoration: const InputDecoration(labelText: 'Price'), keyboardType: TextInputType.number),
              TextField(controller: stockCtrl, decoration: const InputDecoration(labelText: 'Stock'), keyboardType: TextInputType.number),
              TextField(controller: categoryCtrl, decoration: const InputDecoration(labelText: 'Category')),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          ElevatedButton(onPressed: () => Navigator.pop(context, true), child: const Text('Save')),
        ],
      ),
    );

    if (saved != true || !mounted) return;
    final state = context.read<AppState>();
    try {
      if (product == null) {
        await state.createSellerProduct(
          title: titleCtrl.text.trim(),
          description: descCtrl.text.trim(),
          price: double.tryParse(priceCtrl.text) ?? 0,
          stock: int.tryParse(stockCtrl.text) ?? 0,
          category: categoryCtrl.text.trim(),
        );
      } else {
        await state.updateSellerProduct(product.id, {
          'title': titleCtrl.text.trim(),
          'description': descCtrl.text.trim(),
          'price': double.tryParse(priceCtrl.text) ?? product.price,
          'stock': int.tryParse(stockCtrl.text) ?? product.stock,
          'category': categoryCtrl.text.trim(),
        });
      }
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Product saved')));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final products = state.sellerProducts;
    final dashboard = state.sellerDashboard;
    final earnings = state.sellerEarnings;

    return Scaffold(
      appBar: AppBar(
        title: const Text('My Products'),
        actions: [
          IconButton(
            onPressed: () async {
              await state.refreshSellerProducts();
              await state.refreshSellerEarnings();
            },
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showProductDialog(),
        child: const Icon(Icons.add),
      ),
      body: Column(
        children: [
          if (dashboard != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
              child: Card(
                color: Theme.of(context).colorScheme.primaryContainer,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Sales & Profit', style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Expanded(child: _statTile('Sales (Month)', '₱${dashboard.salesMonth.toStringAsFixed(2)}')),
                          Expanded(child: _statTile('Profit (Month)', '₱${dashboard.netProfitMonth.toStringAsFixed(2)}')),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Expanded(child: _statTile('Sales (Today)', '₱${dashboard.salesToday.toStringAsFixed(2)}')),
                          Expanded(child: _statTile('Orders', '${dashboard.totalOrders}')),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
          if (earnings != null && earnings.transactions.isNotEmpty)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Text('Profit per delivery', style: Theme.of(context).textTheme.titleSmall),
              ),
            ),
          if (earnings != null && earnings.transactions.isNotEmpty)
            SizedBox(
              height: 120,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.all(16),
                itemCount: earnings.transactions.take(10).length,
                separatorBuilder: (_, __) => const SizedBox(width: 12),
                itemBuilder: (context, index) {
                  final txn = earnings.transactions[index];
                  return SizedBox(
                    width: 180,
                    child: Card(
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('Order #${txn.orderId}', style: const TextStyle(fontWeight: FontWeight.bold)),
                            Text('Sales: ₱${txn.grossSales.toStringAsFixed(2)}', style: const TextStyle(fontSize: 12)),
                            Text('Profit: ₱${txn.netProfit.toStringAsFixed(2)}', style: const TextStyle(fontSize: 12, color: Colors.green)),
                          ],
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),
          Expanded(
            child: products.isEmpty
                ? const Center(child: Text('No products yet. Tap + to add one.'))
                : ListView.separated(
                    padding: const EdgeInsets.all(16),
                    itemCount: products.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 12),
                    itemBuilder: (context, index) {
                      final product = products[index];
                      return Card(
                        child: ListTile(
                          title: Text(product.title),
                          subtitle: Text('₱${product.price.toStringAsFixed(2)} · ${product.stock} in stock'),
                          trailing: PopupMenuButton<String>(
                            onSelected: (value) async {
                              if (value == 'edit') {
                                await _showProductDialog(product: product);
                              } else if (value == 'restock') {
                                final ctrl = TextEditingController(text: '${product.stock}');
                                final ok = await showDialog<bool>(
                                  context: context,
                                  builder: (ctx) => AlertDialog(
                                    title: const Text('Restock'),
                                    content: TextField(controller: ctrl, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'New stock')),
                                    actions: [
                                      TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
                                      ElevatedButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Save')),
                                    ],
                                  ),
                                );
                                if (ok == true) {
                                  await state.restockSellerProduct(product.id, int.tryParse(ctrl.text) ?? product.stock);
                                }
                              } else if (value == 'delete') {
                                await state.deleteSellerProduct(product.id);
                              }
                            },
                            itemBuilder: (_) => const [
                              PopupMenuItem(value: 'edit', child: Text('Edit')),
                              PopupMenuItem(value: 'restock', child: Text('Restock')),
                              PopupMenuItem(value: 'delete', child: Text('Delete')),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }

  Widget _statTile(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontSize: 12, color: Colors.black54)),
        Text(value, style: const TextStyle(fontWeight: FontWeight.bold)),
      ],
    );
  }
}
