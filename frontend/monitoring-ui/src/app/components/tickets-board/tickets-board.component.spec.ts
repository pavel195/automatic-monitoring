import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

import { TicketsBoardComponent } from './tickets-board.component';
import { Ticket } from '../../services/api.service';

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

describe('TicketsBoardComponent', () => {
  let fixture: ComponentFixture<TicketsBoardComponent>;
  let component: TicketsBoardComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TicketsBoardComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(TicketsBoardComponent);
    component = fixture.componentInstance;
  });

  it('does not start a second polling loop', () => {
    const intervalSpy = spyOn(window, 'setInterval');

    fixture.detectChanges();

    expect(intervalSpy).not.toHaveBeenCalled();
  });

  it('emits the selected ticket', () => {
    spyOn(component.selectTicket, 'emit');

    component.select(ticket);

    expect(component.selectedTicketId).toBe(ticket.id);
    expect(component.selectTicket.emit).toHaveBeenCalledOnceWith(ticket);
  });
});
