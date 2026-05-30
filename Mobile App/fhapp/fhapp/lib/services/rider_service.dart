import '../config/supabase_config.dart';
import '../models/earnings.dart';
import '../models/order.dart';
import 'api_client.dart';

class RiderService {
  RiderService(this._client);

  final ApiClient _client;

  Future<RiderDashboardStats> fetchDashboard() async {
    final data = await _client.getJson('${SupabaseConfig.riderApi}/dashboard');
    if (data['success'] != true || data['dashboard'] == null) {
      throw Exception(data['error']?.toString() ?? 'Failed to load rider dashboard');
    }
    return RiderDashboardStats.fromJson(data['dashboard'] as Map<String, dynamic>);
  }

  Future<List<HubOrder>> fetchAvailableOrders() async {
    final data = await _client.getJson('${SupabaseConfig.riderApi}/available-orders');
    if (data['success'] != true) {
      throw Exception(data['error']?.toString() ?? 'Failed to load available orders');
    }
    final list = data['data'] as List<dynamic>? ?? [];
    return list.map((e) => HubOrder.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<List<HubOrder>> fetchMyOrders() async {
    final data = await _client.getJson('${SupabaseConfig.riderApi}/orders');
    if (data['success'] != true) {
      throw Exception(data['error']?.toString() ?? 'Failed to load assigned orders');
    }
    final list = data['orders'] as List<dynamic>? ?? [];
    return list.map((e) => HubOrder.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> acceptOrder(int orderId) async {
    final data = await _client.postJson('${SupabaseConfig.riderApi}/accept-order', {
      'order_id': orderId,
    });
    if (data['success'] != true) {
      throw Exception(data['error']?.toString() ?? 'Failed to accept order');
    }
  }

  Future<void> updateDeliveryStatus(int orderId, String status) async {
    final data = await _client.putJson(
      '${SupabaseConfig.riderApi}/orders/$orderId/delivery-update',
      {'status': status},
    );
    if (data['success'] != true) {
      throw Exception(data['error']?.toString() ?? 'Failed to update delivery status');
    }
  }
}
