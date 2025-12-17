import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatChipsModule } from '@angular/material/chips';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { TelegramBotService, TelegramBot } from '../../services/telegram-bot.service';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-telegram-bots',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatTableModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatCheckboxModule,
    MatChipsModule,
    MatSnackBarModule,
  ],
  templateUrl: './telegram-bots.component.html',
  styleUrls: ['./telegram-bots.component.css'],
})
export class TelegramBotsComponent implements OnInit {
  bots: TelegramBot[] = [];
  displayedColumns: string[] = ['bot_username', 'status', 'allow_direct', 'actions'];
  loading = false;
  showForm = false;
  editingBot: TelegramBot | null = null;
  
  // Форма
  botToken = '';
  allowDirect = false;
  showToken = false;
  error = '';
  fieldErrors: { [key: string]: string[] } = {};

  constructor(
    private readonly botService: TelegramBotService,
    private readonly authService: AuthService,
    private readonly snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.loadBots();
  }

  loadBots(): void {
    this.loading = true;
    this.botService.getBots().subscribe({
      next: (bots) => {
        this.bots = bots;
        this.loading = false;
      },
      error: (err) => {
        console.error('Ошибка загрузки ботов:', err);
        this.snackBar.open('Ошибка загрузки ботов', 'Закрыть', { duration: 3000 });
        this.loading = false;
      },
    });
  }

  openCreateForm(): void {
    this.editingBot = null;
    this.resetForm();
    this.showForm = true;
  }

  openEditForm(bot: TelegramBot): void {
    this.editingBot = bot;
    this.botToken = bot.bot_token || '';
    this.allowDirect = bot.allow_direct || false;
    this.error = '';
    this.fieldErrors = {};
    this.showForm = true;
  }

  cancelForm(): void {
    this.showForm = false;
    this.resetForm();
  }

  resetForm(): void {
    this.botToken = '';
    this.allowDirect = false;
    this.error = '';
    this.fieldErrors = {};
  }

  onSubmit(): void {
    this.error = '';
    this.fieldErrors = {};

    if (!this.botToken.trim()) {
      this.error = 'Токен бота обязателен для заполнения';
      return;
    }

    const botData: Partial<TelegramBot> = {
      bot_token: this.botToken.trim(),
      chat_ids: [],
      discussion_chat_ids: [],
      allow_direct: this.allowDirect,
    };

    const request = this.editingBot
      ? this.botService.updateBot(this.editingBot.id!, botData)
      : this.botService.createBot(botData);

    this.loading = true;
    request.subscribe({
      next: () => {
        this.snackBar.open(
          this.editingBot ? 'Бот обновлен' : 'Бот создан успешно',
          'Закрыть',
          { duration: 3000 }
        );
        this.loadBots();
        this.cancelForm();
      },
      error: (err) => {
        this.loading = false;
        console.error('Ошибка сохранения бота:', err);
        console.error('Детали ошибки:', JSON.stringify(err.error, null, 2));

        if (err.error && typeof err.error === 'object') {
          const errors = err.error;
          this.fieldErrors = {};

          for (const [key, value] of Object.entries(errors)) {
            if (key === 'detail' || key === 'error') {
              continue;
            }
            if (Array.isArray(value)) {
              this.fieldErrors[key] = value;
            } else if (typeof value === 'string') {
              this.fieldErrors[key] = [value];
            }
          }

          if (errors.detail) {
            this.error = Array.isArray(errors.detail) ? errors.detail[0] : errors.detail;
          } else if (errors.error) {
            this.error = Array.isArray(errors.error) ? errors.error[0] : errors.error;
          } else if (Object.keys(this.fieldErrors).length > 0) {
            // Показываем первую ошибку из полей
            const firstErrorKey = Object.keys(this.fieldErrors)[0];
            const firstError = this.fieldErrors[firstErrorKey][0];
            this.error = `${firstErrorKey}: ${firstError}`;
          } else {
            this.error = 'Ошибка сохранения бота. Попробуйте еще раз.';
          }
        } else {
          this.error = err.error?.detail || err.error?.error || err.message || 'Ошибка сохранения бота. Попробуйте еще раз.';
        }
      },
    });
  }

  deleteBot(bot: TelegramBot): void {
    if (!confirm(`Удалить бота ${bot.bot_username || 'без username'}?`)) {
      return;
    }

    this.loading = true;
    this.botService.deleteBot(bot.id!).subscribe({
      next: () => {
        this.snackBar.open('Бот удален', 'Закрыть', { duration: 3000 });
        this.loadBots();
      },
      error: (err) => {
        console.error('Ошибка удаления бота:', err);
        this.snackBar.open('Ошибка удаления бота', 'Закрыть', { duration: 3000 });
        this.loading = false;
      },
    });
  }

  getStatusLabel(status?: string): string {
    switch (status) {
      case 'active':
        return 'Активен';
      case 'inactive':
        return 'Неактивен';
      case 'error':
        return 'Ошибка';
      default:
        return 'Неизвестно';
    }
  }

  getStatusColor(status?: string): string {
    switch (status) {
      case 'active':
        return 'primary';
      case 'inactive':
        return '';
      case 'error':
        return 'warn';
      default:
        return '';
    }
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

  isCompanyAdmin(): boolean {
    return this.authService.isCompanyAdmin() || this.authService.isSuperAdmin();
  }
}

