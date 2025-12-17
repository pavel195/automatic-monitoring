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

  constructor(
    private readonly authService: AuthService,
    private readonly router: Router
  ) {
    this.isAuthenticated$ = this.authService.currentUser$.pipe(
      map(user => !!user)
    );
    this.currentUser$ = this.authService.currentUser$;
    this.currentProfile$ = this.authService.currentProfile$;
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
      
      // Если нет токена и не на странице логина/регистрации - редирект
      if (!token && currentUrl !== '/login' && currentUrl !== '/register') {
        console.log('[AppComponent] Нет токена, редирект на /login');
        this.router.navigate(['/login'], { replaceUrl: true });
      }
    }, 50);
  }

  private checkAuthOnNavigation(): void {
    const token = this.authService.getToken();
    const currentUrl = this.router.url;
    
    // Если нет токена и не на публичных страницах - редирект
    if (!token && currentUrl !== '/login' && currentUrl !== '/register') {
      console.log('[AppComponent] Нет токена при навигации, редирект на /login');
      this.router.navigate(['/login'], { replaceUrl: true });
    }
  }

  logout(): void {
    this.authService.logout();
  }
}

