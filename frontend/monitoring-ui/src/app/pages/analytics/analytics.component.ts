import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { AnalyticsChartsComponent } from '../../components/analytics-charts/analytics-charts.component';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-analytics',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, AnalyticsChartsComponent],
  templateUrl: './analytics.component.html',
  styleUrls: ['./analytics.component.css'],
})
export class AnalyticsComponent implements OnInit {
  metrics: any;
  summaryCards: Array<{
    label: string;
    value: number | string;
    subtitle: string;
    icon: string;
  }> = [];

  constructor(private readonly api: ApiService) {}

  ngOnInit(): void {
    this.api.getMetrics().subscribe((metrics) => {
      this.metrics = metrics;
      this.summaryCards = this.buildSummary(metrics);
    });
  }

  private buildSummary(metrics: any) {
    if (!metrics) {
      return [];
    }
    return [
      {
        label: 'Открытые обращения',
        value: metrics.open_count ?? 0,
        subtitle: 'В работе / ожидают реакции',
        icon: 'outbound',
      },
      {
        label: 'Новые обращения',
        value: metrics.new_count ?? 0,
        subtitle: 'Без подтверждения',
        icon: 'priority_high',
      },
      {
        label: 'Сообщений за 24ч',
        value: metrics.messages_total ?? 0,
        subtitle: 'По всем каналам',
        icon: 'forum',
      },
      {
        label: 'Доля транспорта',
        value: `${Math.round((metrics.transport_share || 0) * 100)}%`,
        subtitle: `${metrics.transport_total || 0} из ${metrics.total || 0}`,
        icon: 'train',
      },
    ];
  }
}

