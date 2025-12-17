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
      // Если получили 401 или 403, очищаем авторизацию и редиректим на логин
      if (error.status === 401 || error.status === 403) {
        authService.clearAuth();
        router.navigate(['/login'], { replaceUrl: true });
      }
      return throwError(() => error);
    })
  );
};

