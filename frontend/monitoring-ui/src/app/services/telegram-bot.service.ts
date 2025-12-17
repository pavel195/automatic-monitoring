import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface TelegramBot {
  id?: number;
  company?: number;
  bot_token: string;
  bot_username?: string;
  chat_ids: string[];
  discussion_chat_ids: string[];
  allow_direct: boolean;
  status?: 'active' | 'inactive' | 'error';
  last_error?: string;
  created_at?: string;
  updated_at?: string;
}

@Injectable({ providedIn: 'root' })
export class TelegramBotService {
  private readonly base = `${environment.apiUrl}/companies/bots/`;

  constructor(private readonly http: HttpClient) {}

  getBots(): Observable<TelegramBot[]> {
    return this.http.get<TelegramBot[]>(this.base);
  }

  getBot(id: number): Observable<TelegramBot> {
    return this.http.get<TelegramBot>(`${this.base}${id}/`);
  }

  createBot(bot: Partial<TelegramBot>): Observable<TelegramBot> {
    return this.http.post<TelegramBot>(this.base, bot);
  }

  updateBot(id: number, bot: Partial<TelegramBot>): Observable<TelegramBot> {
    return this.http.patch<TelegramBot>(`${this.base}${id}/`, bot);
  }

  deleteBot(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}${id}/`);
  }
}

