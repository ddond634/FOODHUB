import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import '../config/supabase_config.dart';
import '../models/product.dart';

class ProductCard extends StatelessWidget {
  const ProductCard({
    super.key,
    required this.product,
    this.onTap,
    this.onAddToCart,
    this.compact = false,
  });

  final Product product;
  final VoidCallback? onTap;
  final VoidCallback? onAddToCart;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final imageUrl = SupabaseConfig.resolveImageUrl(product.imgUrl);

    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            AspectRatio(
              aspectRatio: compact ? 1.1 : 1,
              child: imageUrl.isEmpty
                  ? Container(
                      color: Colors.grey.shade200,
                      child: const Icon(Icons.image_not_supported_outlined, size: 40),
                    )
                  : CachedNetworkImage(
                      imageUrl: imageUrl,
                      fit: BoxFit.cover,
                      placeholder: (_, __) => Container(color: Colors.grey.shade200),
                      errorWidget: (_, __, ___) => Container(
                        color: Colors.grey.shade200,
                        child: const Icon(Icons.broken_image_outlined),
                      ),
                    ),
            ),
            Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (product.category != null && product.category!.isNotEmpty)
                    Text(
                      product.category!,
                      style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
                    ),
                  Text(
                    product.title,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Text(
                        '₱${product.price.toStringAsFixed(2)}',
                        style: const TextStyle(
                          color: AppThemeColors.primary,
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
                      const Spacer(),
                      if (onAddToCart != null)
                        IconButton.filled(
                          onPressed: onAddToCart,
                          icon: const Icon(Icons.add_shopping_cart, size: 18),
                          style: IconButton.styleFrom(
                            backgroundColor: AppThemeColors.primary,
                            foregroundColor: Colors.white,
                            minimumSize: const Size(36, 36),
                          ),
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
  }
}

class AppThemeColors {
  static const primary = Color(0xFF28A745);
}
