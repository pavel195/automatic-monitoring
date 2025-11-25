import { HttpClient } from '@angular/common/http';
import { Injectable, OnDestroy } from '@angular/core';
import { Observable, Subject, interval } from 'rxjs';
import { switchMap } from 'rxjs/operators';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class WebsocketService implements OnDestroy {
  private socket?: WebSocket;
  private messages$ = new Subject<any>();

  constructor(private readonly http: HttpClient) {
    this.connect();
  }

  private connect() {
    try {
      this.socket = new WebSocket(environment.wsUrl);
      this.socket.onmessage = (event) => {
        this.messages$.next(JSON.parse(event.data));
      };
      this.socket.onerror = () => this.reconnect();
      this.socket.onclose = () => this.reconnect();
    } catch (err) {
      console.warn('WebSocket недоступен, переключаемся на poll', err);
      this.startPolling();
    }
  }

  private reconnect() {
    setTimeout(() => this.connect(), 5000);
  }

  private startPolling() {
    interval(10000)
      .pipe(
        switchMap(() => this.http.get(`${environment.apiUrl}/tickets/`))
      )
      .subscribe((tickets) => {
        this.messages$.next({ type: 'poll', payload: tickets });
      });
  }

  stream(): Observable<any> {
    return this.messages$.asObservable();
  }

  ngOnDestroy(): void {
    this.socket?.close();
    this.messages$.complete();
  }
}

