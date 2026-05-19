import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { ApiService, Ticket } from '../../services/api.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
  ],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css'],
})
export class DashboardComponent implements OnInit, OnDestroy {
  metrics: any;
  latestTickets: Ticket[] = [];
  loading = true;
  sentimentStats: { label: string; percent: number; color: string }[] = [];
  private refreshInterval?: ReturnType<typeof setInterval>;

  private sentimentLabels: Record<string, string> = {
    positive: 'Позитив',
    neutral: 'Нейтрально',
    negative: 'Негатив',
  };
  private transportLabels: Record<string, string> = {
    metro: 'Метро', bus: 'Автобус', tram: 'Трамвай', train: 'Поезд',
    airplane: 'Самолёт', water: 'Водный', taxi: 'Такси', other: 'Транспорт',
  };
  private categoryLabels: Record<string, string> = {
    complaint: 'Жалоба', request: 'Запрос', incident: 'Инцидент',
    praise: 'Благодарность', suggestion: 'Предложение', payment: 'Оплата',
  };
  private statusLabels: Record<string, string> = {
    new: 'Новое', acknowledged: 'Принято', in_progress: 'В работе',
    resolved: 'Решено', closed: 'Закрыто',
  };

  constructor(
    private readonly api: ApiService,
    private readonly router: Router
  ) {}

  ngOnInit() {
    this.loadData();
    this.refreshInterval = setInterval(() => this.loadData(), 30000);
  }

  ngOnDestroy() {
    if (this.refreshInterval) clearInterval(this.refreshInterval);
  }

  loadData() {
    this.api.getMetrics().subscribe({
      next: (metrics) => {
        this.metrics = metrics;
        this.sentimentStats = this.buildSentimentStats(metrics?.sentiment_breakdown || []);
      },
      error: () => {},
    });
    this.api.getTickets().subscribe({
      next: (data: any) => {
        const tickets = Array.isArray(data) ? data : data.results || [];
        this.latestTickets = tickets.slice(0, 5);
        this.loading = false;
      },
      error: () => {
        this.latestTickets = [];
        this.loading = false;
      },
    });
  }

  getResolvedPercentage(): number {
    if (!this.metrics?.total) return 0;
    return Math.round((this.metrics.resolved / this.metrics.total) * 100);
  }

  priorityLabel(priority: number): string {
    return ['—', 'Низкий', 'Средний', 'Высокий', 'Критический'][priority] || '—';
  }

  sentimentChip(sentiment: string): string {
    return this.sentimentLabels[sentiment] || 'Нейтрально';
  }

  getSentimentIcon(label: string): string {
    const icons: Record<string, string> = {
      'Позитив': 'sentiment_satisfied',
      'Нейтрально': 'sentiment_neutral',
      'Негатив': 'sentiment_dissatisfied',
    };
    return icons[label] || 'help';
  }

  topicLabel(ticket: Ticket): string {
    if (ticket.is_transport && ticket.transport_mode) {
      return this.transportLabels[ticket.transport_mode] || 'Транспорт';
    }
    return this.categoryLabels[ticket.category] || ticket.category;
  }

  statusLabel(status: string): string {
    return this.statusLabels[status] || status;
  }

  formatMtta(): string {
    if (!this.metrics?.mtta_seconds) return '—';
    const mins = Math.round(this.metrics.mtta_seconds / 60);
    if (mins < 60) return `${mins} мин`;
    return `${Math.round(mins / 60)} ч ${mins % 60} мин`;
  }

  formatMttr(): string {
    if (!this.metrics?.mttr_seconds) return '—';
    const mins = Math.round(this.metrics.mttr_seconds / 60);
    if (mins < 60) return `${mins} мин`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours} ч ${mins % 60} мин`;
    return `${Math.floor(hours / 24)} д ${hours % 24} ч`;
  }

  getChannelIcon(channel: string): string {
    const icons: Record<string, string> = {
      telegram: 'send', vk: 'group', email: 'email', other: 'chat',
    };
    return icons[channel] || 'chat';
  }

  getChannelName(channel: string): string {
    const names: Record<string, string> = {
      telegram: 'Telegram', vk: 'VKontakte', email: 'Email', other: 'Другое',
    };
    return names[channel] || channel;
  }

  relativeTime(dateStr: string): string {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'только что';
    if (mins < 60) return `${mins} мин назад`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours} ч назад`;
    return `${Math.floor(hours / 24)} д назад`;
  }

  navigateToTickets(): void {
    this.router.navigate(['/tickets']);
  }

  private buildSentimentStats(data: any[]): { label: string; percent: number; color: string }[] {
    const total = data.reduce((acc, item) => acc + item.total, 0) || 1;
    const palette: Record<string, string> = {
      positive: '#10B981', neutral: '#94A3B8', negative: '#EF4444',
    };
    return data.map((item) => ({
      label: this.sentimentLabels[item.sentiment] || item.sentiment,
      percent: Math.round((item.total / total) * 100),
      color: palette[item.sentiment] || '#94A3B8',
    }));
  }
}
