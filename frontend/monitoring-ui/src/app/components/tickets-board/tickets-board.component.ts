import { Component, EventEmitter, Input, OnDestroy, OnInit, Output } from '@angular/core';
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
  @Input() tickets: Ticket[] = [];
  @Input() loading: boolean = false;
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
  private readonly statusLabels: Record<string, string> = {
    new: 'Новое',
    acknowledged: 'Подтверждено',
    in_progress: 'В работе',
    resolved: 'Решено',
    closed: 'Закрыто',
  };
  private readonly groupLabels: Record<string, string> = {
    operations: 'Эксплуатация',
    safety: 'Безопасность',
    info: 'Информация',
    service: 'Сервис',
    internal: 'Внутренние',
  };
  private readonly sentimentLabels: Record<string, string> = {
    positive: 'Позитивный',
    neutral: 'Нейтральный',
    negative: 'Негативный',
  };

  displayedColumns = [
    'title',
    'category',
    'priority',
    'sentiment',
    'status',
    'group',
    'created_at',
  ];
  
  selectedTicketId: number | null = null;
  private subscription = new Subscription();

  constructor(
    private readonly api: ApiService,
    private readonly ws: WebsocketService
  ) {}

  ngOnInit(): void {
    // Если тикеты переданы через @Input, используем их
    // Иначе загружаем самостоятельно (для обратной совместимости)
    if (!this.tickets || this.tickets.length === 0) {
      this.loadTickets();
      
      // Автообновление тикетов каждые 10 секунд
      const intervalId = setInterval(() => {
        this.loadTickets();
      }, 10000);
      this.subscription.add({ unsubscribe: () => clearInterval(intervalId) });
      
      this.subscription.add(
        this.ws.stream().subscribe((event) => {
          if (event) {
            this.loadTickets();
          }
        })
      );
    }
  }

  loadTickets() {
    this.api.getTickets().subscribe({
      next: (data: any) => {
        this.tickets = Array.isArray(data) ? data : data.results || [];
      },
      error: (err) => {
        console.error('Ошибка загрузки тикетов:', err);
        this.tickets = [];
        // Если ошибка авторизации, можно перенаправить на логин
        if (err.status === 401 || err.status === 403) {
          // Обработка будет в guard
        }
      },
    });
  }

  select(row: Ticket, event?: Event) {
    if (event) {
      // Не останавливаем всплытие, чтобы событие дошло до родителя
      // event.stopPropagation();
    }
    
    if (!row || !row.id) {
      console.warn('TicketsBoard: попытка выбрать пустую строку или тикет без ID', row);
      return;
    }
    
    console.log('TicketsBoard: выбран тикет', row.id, row.title, row);
    
    // Сохраняем выбранный ID для визуального выделения
    this.selectedTicketId = row.id;
    
    // Эмитим событие синхронно
    try {
      this.selectTicket.emit(row);
      console.log('TicketsBoard: событие selectTicket отправлено');
    } catch (error) {
      console.error('TicketsBoard: ошибка при отправке события', error);
    }
  }

  priorityColor(priority: number): string {
    switch (priority) {
      case 4:
        return 'warn'; // Критический - красный
      case 3:
        return 'accent'; // Высокий - оранжевый
      case 2:
        return 'primary'; // Средний - синий
      case 1:
        return 'primary'; // Низкий - синий
      default:
        return 'primary';
    }
  }

  priorityLabel(priority: number): string {
    switch (priority) {
      case 4:
        return 'Критический';
      case 3:
        return 'Высокий';
      case 2:
        return 'Средний';
      case 1:
        return 'Низкий';
      default:
        return `${priority}`;
    }
  }

  formatDate(dateString: string): string {
    if (!dateString) {
      return '—';
    }
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) {
      return 'только что';
    } else if (diffMins < 60) {
      return `${diffMins} мин. назад`;
    } else if (diffHours < 24) {
      return `${diffHours} ч. назад`;
    } else if (diffDays < 7) {
      return `${diffDays} дн. назад`;
    } else {
      return date.toLocaleDateString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
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

  displayStatus(status: string): string {
    return this.statusLabels[status] || status;
  }

  displayGroup(group: string): string {
    return this.groupLabels[group] || group || '—';
  }

  displaySentiment(sentiment: string | undefined): string {
    if (!sentiment) {
      return 'Нейтральный';
    }
    return this.sentimentLabels[sentiment] || sentiment;
  }

  ngOnDestroy(): void {
    this.subscription.unsubscribe();
  }
}

