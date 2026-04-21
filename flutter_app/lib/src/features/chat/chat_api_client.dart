import 'package:dio/dio.dart';

class ChatApiClient {
  ChatApiClient(this._dio);

  final Dio _dio;

  Future<Map<String, dynamic>> chat({
    required String text,
    String? sessionId,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/chat',
      data: {
        'text': text,
        'session_id': sessionId,
      },
    );
    return response.data ?? const {};
  }
}
