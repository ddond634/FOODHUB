import '../config/supabase_config.dart';
import '../models/cart_item.dart';
import 'api_client.dart';

class CartService {
  CartService(this._client);

  final ApiClient _client;

  Future<List<CartItem>> fetchCart() async {
    final data = await _client.getJson('${SupabaseConfig.commerceApi}/cart', authenticated: true);
    if (data['success'] != true) {
      throw Exception(data['error']?.toString() ?? 'Failed to load cart');
    }
    final inner = data['data'] as Map<String, dynamic>?;
    final list = inner?['items'] as List<dynamic>? ?? [];
    return list.map((e) => CartItem.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> addToCart(int productId, {int quantity = 1}) async {
    final data = await _client.postJson(
      '${SupabaseConfig.commerceApi}/cart',
      {
        'product_id': productId,
        'quantity': quantity,
        'variation_id': null,
      },
      authenticated: true,
    );
    if (data['success'] != true) {
      throw Exception(data['error']?.toString() ?? 'Failed to add to cart');
    }
  }

  Future<void> updateQuantity(int cartId, int quantity) async {
    final data = await _client.putJson(
      '${SupabaseConfig.commerceApi}/cart/$cartId',
      {'quantity': quantity},
    );
    if (data['success'] != true) {
      throw Exception(data['error']?.toString() ?? 'Failed to update cart');
    }
  }

  Future<void> removeItem(int cartId) async {
    final data = await _client.deleteJson('${SupabaseConfig.commerceApi}/cart/$cartId');
    if (data['success'] != true) {
      throw Exception(data['error']?.toString() ?? 'Failed to remove item');
    }
  }
}
