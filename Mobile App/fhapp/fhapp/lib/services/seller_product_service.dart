import '../config/supabase_config.dart';
import '../models/product.dart';
import 'api_client.dart';

class SellerProductService {
  SellerProductService(this._client);

  final ApiClient _client;

  Future<List<Product>> fetchMyProducts() async {
    final data = await _client.getJson('${SupabaseConfig.sellerApi}/products');
    if (data['success'] != true) {
      throw Exception(data['error']?.toString() ?? 'Failed to load products');
    }
    final list = data['data'] as List<dynamic>? ?? [];
    return list.map((e) => Product.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> createProduct({
    required String title,
    required String description,
    required double price,
    required int stock,
    String category = 'General',
    String? imgUrl,
  }) async {
    final data = await _client.postJson('${SupabaseConfig.sellerApi}/products', {
      'title': title,
      'description': description,
      'price': price,
      'stock': stock,
      'category': category,
      if (imgUrl != null) 'img_url': imgUrl,
    });
    if (data['success'] != true) {
      throw Exception(data['error']?.toString() ?? 'Failed to create product');
    }
  }

  Future<void> updateProduct(int id, Map<String, dynamic> updates) async {
    final data = await _client.putJson('${SupabaseConfig.sellerApi}/products/$id', updates);
    if (data['success'] != true) {
      throw Exception(data['error']?.toString() ?? 'Failed to update product');
    }
  }

  Future<void> deleteProduct(int id) async {
    final data = await _client.deleteJson('${SupabaseConfig.sellerApi}/products/$id');
    if (data['success'] != true) {
      throw Exception(data['error']?.toString() ?? 'Failed to delete product');
    }
  }

  Future<void> restockProduct(int id, int stock) async {
    await updateProduct(id, {'stock': stock});
  }
}
