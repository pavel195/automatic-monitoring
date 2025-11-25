import { Component, EventEmitter, OnDestroy, OnInit, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { ApiService, Ticket } from '../../services/api.service';
import { WebsocketService } from '../../services/websocket.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-tickets-board',
  standalone: true,
  imports: [CommonModule, MatTableModule, MatChipsModule],
  templateUrl: './tickets-board.component.html',
  styleUrls: ['./tickets-board.component.css'],
})
export class TicketsBoardComponent implements OnInit, OnDestroy {
  @Output() selectTicket = new EventEmitter<Ticket>();

  private readonly transportLabels: Record<string, string> = {
    metro: 'Метро',
    bus: 'Автобус',
    tram: 'Трамвай',
    train: 'Поезд',
    airplane: 'Самолёт',
    water: 'Водный транспорт',
    taxi: 'Такси',
    other: 'Транспорт',
  };

  private readonly categoryLabels: Record<string, string> = {
    complaint: 'Жалоба',
    praise: 'Благодарность',
    request: 'Запрос',
    incident: 'Инцидент',
  };

  displayedColumns = [
    'title',
    'category',
    'priority',
    'sentiment',
    'status',
    'group',
  ];
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
        if (event) {
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

  sentimentColor(sentiment: string): string {
    switch (sentiment) {
      case 'positive':
        return 'accent';
      case 'negative':
        return 'warn';
      default:
        return 'primary';
    }
  }

  displayCategory(ticket: Ticket): string {
    if (ticket.is_transport && ticket.transport_mode) {
      return this.transportLabels[ticket.transport_mode] || 'Транспорт';
    }
    return this.categoryLabels[ticket.category] || ticket.category;
  }

  ngOnDestroy(): void {
    this.subscription.unsubscribe();
  }
}

