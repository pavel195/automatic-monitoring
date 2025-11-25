import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { ApiService, Ticket } from '../../services/api.service';
import { TicketsBoardComponent } from '../../components/tickets-board/tickets-board.component';
import { AnalyticsChartsComponent } from '../../components/analytics-charts/analytics-charts.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    TicketsBoardComponent,
    AnalyticsChartsComponent,
  ],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css'],
})
export class DashboardComponent implements OnInit {
  metrics: any;
  latestTickets: Ticket[] = [];
  loading = true;
  sentimentStats: { label: string; percent: number; color: string }[] = [];
  transportShare = 0;

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
  };

  constructor(private readonly api: ApiService) {}

  ngOnInit() {
    this.loadData();
  }

  loadData() {
    this.api.getMetrics().subscribe((metrics) => {
      this.metrics = metrics;
      this.transportShare = metrics?.transport_share || 0;
      this.sentimentStats = this.buildSentimentStats(
        metrics?.sentiment_breakdown || []
      );
    });
    this.api.getTickets().subscribe((data: any) => {
      const tickets = Array.isArray(data) ? data : data.results;
      this.latestTickets = tickets.slice(0, 4);
      this.loading = false;
    });
  }

  priorityLabel(priority: number): string {
    return ['—', 'Низкий', 'Средний', 'Высокий', 'Критический'][priority] || '—';
  }

  sentimentChip(sentiment: string): string {
    return this.sentimentLabels[sentiment] || 'Нейтрально';
  }

  topicLabel(ticket: Ticket): string {
    if (ticket.is_transport && ticket.transport_mode) {
      return this.transportLabels[ticket.transport_mode] || 'Транспорт';
    }
    return this.categoryLabels[ticket.category] || ticket.category;
  }

  private buildSentimentStats(data: any[]): {
    label: string;
    percent: number;
    color: string;
  }[] {
    const total = data.reduce((acc, item) => acc + item.total, 0) || 1;
    const palette: Record<string, string> = {
      positive: '#22d3ee',
      neutral: '#94a3b8',
      negative: '#f97066',
    };
    return data.map((item) => ({
      label: this.sentimentLabels[item.sentiment] || item.sentiment,
      percent: Math.round((item.total / total) * 100),
      color: palette[item.sentiment] || '#94a3b8',
    }));
  }
}

