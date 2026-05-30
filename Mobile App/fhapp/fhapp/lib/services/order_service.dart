import '../config/supabase_config.dart';
import 'api_client.dart';

class OrderService {
  OrderService(this._client);

  final ApiClient _client;

  Future<int> checkout({
    required List<Map<String, dynamic>> items,
    required Map<String, dynamic> customer,
    required double delivery,
    required double subtotal,
    required double total,
    String payment = 'Cash on Delivery',
  }) async {
    final data = await _client.postJson('${SupabaseConfig.commerceApi}/orders', {
      'items': items,
      'customer': customer,
      'delivery': delivery,
      'subtotal': subtotal,
      'total': total,
      'payment': payment,
    });
    if (data['success'] != true) {
      throw Exception(data['error']?.toString() ?? 'Checkout failed');
    }
    final orderId = (data['order_id'] as num?)?.toInt();
    if (orderId == null) throw Exception('Order ID missing from response');
    return orderId;
  }
}
