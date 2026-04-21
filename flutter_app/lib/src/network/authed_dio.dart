import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../auth/auth_repository.dart';

class AuthRefreshInterceptor extends Interceptor {
  AuthRefreshInterceptor(this._ref);

  final Ref _ref;

  @override
  void onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) {
    final token = _ref.read(authRepositoryProvider).tokens?.accessToken;
    if (token != null && token.isNotEmpty) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    final isUnauthorized = err.response?.statusCode == 401;
    final alreadyRetried = err.requestOptions.extra['retried'] == true;

    if (!isUnauthorized || alreadyRetried) {
      handler.next(err);
      return;
    }

    final refreshed = await _ref.read(authRepositoryProvider.notifier).refreshSession();
    if (!refreshed) {
      handler.next(err);
      return;
    }

    final retryDio = Dio(
      BaseOptions(
        baseUrl: apiBaseUrl,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 10),
      ),
    );
    final token = _ref.read(authRepositoryProvider).tokens?.accessToken;
    if (token != null) {
      err.requestOptions.headers['Authorization'] = 'Bearer $token';
    }
    err.requestOptions.extra['retried'] = true;

    final response = await retryDio.fetch(err.requestOptions);
    handler.resolve(response);
  }
}

final authedDioProvider = Provider<Dio>((ref) {
  final dio = Dio(
    BaseOptions(
      baseUrl: apiBaseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
    ),
  );
  dio.interceptors.add(AuthRefreshInterceptor(ref));
  return dio;
});
