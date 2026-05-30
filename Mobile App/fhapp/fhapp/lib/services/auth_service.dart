import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../config/supabase_config.dart';
import '../models/hub_user.dart';

class AuthService {
  static const _tokenKey = 'hub_access_token';
  static const _userKey = 'hub_user';

  HubUser? _user;
  String? _token;

  HubUser? get user => _user;
  String? get token => _token;
  bool get isLoggedIn => _token != null && _token!.isNotEmpty;

  Future<void> loadSession() async {
    final prefs = await SharedPreferences.getInstance();
    _token = prefs.getString(_tokenKey);
    final userJson = prefs.getString(_userKey);
    if (userJson != null) {
      _user = HubUser.fromJson(jsonDecode(userJson) as Map<String, dynamic>);
    }
  }

  Future<void> login(String email, String password) async {
    final response = await http.post(
      Uri.parse('${SupabaseConfig.authApi}/login'),
      headers: {
        'Authorization': 'Bearer ${SupabaseConfig.anonKey}',
        'apikey': SupabaseConfig.anonKey,
        'Content-Type': 'application/json',
      },
      body: jsonEncode({'email': email.trim(), 'password': password}),
    );

    Map<String, dynamic> data;
    try {
      data = jsonDecode(response.body) as Map<String, dynamic>;
    } catch (_) {
      throw Exception('Login failed (${response.statusCode}). Check your connection.');
    }

    if (response.statusCode >= 400 || data['success'] != true || data['token'] == null) {
      throw Exception(data['error']?.toString() ?? 'Invalid email or password');
    }

    _token = data['token'] as String;
    _user = HubUser.fromJson(data['user'] as Map<String, dynamic>);

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, _token!);
    await prefs.setString(_userKey, jsonEncode(data['user']));
  }

  Future<void> register({
    required String email,
    required String password,
    required String firstName,
    required String lastName,
  }) async {
    final response = await http.post(
      Uri.parse('${SupabaseConfig.authApi}/register'),
      headers: {
        'Authorization': 'Bearer ${SupabaseConfig.anonKey}',
        'apikey': SupabaseConfig.anonKey,
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'email': email.trim(),
        'password': password,
        'first_name': firstName.trim(),
        'last_name': lastName.trim(),
        'role': 'customer',
      }),
    );

    Map<String, dynamic> data;
    try {
      data = jsonDecode(response.body) as Map<String, dynamic>;
    } catch (_) {
      throw Exception('Registration failed (${response.statusCode}). Check your connection.');
    }

    if (response.statusCode >= 400 || data['success'] != true || data['token'] == null) {
      throw Exception(data['error']?.toString() ?? 'Registration failed');
    }

    _token = data['token'] as String;
    _user = HubUser.fromJson(data['user'] as Map<String, dynamic>);

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, _token!);
    await prefs.setString(_userKey, jsonEncode(data['user']));
  }

  Future<void> logout() async {
    _token = null;
    _user = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
    await prefs.remove(_userKey);
  }
}
