/// Shared Supabase configuration — matches the FOODHUB website.
class SupabaseConfig {
  static const projectRef = 'sfeccfbdmbwoblixyoti';
  static const url = 'https://sfeccfbdmbwoblixyoti.supabase.co';
  static const anonKey =
      'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNmZWNjZmJkbWJ3b2JsaXh5b3RpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwODAwNTksImV4cCI6MjA5NTY1NjA1OX0.uM7DX7T-PQqPsMIwh-Fna1BUtVkkOhR4PiT2YqYlhIE';

  static const functionsBase =
      'https://sfeccfbdmbwoblixyoti.functions.supabase.co';
  static const authApi = '$functionsBase/auth_api';
  static const productApi = '$functionsBase/product_api';
  static const commerceApi = '$functionsBase/commerce_api';
  static const storageBase =
      '$url/storage/v1/object/public/hub_uploads';

  static String resolveImageUrl(String? path) {
    if (path == null || path.isEmpty) return '';
    if (path.startsWith('http://') || path.startsWith('https://')) return path;
    final normalized = path.replaceFirst(RegExp(r'^/+'), '').replaceFirst(RegExp(r'^uploads/'), '');
    return '$storageBase/$normalized';
  }
}
