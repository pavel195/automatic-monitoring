import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface VkBot {
  id?: number;
  company?: number;
  community_token: string;
  community_id?: string;
  community_name?: string;
  status?: 'active' | 'inactive' | 'error';
  last_error?: string;
  created_at?: string;
  updated_at?: string;
}

@Injectable({ providedIn: 'root' })
export class VkBotService {
  private readonly base = `${environment.apiUrl}/companies/vk-bots/`;

  constructor(private readonly http: HttpClient) {}

  getBots(): Observable<VkBot[]> {
    return this.http.get<VkBot[]>(this.base);
  }

  getBot(id: number): Observable<VkBot> {
    return this.http.get<VkBot>(`${this.base}${id}/`);
  }

  createBot(bot: Partial<VkBot>): Observable<VkBot> {
    return this.http.post<VkBot>(this.base, bot);
  }

  updateBot(id: number, bot: Partial<VkBot>): Observable<VkBot> {
    return this.http.patch<VkBot>(`${this.base}${id}/`, bot);
  }

  deleteBot(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}${id}/`);
  }
}
