import { ApplicationConfig } from '@angular/core';
import { provideRouter, Routes } from '@angular/router';
import { DashboardComponent } from './pages/dashboard/dashboard.component';
import { TicketsComponent } from './pages/tickets/tickets.component';
import { AnalyticsComponent } from './pages/analytics/analytics.component';

const routes: Routes = [
  { path: '', component: DashboardComponent },
  { path: 'tickets', component: TicketsComponent },
  { path: 'analytics', component: AnalyticsComponent },
];

export const appConfig: ApplicationConfig = {
  providers: [provideRouter(routes)],
};

