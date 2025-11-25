import { Component, EventEmitter, OnDestroy, OnInit, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { ApiService, Ticket } from '../../services/api.service';
import { WebsocketService } from '../../services/websocket.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-tickets-board',
  standalone: true,
  imports: [CommonModule, MatTableModule, MatChipsModule, MatIconModule],
  templateUrl: './tickets-board.component.html',
  styleUrls: ['./tickets-board.component.css'],
})
export class TicketsBoardComponent implements OnInit, OnDestroy {
  @Output() selectTicket = new EventEmitter<Ticket>();

  displayedColumns = ['title', 'category', 'priority', 'status', 'group'];
  tickets: Ticket[] = [];
  private subscription = new Subscription();

  constructor(
    private readonly api: ApiService,
    private readonly ws: WebsocketService
  ) {}

  ngOnInit(): void {
    this.loadTickets();
    this.subscription.add(
      this.ws.stream().subscribe((event) => {
        if (event.type === 'ticket_created' || event.type?.includes('sla')) {
          this.loadTickets();
        }
      })
    );
  }

  loadTickets() {
    this.api.getTickets().subscribe((data: any) => {
      this.tickets = Array.isArray(data) ? data : data.results;
    });
  }

  select(row: Ticket) {
    this.selectTicket.emit(row);
  }

  priorityColor(priority: number): string {
    switch (priority) {
      case 4:
        return 'warn';
      case 3:
        return 'accent';
      default:
        return 'primary';
    }
  }

  ngOnDestroy(): void {
    this.subscription.unsubscribe();
  }
}

