import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface Ticket {
  id: number;
  title: string;
  category: string;
  priority: number;
  status: string;
  assigned_group: string;
  ack_deadline: string;
  resolve_deadline: string;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly base = environment.apiUrl;

  constructor(private readonly http: HttpClient) {}

  getTickets(): Observable<{ results: Ticket[] } | Ticket[]> {
    return this.http.get<{ results: Ticket[] } | Ticket[]>(
      `${this.base}/tickets/`
    );
  }

  acknowledgeTicket(id: number): Observable<Ticket> {
    return this.http.post<Ticket>(`${this.base}/tickets/${id}/acknowledge/`, {});
  }

  resolveTicket(id: number): Observable<Ticket> {
    return this.http.post<Ticket>(`${this.base}/tickets/${id}/resolve/`, {});
  }

  getMetrics(): Observable<any> {
    return this.http.get(`${this.base}/analytics/metrics/`);
  }

  searchTickets(query: string) {
    return this.http.get(`${this.base}/search`, { params: { q: query } });
  }
}

