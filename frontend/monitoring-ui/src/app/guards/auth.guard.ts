import { inject } from '@angular/core';
import { Router, CanActivateFn } from '@angular/router';
import { map } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const authGuard: CanActivateFn = (route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  const token = authService.getToken();

  if (!token) {
    router.navigate(['/login'], {
      queryParams: { returnUrl: state.url },
      replaceUrl: true,
    });
    return false;
  }

  return true;
};

export const companyAdminGuard: CanActivateFn = (route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (!authService.getToken()) {
    return router.createUrlTree(['/login'], {
      queryParams: { returnUrl: state.url },
    });
  }

  return authService.ensureCurrentUser().pipe(
    map((session) => {
      const role = session?.profile?.role;
      if (role === 'company_admin' || role === 'superadmin') {
        return true;
      }
      return router.createUrlTree(['/']);
    })
  );
};
