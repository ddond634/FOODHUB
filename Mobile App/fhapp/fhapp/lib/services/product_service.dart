import '../config/supabase_config.dart';
import '../models/product.dart';
import 'api_client.dart';

class ProductService {
  ProductService(this._client);

  final ApiClient _client;

  Future<List<Product>> fetchProducts({String? category, String? query}) async {
    final params = <String, String>{};
    if (category != null && category.isNotEmpty) params['category'] = category;
    if (query != null && query.isNotEmpty) params['q'] = query;

    final uri = Uri.parse('${SupabaseConfig.productApi}/products')
        .replace(queryParameters: params.isEmpty ? null : params);

    final data = await _client.getJson(uri.toString());
    if (data['success'] != true) {
      throw Exception(data['error']?.toString() ?? 'Failed to load products');
    }

    final list = data['data'] as List<dynamic>? ?? [];
    return list.map((e) => Product.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<List<Product>> fetchBestSellers({int limit = 12}) async {
    final uri = Uri.parse('${SupabaseConfig.productApi}/products/best-sellers')
        .replace(queryParameters: {'limit': '$limit'});

    final data = await _client.getJson(uri.toString());
    if (data['success'] != true) {
      throw Exception(data['error']?.toString() ?? 'Failed to load best sellers');
    }

    final inner = data['data'] as Map<String, dynamic>?;
    final list = inner?['products'] as List<dynamic>? ?? [];
    return list.map((e) => Product.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<Product> fetchProduct(int id) async {
    final data = await _client.getJson('${SupabaseConfig.productApi}/products/$id');
    if (data['success'] != true || data['data'] == null) {
      throw Exception(data['error']?.toString() ?? 'Product not found');
    }
    return Product.fromJson(data['data'] as Map<String, dynamic>);
  }

  Future<List<String>> fetchCategories() async {
    final products = await fetchProducts();
    return products
        .map((p) => p.category)
        .whereType<String>()
        .where((c) => c.isNotEmpty)
        .toSet()
        .toList()
      ..sort();
  }
}
