import '../config/supabase_config.dart';
import '../models/seller.dart';
import 'api_client.dart';

class SellerService {
  SellerService(this._client);

  final ApiClient _client;

  Future<List<SellerShop>> fetchActiveShops() async {
    final data = await _client.getJson('${SupabaseConfig.productApi}/sellers/active');
    if (data['success'] != true) {
      throw Exception(data['error']?.toString() ?? 'Failed to load shops');
    }

    final list = data['data'] as List<dynamic>? ?? [];
    return list.map((e) => SellerShop.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<SellerProfile> fetchSellerProfile(int sellerId) async {
    final data = await _client.getJson('${SupabaseConfig.productApi}/sellers/$sellerId');
    if (data['success'] != true || data['data'] == null) {
      throw Exception(data['error']?.toString() ?? 'Seller not found');
    }
    return SellerProfile.fromJson(data['data'] as Map<String, dynamic>);
  }
}
