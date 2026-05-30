class HubUser {
  final int id;
  final String email;
  final String role;
  final String? firstName;
  final String? lastName;

  const HubUser({
    required this.id,
    required this.email,
    required this.role,
    this.firstName,
    this.lastName,
  });

  factory HubUser.fromJson(Map<String, dynamic> json) {
    return HubUser(
      id: (json['id'] as num).toInt(),
      email: json['email']?.toString() ?? '',
      role: json['role']?.toString() ?? 'customer',
      firstName: json['first_name']?.toString(),
      lastName: json['last_name']?.toString(),
    );
  }

  String get displayName {
    final parts = [firstName, lastName].where((p) => p != null && p.isNotEmpty);
    if (parts.isNotEmpty) return parts.join(' ');
    return email.split('@').first;
  }
}
