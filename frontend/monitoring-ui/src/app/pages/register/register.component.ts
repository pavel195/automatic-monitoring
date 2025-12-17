import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    RouterLink,
  ],
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.css'],
})
export class RegisterComponent {
  companyName = '';
  description = '';
  contactEmail = '';
  contactPhone = '';
  adminEmail = '';
  adminPassword = '';
  adminFirstName = '';
  adminLastName = '';
  botToken = '';
  error = '';
  fieldErrors: { [key: string]: string[] } = {};
  success = false;
  loading = false;

  constructor(
    private readonly authService: AuthService,
    private readonly router: Router
  ) {}

  onSubmit() {
    // Очищаем предыдущие ошибки
    this.error = '';
    this.fieldErrors = {};

    // Базовая валидация на клиенте
    if (!this.companyName || !this.contactEmail || !this.adminEmail || !this.adminPassword) {
      this.error = 'Заполните все обязательные поля';
      return;
    }

    if (this.adminPassword.length < 8) {
      this.fieldErrors['admin_password'] = ['Пароль должен содержать минимум 8 символов'];
      return;
    }

    // Валидация email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(this.contactEmail)) {
      this.fieldErrors['contact_email'] = ['Введите корректный email адрес'];
      return;
    }
    if (!emailRegex.test(this.adminEmail)) {
      this.fieldErrors['admin_email'] = ['Введите корректный email адрес'];
      return;
    }

    this.loading = true;

    const companyData = {
      name: this.companyName,
      description: this.description,
      contact_email: this.contactEmail,
      contact_phone: this.contactPhone,
      admin_email: this.adminEmail,
      admin_password: this.adminPassword,
      admin_first_name: this.adminFirstName,
      admin_last_name: this.adminLastName,
    };

    this.authService.register(companyData).subscribe({
      next: () => {
        this.success = true;
        this.loading = false;
        setTimeout(() => {
          this.router.navigate(['/login']);
        }, 2000);
      },
      error: (err) => {
        this.loading = false;
        console.error('Ошибка регистрации:', err);
        
        // Обработка ошибок валидации от Django REST Framework
        if (err.error && typeof err.error === 'object') {
          // Если это словарь с ошибками полей
          const errors = err.error;
          this.fieldErrors = {};
          
          // Обрабатываем ошибки полей
          for (const [key, value] of Object.entries(errors)) {
            if (key === 'detail' || key === 'error') {
              // Пропускаем общие ошибки, обработаем их отдельно
              continue;
            }
            if (Array.isArray(value)) {
              this.fieldErrors[key] = value;
            } else if (typeof value === 'string') {
              this.fieldErrors[key] = [value];
            } else if (value && typeof value === 'object' && Array.isArray(value)) {
              this.fieldErrors[key] = value;
            }
          }
          
          // Если есть общая ошибка
          if (errors.detail) {
            this.error = Array.isArray(errors.detail) ? errors.detail[0] : errors.detail;
          } else if (errors.error) {
            this.error = Array.isArray(errors.error) ? errors.error[0] : errors.error;
          } else if (Object.keys(this.fieldErrors).length > 0) {
            // Если есть ошибки полей, но нет общей ошибки
            this.error = 'Пожалуйста, исправьте ошибки в форме';
          } else {
            this.error = 'Ошибка регистрации. Попробуйте еще раз.';
          }
        } else {
          // Общая ошибка
          this.error = err.error?.detail || err.error?.error || err.message || 'Ошибка регистрации. Попробуйте еще раз.';
        }
      },
    });
  }

  getFieldError(fieldName: string): string | null {
    const errors = this.fieldErrors[fieldName];
    if (errors && errors.length > 0) {
      return errors[0];
    }
    return null;
  }

  hasFieldError(fieldName: string): boolean {
    return !!this.fieldErrors[fieldName] && this.fieldErrors[fieldName].length > 0;
  }
}

