import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TicketsBoardComponent } from '../../components/tickets-board/tickets-board.component';
import { TicketDetailsComponent } from '../../components/ticket-details/ticket-details.component';
import { Ticket } from '../../services/api.service';

@Component({
  selector: 'app-tickets-page',
  standalone: true,
  imports: [CommonModule, TicketsBoardComponent, TicketDetailsComponent],
  templateUrl: './tickets.component.html',
  styleUrls: ['./tickets.component.css'],
})
export class TicketsComponent {
  selected?: Ticket;

  onSelect(ticket: Ticket) {
    this.selected = ticket;
  }
}

