import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { NgxChartsModule } from '@swimlane/ngx-charts';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-analytics',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    NgxChartsModule,
  ],
  templateUrl: './analytics.component.html',
  styleUrls: ['./analytics.component.css'],
})
export class AnalyticsComponent implements OnInit {
  metrics: any = null;
  selectedPeriod: '24h' | '7d' | '30d' = '24h';
  
  // Данные для графиков
  statusData: { name: string; value: number }[] = [];
  categoryData: { name: string; value: number }[] = [];
  sentimentData: { name: string; value: number }[] = [];
  modeData: { name: string; value: number }[] = [];
  channelData: { name: string; value: number }[] = [];
  topicData: { name: string; value: number }[] = [];
  timeSeriesData: { name: string; series: { name: string; value: number }[] }[] = [];

  // Цветовые схемы
  statusColorScheme = {
    domain: ['#F97316', '#FBBF24', '#3B82F6', '#06B6D4', '#94A3B8']
  };
  categoryColorScheme = {
    domain: ['#3B82F6', '#F97316', '#10B981', '#8B5CF6']
  };
  sentimentColorScheme = {
    domain: ['#EF4444', '#94A3B8', '#10B981']
  };
  transportColorScheme = {
    domain: ['#2563EB', '#F97316', '#10B981', '#3B82F6', '#FB923C', '#06B6D4', '#8B5CF6']
  };

  // Лейблы
  private readonly categoryLabels: Record<string, string> = {
    complaint: 'Жалобы',
    request: 'Запросы',
    incident: 'Инциденты',
    praise: 'Благодарности',
  };

  private readonly sentimentLabels: Record<string, string> = {
    positive: 'Позитив',
    neutral: 'Нейтрально',
    negative: 'Негатив',
  };

  private readonly statusLabels: Record<string, string> = {
    new: 'Новое',
    acknowledged: 'Подтверждено',
    in_progress: 'В работе',
    resolved: 'Решено',
    closed: 'Закрыто',
  };

  private readonly channelLabels: Record<string, string> = {
    telegram: 'Telegram',
    email: 'Email',
    vk: 'VK',
    other: 'Другое',
  };

  private readonly modeLabels: Record<string, string> = {
    metro: 'Метро',
    bus: 'Автобус',
    tram: 'Трамвай',
    train: 'Поезд',
    airplane: 'Самолёт',
    water: 'Водный',
    taxi: 'Такси',
    other: 'Другое',
  };

  constructor(private readonly api: ApiService) {}

  ngOnInit(): void {
    this.loadMetrics();
  }

  selectPeriod(period: '24h' | '7d' | '30d'): void {
    this.selectedPeriod = period;
    this.loadMetrics();
  }

  loadMetrics(): void {
    this.api.getMetrics(this.selectedPeriod).subscribe((metrics) => {
      this.metrics = metrics;
      this.processMetrics(metrics);
    });
  }

  private processMetrics(metrics: any): void {
    // Статусы
    if (metrics?.status_breakdown) {
      this.statusData = metrics.status_breakdown.map((item: any) => ({
        name: this.statusLabels[item.status] || item.status,
        value: item.total,
      }));
    }

    // Категории
    if (metrics?.category_breakdown) {
      this.categoryData = metrics.category_breakdown.map((item: any) => ({
        name: this.categoryLabels[item.category] || item.category,
        value: item.total,
      }));
    }

    // Тональность
    if (metrics?.sentiment_breakdown) {
      this.sentimentData = metrics.sentiment_breakdown.map((item: any) => ({
        name: this.sentimentLabels[item.sentiment] || item.sentiment,
        value: item.total,
      }));
    }

    // Типы транспорта
    if (metrics?.mode_breakdown) {
      this.modeData = metrics.mode_breakdown
        .filter((item: any) => item.transport_mode && item.total > 0)
        .map((item: any) => ({
          name: this.modeLabels[item.transport_mode] || item.transport_mode,
          value: item.total,
        }))
        .sort((a: any, b: any) => b.value - a.value);
    }

    // Каналы
    if (metrics?.channel_breakdown) {
      this.channelData = metrics.channel_breakdown.map((item: any) => ({
        name: this.channelLabels[item.channel] || item.channel,
        value: item.total,
      }));
    }

    // Тематики
    if (metrics?.topic_breakdown) {
      this.topicData = metrics.topic_breakdown
        .map((item: any) => ({
          name: this.modeLabels[item.topic] ||
                this.categoryLabels[item.topic] ||
                item.topic,
          value: item.total,
        }))
        .sort((a: any, b: any) => b.value - a.value);
    }

    // Time series
    if (metrics?.time_series?.length) {
      this.timeSeriesData = [{
        name: 'Обращения',
        series: metrics.time_series.map((item: any) => {
          const date = new Date(item.timestamp);
          const label = this.selectedPeriod === '24h'
            ? `${date.getHours()}:00`
            : `${date.getDate()}.${(date.getMonth() + 1).toString().padStart(2, '0')}`;
          return { name: label, value: item.count };
        }),
      }];
    } else {
      this.timeSeriesData = [];
    }
  }

  // Форматирование
  formatDuration(seconds: number | null | undefined): string {
    if (!seconds) return 'н/д';
    if (seconds < 60) return `${Math.round(seconds)}с`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}м`;
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.round((seconds % 3600) / 60);
    return `${hours}ч ${minutes}м`;
  }

  getResolvedPercentage(): number {
    if (!this.metrics?.total) return 0;
    return Math.round((this.metrics.resolved / this.metrics.total) * 100);
  }

  getTransportPercentage(): number {
    if (!this.metrics?.total) return 0;
    return Math.round((this.metrics.transport_share || 0) * 100);
  }

  getStatusPercentage(value: number): number {
    if (!this.metrics?.total) return 0;
    return Math.round((value / this.metrics.total) * 100);
  }

  getSentimentPercentage(value: number): number {
    if (!this.metrics?.total) return 0;
    return Math.round((value / this.metrics.total) * 100);
  }

  getTopicPercentage(value: number): number {
    if (!this.topicData.length) return 0;
    const max = Math.max(...this.topicData.map(t => t.value));
    return max > 0 ? Math.round((value / max) * 100) : 0;
  }

  getChannelPercentage(value: number): number {
    if (!this.channelData.length) return 0;
    const max = Math.max(...this.channelData.map(c => c.value));
    return max > 0 ? Math.round((value / max) * 100) : 0;
  }

  getOpenPercentage(): number {
    if (!this.metrics?.total) return 0;
    return Math.round((this.metrics.open_count / this.metrics.total) * 100);
  }

  getNewPercentage(): number {
    if (!this.metrics?.total) return 0;
    return Math.round((this.metrics.new_count / this.metrics.total) * 100);
  }

  // Иконки и цвета
  getStatusColor(status: string): string {
    const colors: Record<string, string> = {
      'Новое': '#F97316',
      'Подтверждено': '#FBBF24',
      'В работе': '#3B82F6',
      'Решено': '#06B6D4',
      'Закрыто': '#94A3B8',
    };
    return colors[status] || '#64748B';
  }

  getSentimentIcon(sentiment: string): string {
    const icons: Record<string, string> = {
      'Позитив': 'sentiment_satisfied',
      'Нейтрально': 'sentiment_neutral',
      'Негатив': 'sentiment_dissatisfied',
    };
    return icons[sentiment] || 'help';
  }

  getChannelIcon(channel: string): string {
    const icons: Record<string, string> = {
      'Telegram': 'send',
      'Email': 'email',
      'VK': 'forum',
      'Другое': 'more_horiz',
    };
    return icons[channel] || 'chat';
  }

  getChannelColor(channel: string): string {
    const colors: Record<string, string> = {
      'Telegram': '#F97316',
      'Email': '#3B82F6',
      'VK': '#8B5CF6',
      'Другое': '#94A3B8',
    };
    return colors[channel] || '#64748B';
  }
}
