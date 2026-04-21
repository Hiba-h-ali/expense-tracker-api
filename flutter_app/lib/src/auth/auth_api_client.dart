import 'package:dio/dio.dart';

import 'models.dart';

class AuthApiClient {
  AuthApiClient(this._dio);

  final Dio _dio;

  Future<void> register(RegisterPayload payload) async {
    await _dio.post('/auth/register', data: payload.toJson());
  }

  Future<AuthTokens> login(LoginPayload payload) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/auth/login',
      data: payload.toJson(),
    );
    return AuthTokens.fromJson(response.data ?? const {});
  }

  Future<AuthTokens> refresh(String refreshToken) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/auth/refresh',
      data: {'refresh_token': refreshToken},
    );
    return AuthTokens.fromJson(response.data ?? const {});
  }

  Future<void> logout(String refreshToken) async {
    await _dio.post('/auth/logout', data: {'refresh_token': refreshToken});
  }

  Future<AuthUser> me(String accessToken) async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/auth/me',
      options: Options(
        headers: {'Authorization': 'Bearer $accessToken'},
      ),
    );
    return AuthUser.fromJson(response.data ?? const {});
  }
}
