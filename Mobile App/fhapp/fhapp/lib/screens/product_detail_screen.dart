import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../config/supabase_config.dart';
import '../providers/app_state.dart';
import '../services/product_service.dart';
import '../models/product.dart';
import '../services/api_client.dart';

class ProductDetailScreen extends StatefulWidget {
  const ProductDetailScreen({super.key, required this.productId});

  final int productId;

  @override
  State<ProductDetailScreen> createState() => _ProductDetailScreenState();
}

class _ProductDetailScreenState extends State<ProductDetailScreen> {
  Product? _product;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final state = context.read<AppState>();
    final service = ProductService(ApiClient(hubToken: state.auth.token));
    try {
      final product = await service.fetchProduct(widget.productId);
      if (!mounted) return;
      setState(() {
        _product = product;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _addToCart() async {
    final state = context.read<AppState>();
    try {
      await state.addToCart(widget.productId);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Added to cart')),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(state.error ?? 'Could not add to cart')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return Scaffold(
        appBar: AppBar(),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    if (_error != null || _product == null) {
      return Scaffold(
        appBar: AppBar(),
        body: Center(child: Text(_error ?? 'Product not found')),
      );
    }

    final product = _product!;
    final imageUrl = SupabaseConfig.resolveImageUrl(product.imgUrl);

    return Scaffold(
      appBar: AppBar(title: Text(product.title)),
      body: ListView(
        children: [
          AspectRatio(
            aspectRatio: 1.2,
            child: imageUrl.isEmpty
                ? Container(color: Colors.grey.shade200)
                : CachedNetworkImage(imageUrl: imageUrl, fit: BoxFit.cover),
          ),
          Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (product.category != null)
                  Text(product.category!, style: TextStyle(color: Colors.grey.shade600)),
                const SizedBox(height: 8),
                Text(
                  product.title,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 12),
                Text(
                  '₱${product.price.toStringAsFixed(2)}',
                  style: const TextStyle(
                    color: Color(0xFF28A745),
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                Text('${product.stock} in stock'),
                const SizedBox(height: 16),
                Text(product.description.isEmpty ? 'No description available.' : product.description),
              ],
            ),
          ),
        ],
      ),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: ElevatedButton.icon(
            onPressed: context.watch<AppState>().busy ? null : _addToCart,
            icon: const Icon(Icons.add_shopping_cart),
            label: const Text('Add to Cart'),
          ),
        ),
      ),
    );
  }
}
