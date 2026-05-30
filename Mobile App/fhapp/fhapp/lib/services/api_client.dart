import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/supabase_config.dart';

class ApiClient {
  ApiClient({this.hubToken});

  String? hubToken;

  Map<String, String> _gatewayHeaders({Map<String, String>? extra}) {
    final headers = <String, String>{
      'Authorization': 'Bearer ${SupabaseConfig.anonKey}',
      'apikey': SupabaseConfig.anonKey,
      'Content-Type': 'application/json',
      ...?extra,
    };
    if (hubToken != null && hubToken!.isNotEmpty) {
      headers['X-Hub-Token'] = hubToken!;
    }
    return headers;
  }

  Future<Map<String, dynamic>> getJson(
    String url, {
    bool authenticated = false,
  }) async {
    final response = await http.get(
      Uri.parse(url),
      headers: _gatewayHeaders(),
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> postJson(
    String url,
    Map<String, dynamic> body, {
    bool authenticated = false,
  }) async {
    final response = await http.post(
      Uri.parse(url),
      headers: _gatewayHeaders(),
      body: jsonEncode(body),
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> putJson(String url, Map<String, dynamic> body) async {
    final response = await http.put(
      Uri.parse(url),
      headers: _gatewayHeaders(),
      body: jsonEncode(body),
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> deleteJson(String url) async {
    final response = await http.delete(
      Uri.parse(url),
      headers: _gatewayHeaders(),
    );
    return _decode(response);
  }

  Map<String, dynamic> _decode(http.Response response) {
    final text = response.body;
    if (text.isEmpty) {
      return {'success': response.statusCode >= 200 && response.statusCode < 300};
    }
    final decoded = jsonDecode(text);
    if (decoded is Map<String, dynamic>) return decoded;
    return {'success': false, 'error': 'Unexpected response format'};
  }
}
