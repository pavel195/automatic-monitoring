import { Component, OnInit } from '@angular/core';
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
export class DashboardComponent implements OnInit {
  metrics: any;
  latestTickets: Ticket[] = [];
  loading = true;
  sentimentStats: { label: string; percent: number; color: string }[] = [];

  private sentimentLabels: Record<string, string> = {
    positive: 'Позитив',
    neutral: 'Нейтрально',
    negative: 'Негатив',
  };
  private transportLabels: Record<string, string> = {
    metro: 'Метро',
    bus: 'Автобус',
    tram: 'Трамвай',
    train: 'Поезд',
    airplane: 'Самолёт',
    water: 'Водный транспорт',
    taxi: 'Такси',
    other: 'Транспорт',
  };
  private categoryLabels: Record<string, string> = {
    complaint: 'Жалоба',
    request: 'Запрос',
    incident: 'Инцидент',
    praise: 'Благодарность',
    suggestion: 'Предложение',
    payment: 'Оплата',
  };

  constructor(
    private readonly api: ApiService,
    private readonly router: Router
  ) {}

  ngOnInit() {
    this.loadData();
  }

  loadData() {
    this.api.getMetrics().subscribe({
      next: (metrics) => {
        this.metrics = metrics;
        this.sentimentStats = this.buildSentimentStats(
          metrics?.sentiment_breakdown || []
        );
      },
      error: (err) => {
        console.error('Ошибка загрузки метрик:', err);
        if (err.status === 401 || err.status === 403) {
          // Перенаправление будет обработано guard
        }
      },
    });
    this.api.getTickets().subscribe({
      next: (data: any) => {
        const tickets = Array.isArray(data) ? data : data.results || [];
        this.latestTickets = tickets.slice(0, 5);
        this.loading = false;
      },
      error: (err) => {
        console.error('Ошибка загрузки тикетов:', err);
        this.latestTickets = [];
        this.loading = false;
        if (err.status === 401 || err.status === 403) {
          // Перенаправление будет обработано guard
        }
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

  navigateToTickets(): void {
    this.router.navigate(['/tickets']).catch(err => {
      console.error('Ошибка навигации:', err);
    });
  }

  private buildSentimentStats(data: any[]): {
    label: string;
    percent: number;
    color: string;
  }[] {
    const total = data.reduce((acc, item) => acc + item.total, 0) || 1;
    const palette: Record<string, string> = {
      positive: '#10B981',
      neutral: '#94A3B8',
      negative: '#EF4444',
    };
    return data.map((item) => ({
      label: this.sentimentLabels[item.sentiment] || item.sentiment,
      percent: Math.round((item.total / total) * 100),
      color: palette[item.sentiment] || '#94A3B8',
    }));
  }
}
