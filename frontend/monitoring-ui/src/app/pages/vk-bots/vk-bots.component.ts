import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { VkBotService, VkBot } from '../../services/vk-bot.service';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-vk-bots',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatSnackBarModule,
  ],
  templateUrl: './vk-bots.component.html',
  styleUrls: ['./vk-bots.component.css'],
})
export class VkBotsComponent implements OnInit {
  bots: VkBot[] = [];
  displayedColumns: string[] = ['community_name', 'status', 'actions'];
  loading = false;
  showForm = false;
  editingBot: VkBot | null = null;

  communityToken = '';
  showToken = false;
  error = '';
  fieldErrors: { [key: string]: string[] } = {};

  constructor(
    private readonly botService: VkBotService,
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
      error: () => {
        this.snackBar.open('Ошибка загрузки VK ботов', 'Закрыть', { duration: 3000 });
        this.loading = false;
      },
    });
  }

  openCreateForm(): void {
    this.editingBot = null;
    this.resetForm();
    this.showForm = true;
  }

  openEditForm(bot: VkBot): void {
    this.editingBot = bot;
    this.communityToken = bot.community_token || '';
    this.error = '';
    this.fieldErrors = {};
    this.showForm = true;
  }

  cancelForm(): void {
    this.showForm = false;
    this.resetForm();
  }

  resetForm(): void {
    this.communityToken = '';
    this.error = '';
    this.fieldErrors = {};
  }

  onSubmit(): void {
    this.error = '';
    this.fieldErrors = {};

    if (!this.communityToken.trim()) {
      this.error = 'Токен сообщества обязателен';
      return;
    }

    const botData: Partial<VkBot> = {
      community_token: this.communityToken.trim(),
    };

    const request = this.editingBot
      ? this.botService.updateBot(this.editingBot.id!, botData)
      : this.botService.createBot(botData);

    this.loading = true;
    request.subscribe({
      next: () => {
        this.snackBar.open(
          this.editingBot ? 'VK бот обновлён' : 'VK бот создан',
          'Закрыть',
          { duration: 3000 }
        );
        this.loadBots();
        this.cancelForm();
      },
      error: (err) => {
        this.loading = false;
        if (err.error && typeof err.error === 'object') {
          const errors = err.error;
          this.fieldErrors = {};
          for (const [key, value] of Object.entries(errors)) {
            if (key === 'detail' || key === 'error') continue;
            this.fieldErrors[key] = Array.isArray(value) ? value as string[] : [value as string];
          }
          if (errors.detail) {
            this.error = Array.isArray(errors.detail) ? errors.detail[0] : errors.detail;
          } else if (Object.keys(this.fieldErrors).length > 0) {
            const firstKey = Object.keys(this.fieldErrors)[0];
            this.error = `${firstKey}: ${this.fieldErrors[firstKey][0]}`;
          } else {
            this.error = 'Ошибка сохранения. Попробуйте ещё раз.';
          }
        } else {
          this.error = err.message || 'Ошибка сохранения.';
        }
      },
    });
  }

  deleteBot(bot: VkBot): void {
    if (!confirm(`Удалить VK бота ${bot.community_name || 'без названия'}?`)) return;
    this.loading = true;
    this.botService.deleteBot(bot.id!).subscribe({
      next: () => {
        this.snackBar.open('VK бот удалён', 'Закрыть', { duration: 3000 });
        this.loadBots();
      },
      error: () => {
        this.snackBar.open('Ошибка удаления', 'Закрыть', { duration: 3000 });
        this.loading = false;
      },
    });
  }

  getStatusLabel(status?: string): string {
    const labels: Record<string, string> = { active: 'Активен', inactive: 'Неактивен', error: 'Ошибка' };
    return labels[status || ''] || 'Неизвестно';
  }

  hasFieldError(field: string): boolean {
    return !!this.fieldErrors[field]?.length;
  }

  getFieldError(field: string): string | null {
    return this.fieldErrors[field]?.[0] || null;
  }
}
