import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, BehaviorSubject, tap } from 'rxjs';
import { Router } from '@angular/router';
import { environment } from '../../environments/environment';

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
}

export interface UserProfile {
  id: number;
  user: number;
  company: number | null;
  company_name: string | null;
  role: 'operator' | 'company_admin' | 'superadmin';
  phone: string;
}

export interface AuthResponse {
  token: string;
  user: User;
  profile: UserProfile | null;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly base = environment.apiUrl;
  private readonly tokenKey = 'auth_token';
  private currentUserSubject = new BehaviorSubject<User | null>(null);
  private currentProfileSubject = new BehaviorSubject<UserProfile | null>(null);
  private tokenCheckInterval?: number;
  
  public currentUser$ = this.currentUserSubject.asObservable();
  public currentProfile$ = this.currentProfileSubject.asObservable();

  constructor(
    private readonly http: HttpClient,
    private readonly router: Router
  ) {
    // Восстанавливаем сессию при инициализации
    const token = this.getToken();
    if (token) {
      this.loadCurrentUser();
      // Запускаем периодическую проверку токена (каждые 5 минут)
      this.startTokenCheck();
    }
  }

  login(username: string, password: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.base}/companies/auth/login/`, {
      username,
      password,
    }).pipe(
      tap((response) => {
        this.setToken(response.token);
        this.currentUserSubject.next(response.user);
        this.currentProfileSubject.next(response.profile);
        // Запускаем периодическую проверку токена после успешного входа
        this.startTokenCheck();
      })
    );
  }

  logout(): void {
    const token = this.getToken();
    if (token) {
      const headers = new HttpHeaders().set('Authorization', `Token ${token}`);
      this.http.post(`${this.base}/companies/auth/logout/`, {}, { headers }).subscribe({
        error: () => {
          // Игнорируем ошибки при выходе
        },
      });
    }
    this.clearAuth();
    this.router.navigate(['/login']);
  }

  register(companyData: any): Observable<any> {
    return this.http.post(`${this.base}/companies/companies/register/`, companyData);
  }

  getToken(): string | null {
    return localStorage.getItem(this.tokenKey);
  }

  setToken(token: string): void {
    localStorage.setItem(this.tokenKey, token);
  }

  clearAuth(): void {
    console.log('[AuthService] Очистка авторизации');
    localStorage.removeItem(this.tokenKey);
    this.currentUserSubject.next(null);
    this.currentProfileSubject.next(null);
    this.stopTokenCheck();
  }

  private startTokenCheck(): void {
    // Останавливаем предыдущий интервал, если он был
    this.stopTokenCheck();
    
    // Проверяем токен каждые 5 минут
    this.tokenCheckInterval = window.setInterval(() => {
      const token = this.getToken();
      if (token && this.currentUserSubject.value) {
        // Токен есть и пользователь загружен - проверяем валидность
        this.verifyToken();
      } else if (token && !this.currentUserSubject.value) {
        // Токен есть, но пользователь не загружен - пытаемся загрузить
        this.loadCurrentUser();
      }
    }, 5 * 60 * 1000); // 5 минут
  }

  private stopTokenCheck(): void {
    if (this.tokenCheckInterval) {
      clearInterval(this.tokenCheckInterval);
      this.tokenCheckInterval = undefined;
    }
  }

  private verifyToken(): void {
    const token = this.getToken();
    if (!token) {
      return;
    }

    const headers = new HttpHeaders().set('Authorization', `Token ${token}`);
    // Используем легковесный endpoint для проверки токена
    this.http.get<{ user: User; profile: UserProfile | null }>(
      `${this.base}/companies/auth/me/`,
      { headers }
    ).subscribe({
      next: (response) => {
        // Токен валидный, обновляем данные пользователя
        this.currentUserSubject.next(response.user);
        this.currentProfileSubject.next(response.profile);
      },
      error: (err) => {
        // Если получили 401, токен невалидный - очищаем сессию
        if (err.status === 401) {
          console.warn('[AuthService] Токен истек или невалидный, очищаем сессию');
          this.clearAuth();
          this.router.navigate(['/login'], { queryParams: { returnUrl: this.router.url } });
        }
      },
    });
  }

  isAuthenticated(): boolean {
    const token = this.getToken();
    // Если токена нет, точно не авторизован
    if (!token) {
      return false;
    }
    // Если токен есть, но пользователь еще не загружен, считаем авторизованным
    // (пользователь загрузится асинхронно)
    return true;
  }

  getCurrentUser(): User | null {
    return this.currentUserSubject.value;
  }

  getCurrentProfile(): UserProfile | null {
    return this.currentProfileSubject.value;
  }

  isSuperAdmin(): boolean {
    const profile = this.getCurrentProfile();
    return profile?.role === 'superadmin';
  }

  isCompanyAdmin(): boolean {
    const profile = this.getCurrentProfile();
    return profile?.role === 'company_admin';
  }

  private loadCurrentUser(): void {
    const token = this.getToken();
    if (!token) {
      return;
    }
    
    const headers = new HttpHeaders().set('Authorization', `Token ${token}`);
    this.http.get<{ user: User; profile: UserProfile | null }>(
      `${this.base}/companies/auth/me/`,
      { headers }
    ).subscribe({
      next: (response) => {
        this.currentUserSubject.next(response.user);
        this.currentProfileSubject.next(response.profile);
      },
      error: (err) => {
        // Очищаем токен только если получили 401 (невалидный токен)
        // 403 или другие ошибки могут быть временными
        if (err.status === 401) {
          console.warn('[AuthService] Токен невалидный, очищаем сессию');
          this.clearAuth();
        } else {
          console.warn('[AuthService] Ошибка загрузки пользователя:', err.status, err.statusText);
          // При других ошибках не очищаем токен, возможно это временная проблема
        }
      },
    });
  }
}

