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
    localStorage.removeItem(this.tokenKey);
    this.currentUserSubject.next(null);
    this.currentProfileSubject.next(null);
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
      error: () => {
        this.clearAuth();
      },
    });
  }
}

