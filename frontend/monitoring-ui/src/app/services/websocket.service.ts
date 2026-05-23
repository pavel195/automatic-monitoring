import { Injectable, OnDestroy } from '@angular/core';
import { Observable, Subject, Subscription, interval } from 'rxjs';
import { startWith } from 'rxjs/operators';

@Injectable({ providedIn: 'root' })
export class WebsocketService implements OnDestroy {
  private messages$ = new Subject<{ type: string }>();
  private ticker: Subscription;

  constructor() {
    this.ticker = interval(3000)
      .pipe(startWith(0))
      .subscribe(() => this.messages$.next({ type: 'tick' }));
  }

  stream(): Observable<{ type: string }> {
    return this.messages$.asObservable();
  }

  emitImmediate() {
    this.messages$.next({ type: 'tick' });
  }

  ngOnDestroy(): void {
    this.ticker.unsubscribe();
    this.messages$.complete();
  }
}
