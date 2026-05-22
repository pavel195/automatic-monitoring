import { Component, OnInit, OnDestroy } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDividerModule } from '@angular/material/divider';
import { NgIf, NgClass, AsyncPipe } from '@angular/common';
import { AuthService } from './services/auth.service';
import { Observable, Subscription } from 'rxjs';
import { map } from 'rxjs/operators';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatSidenavModule,
    MatListModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    MatDividerModule,
    NgIf,
    NgClass,
    AsyncPipe,
  ],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
})
export class AppComponent implements OnInit, OnDestroy {
  title = 'Центр мониторинга';
  isAuthenticated$: Observable<boolean>;
  currentUser$: Observable<any>;
  currentProfile$: Observable<any>;
  collapsed = false;
  private readonly publicRoutes = new Set(['/login', '/register']);
  private routerSub?: Subscription;

  constructor(
    private readonly authService: AuthService,
    private readonly router: Router
  ) {
    this.isAuthenticated$ = this.authService.currentUser$.pipe(
      map(user => {
        if (user) return true;
        return this.authService.isAuthenticated();
      })
    );
    this.currentUser$ = this.authService.currentUser$;
    this.currentProfile$ = this.authService.currentProfile$;
  }

  ngOnInit(): void {
    this.checkAuthOnInit();
    this.routerSub = this.router.events
      .pipe(filter(event => event instanceof NavigationEnd))
      .subscribe(() => {
        this.checkAuthOnNavigation();
      });
  }

  ngOnDestroy(): void {
    this.routerSub?.unsubscribe();
  }

  private checkAuthOnInit(): void {
    setTimeout(() => {
      const token = this.authService.getToken();
      const currentUrl = this.router.url;
      if (!token && !this.isPublicUrl(currentUrl)) {
        this.router.navigate(['/login'], {
          queryParams: { returnUrl: currentUrl },
          replaceUrl: false
        });
      }
    }, 100);
  }

  private checkAuthOnNavigation(): void {
    const token = this.authService.getToken();
    const currentUrl = this.router.url;
    if (!token && !this.isPublicUrl(currentUrl)) {
      this.router.navigate(['/login'], {
        queryParams: { returnUrl: currentUrl },
        replaceUrl: false
      });
    }
  }

  private isPublicUrl(url: string): boolean {
    return this.publicRoutes.has(url.split('?')[0]);
  }

  toggleSidebar(): void {
    this.collapsed = !this.collapsed;
  }

  getRoleName(role: string): string {
    const roles: Record<string, string> = {
      superadmin: 'Супер-администратор',
      company_admin: 'Администратор',
      operator: 'Оператор',
    };
    return roles[role] || 'Оператор';
  }

  logout(): void {
    this.authService.logout();
  }
}
