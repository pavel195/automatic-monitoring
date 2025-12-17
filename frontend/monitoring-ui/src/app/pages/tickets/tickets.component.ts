import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { TicketsBoardComponent } from '../../components/tickets-board/tickets-board.component';
import { TicketDetailsComponent } from '../../components/ticket-details/ticket-details.component';
import { ApiService, Ticket } from '../../services/api.service';
import { debounceTime, distinctUntilChanged, Subject } from 'rxjs';

interface Filters {
  status: string | null;
  category: string | null;
  priority: number | null;
  sentiment: string | null;
  group: string | null;
}

@Component({
  selector: 'app-tickets-page',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    TicketsBoardComponent,
    TicketDetailsComponent,
  ],
  templateUrl: './tickets.component.html',
  styleUrls: ['./tickets.component.css'],
})
export class TicketsComponent implements OnInit {
  selected?: Ticket;
  allTickets: Ticket[] = [];
  filteredTickets: Ticket[] = [];
  searchQuery: string = '';
  loading = false;
  
  filters: Filters = {
    status: null,
    category: null,
    priority: null,
    sentiment: null,
    group: null,
  };

  private searchSubject = new Subject<string>();

  constructor(
    private readonly api: ApiService,
    private readonly cdr: ChangeDetectorRef
  ) {
    // Debounce для поиска - ждем 500ms после последнего ввода
    this.searchSubject
      .pipe(
        debounceTime(500),
        distinctUntilChanged()
      )
      .subscribe((query) => {
        this.performSearch(query);
      });
  }

  ngOnInit() {
    this.loadTickets();
  }

  loadTickets() {
    this.loading = true;
    this.api.getTickets().subscribe({
      next: (data: any) => {
        this.allTickets = Array.isArray(data) ? data : data.results || [];
        this.applyFilters();
        this.loading = false;
      },
      error: (err) => {
        console.error('Ошибка загрузки тикетов:', err);
        this.allTickets = [];
        this.filteredTickets = [];
        this.loading = false;
      },
    });
  }

  onSearchChange() {
    if (this.searchQuery.trim()) {
      // Используем полнотекстовый поиск через Elasticsearch
      this.searchSubject.next(this.searchQuery.trim());
    } else {
      // Если поиск пустой, показываем все тикеты с примененными фильтрами
      this.filteredTickets = this.allTickets;
      this.applyFilters();
    }
  }

  performSearch(query: string) {
    if (!query.trim()) {
      this.applyFilters();
      return;
    }

    this.loading = true;
    this.api.searchTickets(query).subscribe({
      next: (response: any) => {
        // Elasticsearch возвращает результаты в формате { hits: { hits: [...] } }
        const searchResults: Ticket[] = [];
        
        if (response.hits && response.hits.hits) {
          // Извлекаем ID тикетов из результатов поиска
          // Elasticsearch возвращает _id как строку, нужно преобразовать в число
          const searchIds = response.hits.hits.map((hit: any) => 
            parseInt(hit._id, 10)
          );
          
          // Находим полные объекты тикетов по ID
          searchResults.push(
            ...this.allTickets.filter((ticket) =>
              searchIds.includes(ticket.id)
            )
          );
        }

        // Если результатов поиска нет, но есть тикеты, применяем фильтры ко всем
        if (searchResults.length === 0 && this.allTickets.length > 0) {
          // Возможно, поиск не нашел совпадений, но показываем все с фильтрами
          this.filteredTickets = this.applyFiltersToTickets(this.allTickets);
        } else {
          // Применяем фильтры к результатам поиска
          this.filteredTickets = this.applyFiltersToTickets(searchResults);
        }
        
        this.loading = false;
      },
      error: (err) => {
        console.error('Ошибка поиска:', err);
        // При ошибке поиска показываем все тикеты с фильтрами
        this.applyFilters();
        this.loading = false;
      },
    });
  }

  clearSearch() {
    this.searchQuery = '';
    this.filteredTickets = this.allTickets;
    this.applyFilters();
  }

  applyFilters() {
    this.filteredTickets = this.applyFiltersToTickets(this.allTickets);
  }

  private applyFiltersToTickets(tickets: Ticket[]): Ticket[] {
    return tickets.filter((ticket) => {
      // Фильтр по статусу
      if (this.filters.status && ticket.status !== this.filters.status) {
        return false;
      }

      // Фильтр по категории
      if (this.filters.category && ticket.category !== this.filters.category) {
        return false;
      }

      // Фильтр по приоритету
      if (this.filters.priority !== null && ticket.priority !== this.filters.priority) {
        return false;
      }

      // Фильтр по тональности
      if (this.filters.sentiment && ticket.sentiment !== this.filters.sentiment) {
        return false;
      }

      // Фильтр по группе
      if (this.filters.group && ticket.assigned_group !== this.filters.group) {
        return false;
      }

      return true;
    });
  }

  clearFilters() {
    this.filters = {
      status: null,
      category: null,
      priority: null,
      sentiment: null,
      group: null,
    };
    this.applyFilters();
  }

  hasActiveFilters(): boolean {
    return (
      this.filters.status !== null ||
      this.filters.category !== null ||
      this.filters.priority !== null ||
      this.filters.sentiment !== null ||
      this.filters.group !== null
    );
  }

  onSelect(ticket: Ticket) {
    console.log('TicketsComponent.onSelect вызван с:', ticket);
    
    if (!ticket) {
      console.warn('TicketsComponent: попытка выбрать пустой тикет');
      this.selected = undefined;
      this.cdr.detectChanges();
      return;
    }
    
    if (!ticket.id) {
      console.warn('TicketsComponent: тикет без ID', ticket);
      return;
    }
    
    console.log('TicketsComponent: получен тикет', ticket.id, ticket.title);
    
    // Создаем новый объект для триггера изменений Angular
    // Используем Object.assign для создания нового объекта
    this.selected = Object.assign({}, ticket);
    
    // Принудительно запускаем обнаружение изменений
    this.cdr.detectChanges();
    
    console.log('TicketsComponent: selected установлен', this.selected?.id, this.selected?.title);
    
    // Дополнительная проверка через небольшую задержку
    setTimeout(() => {
      if (this.selected?.id === ticket.id) {
        console.log('TicketsComponent: selected подтвержден после задержки', this.selected.id);
      } else {
        console.warn('TicketsComponent: selected не совпадает!', this.selected?.id, 'ожидалось', ticket.id);
      }
    }, 100);
  }
}
