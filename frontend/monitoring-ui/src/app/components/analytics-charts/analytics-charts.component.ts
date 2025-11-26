import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { NgxChartsModule } from '@swimlane/ngx-charts';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-analytics-charts',
  standalone: true,
  imports: [CommonModule, NgxChartsModule],
  templateUrl: './analytics-charts.component.html',
  styleUrls: ['./analytics-charts.component.css'],
})
export class AnalyticsChartsComponent implements OnChanges {
  @Input() metrics: any;
  categoryData: { name: string; value: number }[] = [];
  topicData: { name: string; value: number }[] = [];
  sentimentData: { name: string; value: number }[] = [];
  statusData: { name: string; value: number }[] = [];
  channelData: { name: string; value: number }[] = [];
  modeData: { name: string; value: number }[] = [];
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
  private modeLabels: Record<string, string> = {
    metro: 'Метро',
    bus: 'Автобус',
    tram: 'Трамвай',
    train: 'Поезд',
    airplane: 'Самолёт',
    water: 'Водный',
    taxi: 'Такси',
    other: 'Другое',
  };

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['metrics'] && this.metrics?.topic_breakdown) {
      this.topicData = this.metrics.topic_breakdown.map((item: any) => ({
        name:
          this.modeLabels[item.topic] ??
          this.categoryLabels[item.topic] ??
          item.topic,
        value: item.total,
      }));
    }
    if (changes['metrics'] && this.metrics?.category_breakdown) {
      this.categoryData = this.metrics.category_breakdown.map(
        (item: any) => ({
          name: this.categoryLabels[item.category] || item.category,
          value: item.total,
        })
      );
    }
    if (changes['metrics'] && this.metrics?.sentiment_breakdown) {
      this.sentimentData = this.metrics.sentiment_breakdown.map((item: any) => ({
        name: this.sentimentLabels[item.sentiment] || item.sentiment,
        value: item.total,
      }));
    }
    if (changes['metrics'] && this.metrics?.status_breakdown) {
      this.statusData = this.metrics.status_breakdown.map((item: any) => ({
        name: this.statusLabels[item.status] || item.status,
        value: item.total,
      }));
    }
    if (changes['metrics'] && this.metrics?.channel_breakdown) {
      this.channelData = this.metrics.channel_breakdown
        .slice(0, 6)
        .map((item: any) => ({
          name: this.channelLabels[item.channel] || item.channel,
          value: item.total,
        }));
    }
    if (changes['metrics'] && this.metrics?.mode_breakdown) {
      this.modeData = this.metrics.mode_breakdown
        .filter((item: any) => item.transport_mode)
        .map((item: any) => ({
          name: this.modeLabels[item.transport_mode] || item.transport_mode,
          value: item.total,
        }));
    }
  }
}

