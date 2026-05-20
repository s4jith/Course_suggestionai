import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class LoadingService {
  private readonly _loading$ = new BehaviorSubject<boolean>(false);
  private activeRequests = 0;

  readonly loading$: Observable<boolean> = this._loading$.asObservable();

  show(): void {
    this.activeRequests++;
    this._loading$.next(true);
  }

  hide(): void {
    this.activeRequests = Math.max(0, this.activeRequests - 1);
    if (this.activeRequests === 0) {
      this._loading$.next(false);
    }
  }
}
