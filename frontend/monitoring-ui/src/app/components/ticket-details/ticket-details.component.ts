import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { ApiService, Ticket } from '../../services/api.service';

@Component({
  selector: 'app-ticket-details',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatButtonModule],
  templateUrl: './ticket-details.component.html',
  styleUrls: ['./ticket-details.component.css'],
})
export class TicketDetailsComponent {
  @Input() ticket?: Ticket;

  constructor(private readonly api: ApiService) {}

  acknowledge() {
    if (!this.ticket) {
      return;
    }
    this.api.acknowledgeTicket(this.ticket.id).subscribe((ticket) => {
      this.ticket = ticket;
    });
  }

  resolve() {
    if (!this.ticket) {
      return;
    }
    this.api.resolveTicket(this.ticket.id).subscribe((ticket) => {
      this.ticket = ticket;
    });
  }
}

