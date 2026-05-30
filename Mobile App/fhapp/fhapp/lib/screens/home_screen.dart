import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../widgets/product_card.dart';
import 'product_detail_screen.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final products = state.bestSellers;

    return Scaffold(
      appBar: AppBar(
        title: const Text('FOODHUB'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => state.refreshBestSellers(),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => state.refreshBestSellers(),
        child: products.isEmpty
            ? ListView(
                children: const [
                  SizedBox(height: 120),
                  Center(child: Text('No featured products yet')),
                ],
              )
            : ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  Text(
                    'Best Sellers',
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  Text('Popular picks from the same catalog as the website', style: TextStyle(color: Colors.grey.shade600)),
                  const SizedBox(height: 16),
                  GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 2,
                      childAspectRatio: 0.72,
                      crossAxisSpacing: 12,
                      mainAxisSpacing: 12,
                    ),
                    itemCount: products.length,
                    itemBuilder: (context, index) {
                      final product = products[index];
                      return ProductCard(
                        product: product,
                        compact: true,
                        onTap: () => Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => ProductDetailScreen(productId: product.id),
                          ),
                        ),
                        onAddToCart: () => _addToCart(context, product.id),
                      );
                    },
                  ),
                ],
              ),
      ),
    );
  }

  Future<void> _addToCart(BuildContext context, int productId) async {
    final state = context.read<AppState>();
    try {
      await state.addToCart(productId);
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Added to cart')),
      );
    } catch (_) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(state.error ?? 'Could not add to cart')),
      );
    }
  }
}
