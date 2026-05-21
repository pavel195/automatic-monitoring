import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of } from 'rxjs';

import { TicketsComponent } from './tickets.component';
import { ApiService, Ticket } from '../../services/api.service';

const ticket: Ticket = {
  id: 1,
  title: 'Проверить салон',
  category: 'complaint',
  priority: 2,
  status: 'new',
  sentiment: 'negative',
  is_transport: true,
  transport_mode: 'bus',
  assigned_group: 'service',
  ack_deadline: '2026-05-20T10:00:00Z',
  resolve_deadline: '2026-05-20T12:00:00Z',
  created_at: '2026-05-20T09:00:00Z',
  updated_at: '2026-05-20T09:00:00Z',
};

describe('TicketsComponent', () => {
  let fixture: ComponentFixture<TicketsComponent>;
  let component: TicketsComponent;
  let api: jasmine.SpyObj<ApiService>;

  beforeEach(async () => {
    api = jasmine.createSpyObj<ApiService>('ApiService', [
      'getTickets',
      'searchTickets',
    ]);
    api.getTickets.and.returnValue(of([]));
    api.searchTickets.and.returnValue(of({ hits: { hits: [] } }));

    await TestBed.configureTestingModule({
      imports: [TicketsComponent, NoopAnimationsModule],
      providers: [{ provide: ApiService, useValue: api }],
    }).compileComponents();

    fixture = TestBed.createComponent(TicketsComponent);
    component = fixture.componentInstance;
  });

  it('keeps the list empty when search has no hits', () => {
    component.allTickets = [ticket];

    component.performSearch('ничего нет');

    expect(component.filteredTickets).toEqual([]);
  });
});
