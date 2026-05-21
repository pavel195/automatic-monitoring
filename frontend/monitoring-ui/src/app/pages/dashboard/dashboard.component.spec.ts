import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';

import { DashboardComponent } from './dashboard.component';
import { ApiService, Ticket } from '../../services/api.service';

const ticket: Ticket = {
  id: 1,
  title: 'Дым в вагоне метро',
  category: 'incident',
  priority: 4,
  status: 'new',
  sentiment: 'negative',
  is_transport: true,
  transport_mode: 'metro',
  assigned_group: 'safety',
  ack_deadline: '2026-05-20T10:00:00Z',
  resolve_deadline: '2026-05-20T12:00:00Z',
  created_at: '2026-05-20T09:00:00Z',
  updated_at: '2026-05-20T09:00:00Z',
};

describe('DashboardComponent', () => {
  let fixture: ComponentFixture<DashboardComponent>;
  let component: DashboardComponent;
  let api: jasmine.SpyObj<ApiService>;

  beforeEach(async () => {
    api = jasmine.createSpyObj<ApiService>('ApiService', [
      'getMetrics',
      'getTickets',
    ]);

    await TestBed.configureTestingModule({
      imports: [DashboardComponent, NoopAnimationsModule],
      providers: [
        provideRouter([]),
        { provide: ApiService, useValue: api },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DashboardComponent);
    component = fixture.componentInstance;
  });

  afterEach(() => {
    component.ngOnDestroy();
  });

  it('shows an error instead of a blank dashboard when data loading fails', () => {
    api.getMetrics.and.returnValue(throwError(() => ({ status: 403 })));
    api.getTickets.and.returnValue(throwError(() => ({ status: 403 })));

    fixture.detectChanges();

    expect(component.loading).toBeFalse();
    expect(component.errorMessage).toContain('Не удалось загрузить данные');
    expect(fixture.nativeElement.textContent).toContain('Данные не загрузились');
  });

  it('renders metrics and latest tickets when data is loaded', () => {
    api.getMetrics.and.returnValue(of({
      total: 3,
      resolved: 1,
      tickets_today: 2,
      tickets_this_week: 5,
      sla_breached_count: 0,
      sentiment_breakdown: [{ sentiment: 'negative', total: 1 }],
      channel_breakdown: [{ channel: 'telegram', total: 2 }],
    }));
    api.getTickets.and.returnValue(of([ticket]));

    fixture.detectChanges();

    const text = fixture.nativeElement.textContent;
    expect(component.errorMessage).toBe('');
    expect(text).toContain('Всего обращений');
    expect(text).toContain('Дым в вагоне метро');
  });
});
