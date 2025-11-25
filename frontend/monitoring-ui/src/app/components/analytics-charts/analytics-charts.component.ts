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
  sentimentData: { name: string; value: number }[] = [];
  statusData: { name: string; value: number }[] = [];
  channelData: { name: string; value: number }[] = [];
  modeData: { name: string; value: number }[] = [];
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
    if (changes['metrics'] && this.metrics?.category_breakdown) {
      this.categoryData = this.metrics.category_breakdown.map(
        (item: any) => ({
          name: item.category,
          value: item.total,
        })
      );
    }
    if (changes['metrics'] && this.metrics?.sentiment_breakdown) {
      this.sentimentData = this.metrics.sentiment_breakdown.map((item: any) => ({
        name: item.sentiment,
        value: item.total,
      }));
    }
    if (changes['metrics'] && this.metrics?.status_breakdown) {
      this.statusData = this.metrics.status_breakdown.map((item: any) => ({
        name: item.status,
        value: item.total,
      }));
    }
    if (changes['metrics'] && this.metrics?.channel_breakdown) {
      this.channelData = this.metrics.channel_breakdown
        .slice(0, 6)
        .map((item: any) => ({
          name: item.channel,
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

