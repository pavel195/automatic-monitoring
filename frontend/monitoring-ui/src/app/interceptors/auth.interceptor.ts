import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  // Добавляем токен к запросам, если он есть
  const token = authService.getToken();
  if (token) {
    req = req.clone({
      setHeaders: {
        Authorization: `Token ${token}`,
      },
    });
  }

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      // Обрабатываем только 401 (Unauthorized) - это означает, что токен невалидный или истек
      // 403 (Forbidden) - это недостаточно прав, но токен валидный, поэтому не очищаем сессию
      if (error.status === 401) {
        // Проверяем, что это не запрос на логин или регистрацию
        const url = error.url || '';
        if (!url.includes('/auth/login') && !url.includes('/register')) {
          authService.clearAuth();
          router.navigate(['/login'], { queryParams: { returnUrl: router.url }, replaceUrl: false });
        }
      }
      return throwError(() => error);
    })
  );
};

