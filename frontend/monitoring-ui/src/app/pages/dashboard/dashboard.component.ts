import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { ApiService } from '../../services/api.service';
import { TicketsBoardComponent } from '../../components/tickets-board/tickets-board.component';
import { AnalyticsChartsComponent } from '../../components/analytics-charts/analytics-charts.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    TicketsBoardComponent,
    AnalyticsChartsComponent,
  ],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css'],
})
export class DashboardComponent implements OnInit {
  metrics: any;

  constructor(private readonly api: ApiService) {}

  ngOnInit() {
    this.api.getMetrics().subscribe((metrics) => (this.metrics = metrics));
  }
}

