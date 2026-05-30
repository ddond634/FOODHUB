import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../config/supabase_config.dart';
import '../providers/app_state.dart';
import '../widgets/product_card.dart';
import 'product_detail_screen.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final products = state.bestSellers;
    final shops = state.shops;

    return Scaffold(
      appBar: AppBar(
        title: const Text('FOODHUB'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () async {
              await Future.wait([
                state.refreshBestSellers(),
                state.refreshShops(),
              ]);
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          await Future.wait([
            state.refreshBestSellers(),
            state.refreshShops(),
          ]);
        },
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(
              'Active Stores',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            if (shops.isEmpty)
              Text('No active stores yet', style: TextStyle(color: Colors.grey.shade600))
            else
              SizedBox(
                height: 132,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: shops.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 12),
                  itemBuilder: (context, index) {
                    final shop = shops[index];
                    final logoUrl = SupabaseConfig.resolveImageUrl(shop.storeLogo);
                    return SizedBox(
                      width: 220,
                      child: Card(
                        child: Padding(
                          padding: const EdgeInsets.all(12),
                          child: Row(
                            children: [
                              CircleAvatar(
                                radius: 28,
                                backgroundColor: const Color(0xFF28A745).withValues(alpha: 0.12),
                                backgroundImage: logoUrl.isNotEmpty ? CachedNetworkImageProvider(logoUrl) : null,
                                child: logoUrl.isEmpty
                                    ? const Icon(Icons.storefront, color: Color(0xFF28A745))
                                    : null,
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Text(
                                      shop.displayName,
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(fontWeight: FontWeight.w700),
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      shop.fullAddress ?? 'FOODHUB seller',
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                      style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      '${shop.totalProducts} product${shop.totalProducts == 1 ? '' : 's'}',
                                      style: TextStyle(color: Colors.grey.shade700, fontSize: 12),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    );
                  },
                ),
              ),
            const SizedBox(height: 24),
            Text(
              'Best Sellers',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text('Popular picks from the same catalog as the website', style: TextStyle(color: Colors.grey.shade600)),
            const SizedBox(height: 16),
            if (products.isEmpty)
              const Padding(
                padding: EdgeInsets.only(top: 40),
                child: Center(child: Text('No featured products yet')),
              )
            else
              GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  childAspectRatio: 0.68,
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
