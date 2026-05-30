import 'package:flutter/material.dart';

class CheckoutFormData {
  final String firstName;
  final String lastName;
  final String phone;
  final String email;
  final String addressLine1;
  final String addressLine2;
  final String city;
  final String province;
  final String region;
  final String? notes;

  const CheckoutFormData({
    required this.firstName,
    required this.lastName,
    required this.phone,
    required this.email,
    required this.addressLine1,
    this.addressLine2 = '',
    required this.city,
    required this.province,
    this.region = 'NCR',
    this.notes,
  });

  Map<String, dynamic> toCustomerPayload() {
    final addressParts = [
      addressLine1,
      if (addressLine2.isNotEmpty) addressLine2,
      city,
      province,
    ].where((p) => p.isNotEmpty);
    return {
      'first_name': firstName,
      'last_name': lastName,
      'email': email,
      'phone': phone,
      'address': addressParts.join(', '),
      'address_line1': addressLine1,
      'address_line2': addressLine2,
      'city': city,
      'province': province,
      'region': region,
      if (notes != null && notes!.isNotEmpty) 'notes': notes,
    };
  }
}

Future<CheckoutFormData?> showCheckoutFormDialog(
  BuildContext context, {
  String? defaultFirstName,
  String? defaultLastName,
  String? defaultEmail,
  String? defaultPhone,
}) {
  return showDialog<CheckoutFormData>(
    context: context,
    barrierDismissible: false,
    builder: (ctx) => _CheckoutFormDialog(
      defaultFirstName: defaultFirstName,
      defaultLastName: defaultLastName,
      defaultEmail: defaultEmail,
      defaultPhone: defaultPhone,
    ),
  );
}

class _CheckoutFormDialog extends StatefulWidget {
  const _CheckoutFormDialog({
    this.defaultFirstName,
    this.defaultLastName,
    this.defaultEmail,
    this.defaultPhone,
  });

  final String? defaultFirstName;
  final String? defaultLastName;
  final String? defaultEmail;
  final String? defaultPhone;

  @override
  State<_CheckoutFormDialog> createState() => _CheckoutFormDialogState();
}

class _CheckoutFormDialogState extends State<_CheckoutFormDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _firstNameCtrl;
  late final TextEditingController _lastNameCtrl;
  late final TextEditingController _phoneCtrl;
  late final TextEditingController _emailCtrl;
  late final TextEditingController _address1Ctrl;
  late final TextEditingController _address2Ctrl;
  late final TextEditingController _cityCtrl;
  late final TextEditingController _provinceCtrl;
  late final TextEditingController _notesCtrl;

  @override
  void initState() {
    super.initState();
    _firstNameCtrl = TextEditingController(text: widget.defaultFirstName ?? '');
    _lastNameCtrl = TextEditingController(text: widget.defaultLastName ?? '');
    _phoneCtrl = TextEditingController(text: widget.defaultPhone ?? '');
    _emailCtrl = TextEditingController(text: widget.defaultEmail ?? '');
    _address1Ctrl = TextEditingController();
    _address2Ctrl = TextEditingController();
    _cityCtrl = TextEditingController(text: 'Taguig City');
    _provinceCtrl = TextEditingController(text: 'Metro Manila');
    _notesCtrl = TextEditingController();
  }

  @override
  void dispose() {
    _firstNameCtrl.dispose();
    _lastNameCtrl.dispose();
    _phoneCtrl.dispose();
    _emailCtrl.dispose();
    _address1Ctrl.dispose();
    _address2Ctrl.dispose();
    _cityCtrl.dispose();
    _provinceCtrl.dispose();
    _notesCtrl.dispose();
    super.dispose();
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    Navigator.pop(
      context,
      CheckoutFormData(
        firstName: _firstNameCtrl.text.trim(),
        lastName: _lastNameCtrl.text.trim(),
        phone: _phoneCtrl.text.trim(),
        email: _emailCtrl.text.trim(),
        addressLine1: _address1Ctrl.text.trim(),
        addressLine2: _address2Ctrl.text.trim(),
        city: _cityCtrl.text.trim(),
        province: _provinceCtrl.text.trim(),
        notes: _notesCtrl.text.trim().isEmpty ? null : _notesCtrl.text.trim(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Delivery Information'),
      content: SizedBox(
        width: double.maxFinite,
        child: SingleChildScrollView(
          child: Form(
            key: _formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextFormField(
                  controller: _firstNameCtrl,
                  decoration: const InputDecoration(labelText: 'First Name *'),
                  validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
                ),
                TextFormField(
                  controller: _lastNameCtrl,
                  decoration: const InputDecoration(labelText: 'Last Name *'),
                  validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
                ),
                TextFormField(
                  controller: _phoneCtrl,
                  decoration: const InputDecoration(labelText: 'Phone *'),
                  keyboardType: TextInputType.phone,
                  validator: (v) => (v == null || v.trim().length < 7) ? 'Enter a valid phone' : null,
                ),
                TextFormField(
                  controller: _emailCtrl,
                  decoration: const InputDecoration(labelText: 'Email *'),
                  keyboardType: TextInputType.emailAddress,
                  validator: (v) => (v == null || !v.contains('@')) ? 'Enter a valid email' : null,
                ),
                TextFormField(
                  controller: _address1Ctrl,
                  decoration: const InputDecoration(labelText: 'Street / Building *'),
                  validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
                ),
                TextFormField(
                  controller: _address2Ctrl,
                  decoration: const InputDecoration(labelText: 'Barangay (optional)'),
                ),
                TextFormField(
                  controller: _cityCtrl,
                  decoration: const InputDecoration(labelText: 'City *'),
                  validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
                ),
                TextFormField(
                  controller: _provinceCtrl,
                  decoration: const InputDecoration(labelText: 'Province *'),
                  validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
                ),
                TextFormField(
                  controller: _notesCtrl,
                  decoration: const InputDecoration(labelText: 'Delivery notes (optional)'),
                  maxLines: 2,
                ),
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
        ElevatedButton(onPressed: _submit, child: const Text('Continue')),
      ],
    );
  }
}
