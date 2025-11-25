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

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['metrics'] && this.metrics?.category_breakdown) {
      this.categoryData = this.metrics.category_breakdown.map(
        (item: any) => ({
          name: item.category,
          value: item.total,
        })
      );
    }
  }
}

