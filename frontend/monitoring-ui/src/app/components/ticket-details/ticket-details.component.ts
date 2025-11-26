import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { ApiService, Ticket, TicketResponse } from '../../services/api.service';
import { WebsocketService } from '../../services/websocket.service';

@Component({
  selector: 'app-ticket-details',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
  ],
  templateUrl: './ticket-details.component.html',
  styleUrls: ['./ticket-details.component.css'],
})
export class TicketDetailsComponent {
  @Input() ticket?: Ticket;
  responseBody = '';
  sending = false;
  errorMessage = '';
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
  private readonly statusLabels: Record<string, string> = {
    new: 'Новое',
    acknowledged: 'Подтверждено',
    in_progress: 'В работе',
    resolved: 'Решено',
    closed: 'Закрыто',
  };
  private readonly sentimentLabels: Record<string, string> = {
    positive: 'Позитивный',
    neutral: 'Нейтральный',
    negative: 'Негативный',
  };
  private readonly responseStatusLabels: Record<string, string> = {
    pending: 'В ожидании',
    sent: 'Отправлено',
    failed: 'Ошибка',
  };
  private readonly groupLabels: Record<string, string> = {
    operations: 'Эксплуатация',
    safety: 'Безопасность',
    info: 'Информация',
    service: 'Сервис',
    internal: 'Внутренние',
  };
  private readonly categoryLabels: Record<string, string> = {
    complaint: 'Жалоба',
    request: 'Запрос',
    incident: 'Инцидент',
    praise: 'Благодарность',
  };
  private readonly priorityLabels: Record<number, string> = {
    1: 'Низкий',
    2: 'Средний',
    3: 'Высокий',
    4: 'Критический',
  };

  constructor(
    private readonly api: ApiService,
    private readonly ws: WebsocketService
  ) {}

  acknowledge() {
    if (!this.ticket) {
      return;
    }
    this.api.acknowledgeTicket(this.ticket.id).subscribe((ticket) => {
      this.ticket = ticket;
      this.ws.emitImmediate();
    });
  }

  resolve() {
    if (!this.ticket) {
      return;
    }
    this.api.resolveTicket(this.ticket.id).subscribe((ticket) => {
      this.ticket = ticket;
      this.ws.emitImmediate();
    });
  }

  sendResponse() {
    if (!this.ticket || !this.responseBody.trim()) {
      this.errorMessage = 'Введите текст ответа';
      return;
    }
    this.sending = true;
    this.errorMessage = '';
    this.api
      .respondTicket(this.ticket.id, this.responseBody)
      .subscribe({
        next: (response: TicketResponse) => {
          if (this.ticket) {
            const responses = this.ticket.responses || [];
            this.ticket = {
              ...this.ticket,
              responses: [response, ...responses],
            };
          }
          this.responseBody = '';
          this.ws.emitImmediate();
          this.sending = false;
        },
        error: () => {
          this.errorMessage = 'Не удалось отправить ответ';
          this.sending = false;
        },
      });
  }

  get conversation() {
    if (!this.ticket) {
      return [];
    }
    const inbound =
      this.ticket.messages?.map((message) => ({
        id: `in-${message.id}`,
        direction: 'inbound',
        author: `@${message.author || 'user'}`,
        text: message.payload,
        meta: this.buildMetaLabel(
          this.transportLabels[message.transport_mode] || 'Транспорт',
          message.sentiment
        ),
        timestamp: message.received_at,
        status: '',
      })) || [];
    const outbound =
      this.ticket.responses?.map((response) => ({
        id: `out-${response.id}`,
        direction: 'outbound',
        author: 'Оператор',
        text: response.body,
        meta: this.responseStatusLabel(response.status),
        timestamp: response.created_at,
        status: response.status,
      })) || [];
    return [...inbound, ...outbound].sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
  }

  private buildMetaLabel(mode: string, sentiment: string | undefined) {
    if (!sentiment) {
      return mode;
    }
    return `${mode} · ${this.sentimentLabels[sentiment] || sentiment}`;
  }

  transportLabel(ticket: Ticket | undefined): string {
    if (!ticket) {
      return '—';
    }
    if (ticket.is_transport) {
      return (
        this.transportLabels[ticket.transport_mode] ||
        this.transportLabels.other
      );
    }
    return this.categoryLabels[ticket.category] || ticket.category || '—';
  }

  statusLabel(value: string | undefined): string {
    if (!value) {
      return '—';
    }
    return this.statusLabels[value] || value;
  }

  sentimentLabel(value: string | undefined): string {
    if (!value) {
      return 'Нейтральный';
    }
    return this.sentimentLabels[value] || value;
  }

  responseStatusLabel(value: string | undefined): string {
    if (!value) {
      return '';
    }
    return this.responseStatusLabels[value] || value;
  }

  groupLabel(value: string | undefined): string {
    if (!value) {
      return '—';
    }
    return this.groupLabels[value] || value;
  }

  priorityLabel(value: number | undefined): string {
    if (!value) {
      return '—';
    }
    return this.priorityLabels[value] || `${value}`;
  }
}

