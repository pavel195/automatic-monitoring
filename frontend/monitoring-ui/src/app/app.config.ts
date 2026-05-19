import { ApplicationConfig } from '@angular/core';
import { provideRouter, Routes } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { DashboardComponent } from './pages/dashboard/dashboard.component';
import { TicketsComponent } from './pages/tickets/tickets.component';
import { AnalyticsComponent } from './pages/analytics/analytics.component';
import { LoginComponent } from './pages/login/login.component';
import { RegisterComponent } from './pages/register/register.component';
import { TelegramBotsComponent } from './pages/telegram-bots/telegram-bots.component';
import { VkBotsComponent } from './pages/vk-bots/vk-bots.component';
import { IntegrationsComponent } from './pages/integrations/integrations.component';
import { authGuard } from './guards/auth.guard';
import { authInterceptor } from './interceptors/auth.interceptor';

const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'register', component: RegisterComponent },
  { 
    path: '', 
    component: DashboardComponent, 
    canActivate: [authGuard],
    data: { requiresAuth: true }
  },
  { 
    path: 'tickets', 
    component: TicketsComponent, 
    canActivate: [authGuard],
    data: { requiresAuth: true }
  },
  { 
    path: 'analytics', 
    component: AnalyticsComponent, 
    canActivate: [authGuard],
    data: { requiresAuth: true }
  },
  { 
    path: 'integrations', 
    component: IntegrationsComponent, 
    canActivate: [authGuard],
    data: { requiresAuth: true },
    children: [
      {
        path: 'telegram-bots',
        component: TelegramBotsComponent,
      },
      {
        path: 'vk-bots',
        component: VkBotsComponent,
      },
      {
        path: '',
        redirectTo: 'telegram-bots',
        pathMatch: 'full',
      },
    ]
  },
  { 
    path: 'telegram-bots', 
    redirectTo: '/integrations/telegram-bots',
    pathMatch: 'full'
  },
  { path: '**', redirectTo: '/login' }, // Fallback для несуществующих роутов
];

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    provideHttpClient(withInterceptors([authInterceptor])),
  ],
};

