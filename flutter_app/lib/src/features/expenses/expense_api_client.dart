import 'package:dio/dio.dart';

class ExpenseApiClient {
  ExpenseApiClient(this._dio);

  final Dio _dio;

  Future<List<Map<String, dynamic>>> listExpenses() async {
    final response = await _dio.get<List<dynamic>>('/expenses');
    final data = response.data ?? const [];
    return data.cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> addExpense({
    required double amount,
    required DateTime date,
    int? categoryId,
    String? description,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/expenses',
      data: {
        'amount': amount,
        'date': date.toUtc().toIso8601String(),
        'category_id': categoryId,
        'description': description,
      },
    );
    return response.data ?? const {};
  }
}
