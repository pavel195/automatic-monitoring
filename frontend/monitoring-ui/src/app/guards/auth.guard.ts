import { inject } from '@angular/core';
import { Router, CanActivateFn } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const authGuard: CanActivateFn = (route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  // Проверяем наличие токена
  const token = authService.getToken();
  
  if (!token) {
    console.log('Guard: токен не найден, редирект на /login');
    router.navigate(['/login'], { 
      queryParams: { returnUrl: state.url },
      replaceUrl: true 
    });
    return false;
  }

  // Если токен есть, разрешаем доступ
  // Если токен невалидный, API вернет ошибку и пользователь будет перенаправлен
  return true;
};

