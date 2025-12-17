import { Component, OnInit } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatDividerModule } from '@angular/material/divider';
import { NgIf, AsyncPipe } from '@angular/common';
import { AuthService } from './services/auth.service';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatToolbarModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    MatDividerModule,
    NgIf,
    AsyncPipe,
  ],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
})
export class AppComponent implements OnInit {
  title = 'Центр мониторинга';
  isAuthenticated$: Observable<boolean>;
  currentUser$: Observable<any>;
  currentProfile$: Observable<any>;
  isCompanyAdmin$: Observable<boolean>;

  constructor(
    private readonly authService: AuthService,
    private readonly router: Router
  ) {
    // Проверяем авторизацию по токену и загруженному пользователю
    this.isAuthenticated$ = this.authService.currentUser$.pipe(
      map(user => {
        // Если пользователь загружен - авторизован
        if (user) {
          return true;
        }
        // Если пользователь не загружен, но токен есть - считаем авторизованным
        // (пользователь загрузится асинхронно)
        return this.authService.isAuthenticated();
      })
    );
    this.currentUser$ = this.authService.currentUser$;
    this.currentProfile$ = this.authService.currentProfile$;
    this.isCompanyAdmin$ = this.authService.currentProfile$.pipe(
      map(profile => profile ? (this.authService.isCompanyAdmin() || this.authService.isSuperAdmin()) : false)
    );
  }

  ngOnInit(): void {
    // Проверяем авторизацию при загрузке
    this.checkAuthOnInit();
    
    // Подписываемся на изменения роутера
    this.router.events
      .pipe(filter(event => event instanceof NavigationEnd))
      .subscribe(() => {
        this.checkAuthOnNavigation();
      });
  }

  private checkAuthOnInit(): void {
    // Небольшая задержка для инициализации роутера
    setTimeout(() => {
      const token = this.authService.getToken();
      const currentUrl = this.router.url;
      const isPublicPage = currentUrl === '/login' || currentUrl === '/register';
      
      // Если нет токена и не на публичной странице - редирект
      if (!token && !isPublicPage) {
        console.log('[AppComponent] Нет токена, редирект на /login');
        this.router.navigate(['/login'], { 
          queryParams: { returnUrl: currentUrl },
          replaceUrl: false 
        });
      } else if (token && !this.authService.getCurrentUser()) {
        // Если токен есть, но пользователь не загружен - пытаемся загрузить
        // Это нормально, пользователь загрузится асинхронно через AuthService
        console.log('[AppComponent] Токен найден, ожидаем загрузку пользователя...');
      }
    }, 100);
  }

  private checkAuthOnNavigation(): void {
    const token = this.authService.getToken();
    const currentUrl = this.router.url;
    const isPublicPage = currentUrl === '/login' || currentUrl === '/register';
    
    // Если нет токена и не на публичной странице - редирект
    if (!token && !isPublicPage) {
      console.log('[AppComponent] Нет токена при навигации, редирект на /login');
      this.router.navigate(['/login'], { 
        queryParams: { returnUrl: currentUrl },
        replaceUrl: false 
      });
    }
  }

  logout(): void {
    this.authService.logout();
  }
}

