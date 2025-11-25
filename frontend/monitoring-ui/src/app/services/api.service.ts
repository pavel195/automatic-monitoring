import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface ChannelMessage {
  id: number;
  author: string;
  payload: string;
  received_at: string;
  metadata: Record<string, unknown>;
  sentiment: string;
  is_transport: boolean;
  transport_mode: string;
}

export interface TicketResponse {
  id: number;
  body: string;
  status: string;
  channel: string;
  created_at: string;
}

export interface Ticket {
  id: number;
  title: string;
  category: string;
  priority: number;
  status: string;
  sentiment: string;
  is_transport: boolean;
  transport_mode: string;
  assigned_group: string;
  ack_deadline: string;
  resolve_deadline: string;
  messages?: ChannelMessage[];
  responses?: TicketResponse[];
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

  respondTicket(id: number, body: string): Observable<TicketResponse> {
    return this.http.post<TicketResponse>(`${this.base}/tickets/${id}/respond/`, {
      body,
    });
  }

  getMetrics(): Observable<any> {
    return this.http.get(`${this.base}/analytics/metrics/`);
  }

  searchTickets(query: string) {
    return this.http.get(`${this.base}/search`, { params: { q: query } });
  }
}

