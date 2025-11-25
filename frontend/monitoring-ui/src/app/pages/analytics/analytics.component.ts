import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AnalyticsChartsComponent } from '../../components/analytics-charts/analytics-charts.component';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-analytics',
  standalone: true,
  imports: [CommonModule, AnalyticsChartsComponent],
  templateUrl: './analytics.component.html',
  styleUrls: ['./analytics.component.css'],
})
export class AnalyticsComponent implements OnInit {
  metrics: any;

  constructor(private readonly api: ApiService) {}

  ngOnInit(): void {
    this.api.getMetrics().subscribe((metrics) => (this.metrics = metrics));
  }
}

